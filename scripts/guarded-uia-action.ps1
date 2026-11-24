param(
 [Parameter(Mandatory=$true)][string]$Target,
 [string]$Deadline,
 [ValidateSet('Invoke','SendText','Probe','Scroll','Reveal','Key')][string]$Action='Invoke',
 [string]$TextFile,
 [ValidateSet('Right','Left','Escape','Refresh')][string]$Key
)
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')

$t=Get-Content -LiteralPath $Target -Raw | ConvertFrom-Json
if($Action -in @('Key','SendText')){Assert-BossForeground}
$root=Get-BossBrowserRoot ([long]$t.hwnd)
$binding=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
if(!$t.browser_binding_id -or $t.browser_binding_id -ne $binding.binding_id){throw 'stale_boss_browser_target_rebind_required'}
# RuntimeId is the UIA address to invoke, not a candidate identity/ancestor guard.
$condition=[System.Windows.Automation.PropertyCondition]::new(
 [System.Windows.Automation.AutomationElement]::RuntimeIdProperty,[int[]]$t.runtime_id)
$scope=$null
if(!$t.document_url){throw 'boss_document_identity_required'}
$matches=@(Get-BossDocuments $root|Where-Object {
 $v=$null;!$_.Current.IsOffscreen -and $_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -eq $t.document_url
})
if($matches.Count -eq 0){throw 'bound_boss_document_not_unique'}
if($matches.Count -eq 1){$scope=$matches[0]}
else {
 $containing=@($matches|Where-Object {
  (($_.GetRuntimeId() -join ',') -eq ($t.runtime_id -join ',')) -or
  ($null -ne $_.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition))
 })
 if($containing.Count -ne 1){throw 'bound_boss_document_not_unique'}
 $scope=$containing[0]
}

$element=if(($scope.GetRuntimeId() -join ',') -eq ($t.runtime_id -join ',')){$scope}else{$scope.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$condition)}
if(!$element){
 # Chromium sometimes omits RuntimeId property matches while exposing the same
 # element through a narrow control-type query. This is addressing, not a guard.
 $bc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
 foreach($button in $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$bc)){
  if(($button.GetRuntimeId() -join ',') -eq ($t.runtime_id -join ',')){$element=$button;break}
 }
}
if(!$element){throw 'uia_target_not_found'}
# Retained user-selected restrictions: forbidden controls and keyboard focus.
if($element.Current.Name -match '举报|不合适|删除' -or $element.Current.ClassName -in @('btn-report','btn-quxiao')){throw 'forbidden_target'}
Assert-BossBrowserTarget $element ([long]$t.hwnd)
if(!('BossForegroundRestore' -as [type])){
 Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class BossForegroundRestore {
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint process);
 [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
 [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint attach, uint attachTo, bool on);
 [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hWnd);
}
'@
}
function Restore-BossForeground([long]$Previous){
 if(!$Previous){return $false}
 $current=[long][BossForegroundRestore]::GetForegroundWindow()
 if($current -eq $Previous){return $false}
 if($current -ne [long]$t.hwnd){return $false}
 if(![BossForegroundRestore]::IsWindow([IntPtr]$Previous)){return $false}
 $process=0
 $targetThread=[BossForegroundRestore]::GetWindowThreadProcessId([IntPtr]$Previous,[ref]$process)
 $currentThread=[BossForegroundRestore]::GetCurrentThreadId()
 $attached=$false
 if($targetThread -and $targetThread -ne $currentThread){
  $attached=[BossForegroundRestore]::AttachThreadInput($currentThread,$targetThread,$true)
 }
 try{[void][BossForegroundRestore]::SetForegroundWindow([IntPtr]$Previous)}
 finally{if($attached){[void][BossForegroundRestore]::AttachThreadInput($currentThread,$targetThread,$false)}}
 return ([long][BossForegroundRestore]::GetForegroundWindow() -eq $Previous)
}
$previousForeground=[long][BossForegroundRestore]::GetForegroundWindow()
$restored=$false
$clickStartedAt=[DateTimeOffset]::Now.ToString('o')
if($Action -eq 'Probe'){}
elseif($Action -eq 'Invoke'){
 $navigationClasses=$element.Current.ClassName -split '\s+'
 if(@($navigationClasses|Where-Object {$_ -in @('card-inner','turn-btn','close-btn','boss-popup__close')}).Count){
  . (Join-Path $PSScriptRoot 'msaa-navigation.ps1')
  $msaaError=$null
  try{
   Invoke-BossMsaaNavigation $element $scope
   $restored=Restore-BossForeground $previousForeground
   @{state='dispatched';transport='msaa';verified_sent=$false;foreground_restored=$restored;clickStartedAt=$clickStartedAt;clickEndedAt=[DateTimeOffset]::Now.ToString('o')}|ConvertTo-Json -Compress
   exit
  }catch{
   $msaaError=$_.Exception.Message
   if($msaaError -match 'msaa_navigation_target_not_allowed|msaa_navigation_direction_not_allowed'){throw}
  }
  # MSAA 失效时在同一已核验目标上使用 UIA Invoke 备用点击。
  $invoke=$null
  if(!$element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw "msaa_failed:$msaaError;invoke_not_supported"}
  Assert-BossBrowserTarget $element ([long]$t.hwnd)
  $invoke.Invoke()
  $restored=Restore-BossForeground $previousForeground
  @{state='dispatched';transport='uia';verified_sent=$false;msaa_error=$msaaError;foreground_restored=$restored;clickStartedAt=$clickStartedAt;clickEndedAt=[DateTimeOffset]::Now.ToString('o')}|ConvertTo-Json -Compress
  exit
 }
 $invoke=$null
 if(!$element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw 'invoke_not_supported'}
 Assert-BossBrowserTarget $element ([long]$t.hwnd)
 $invoke.Invoke()
 $restored=Restore-BossForeground $previousForeground
}
elseif($Action -eq 'Scroll'){
 $scroll=$null
 if(!$element.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$scroll)){throw 'scroll_not_supported'}
 Assert-BossBrowserTarget $element ([long]$t.hwnd)
 $scroll.Scroll([System.Windows.Automation.ScrollAmount]::NoAmount,[System.Windows.Automation.ScrollAmount]::LargeIncrement)
}
elseif($Action -eq 'Reveal'){
 $scrollItem=$null
 if(!$element.TryGetCurrentPattern([System.Windows.Automation.ScrollItemPattern]::Pattern,[ref]$scrollItem)){throw 'card_reveal_not_supported'}
 $scrollItem.ScrollIntoView()
}
elseif($Action -eq 'Key'){
 if(!$Key){throw 'key_required'}
 $focus=[System.Windows.Automation.AutomationElement]::FocusedElement
 $walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
 Assert-BossBrowserTarget $focus ([long]$t.hwnd)
 $inDocument=$false
 for($i=0;$focus -and $i -lt 35;$i++){
  $v=$null
  if($focus.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document -and
   $focus.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -eq $t.document_url){$inDocument=$true;break}
  $focus=$walker.GetParent($focus)
 }
 if(!$inDocument){throw 'keyboard_focus_outside_target_document'}
 Add-Type -AssemblyName System.Windows.Forms
 $keys=@{Right='{RIGHT}';Left='{LEFT}';Escape='{ESC}';Refresh='^r'}
 [System.Windows.Forms.SendKeys]::SendWait($keys[$Key])
}
else{
 Add-Type -AssemblyName System.Windows.Forms
 $focus=[System.Windows.Automation.AutomationElement]::FocusedElement
 if(!$focus -or ($focus.GetRuntimeId() -join ',') -ne ($element.GetRuntimeId() -join ',') -or $element.Current.ControlType -ne [System.Windows.Automation.ControlType]::Edit){throw 'chat_input_not_focused'}
 [System.Windows.Forms.Clipboard]::SetText([IO.File]::ReadAllText($TextFile))
 [System.Windows.Forms.SendKeys]::SendWait('^v')
 [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
}
@{state='dispatched';verified_sent=$false;foreground_restored=$restored;clickStartedAt=$clickStartedAt;clickEndedAt=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Compress
