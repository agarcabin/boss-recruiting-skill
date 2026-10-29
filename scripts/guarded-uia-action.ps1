param(
 [Parameter(Mandatory=$true)][string]$Target,
 [string]$Deadline,
 [ValidateSet('Invoke','SendText','Probe','Scroll','Key')][string]$Action='Invoke',
 [string]$TextFile,
 [ValidateSet('Right','Left','Escape','Refresh')][string]$Key
)
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$t=Get-Content -LiteralPath $Target -Raw | ConvertFrom-Json
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$t.hwnd)
# RuntimeId is the UIA address to invoke, not a candidate identity/ancestor guard.
$condition=[System.Windows.Automation.PropertyCondition]::new(
 [System.Windows.Automation.AutomationElement]::RuntimeIdProperty,[int[]]$t.runtime_id)
$scope=$root
if($t.document_url){
 $docs=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document))
 foreach($doc in $docs){
  $v=$null
  if($doc.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -eq $t.document_url){$scope=$doc;break}
 }
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
$clickStartedAt=[DateTimeOffset]::Now.ToString('o')
if($Action -eq 'Probe'){}
elseif($Action -eq 'Invoke'){
 $invoke=$null
 if(!$element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw 'invoke_not_supported'}
 $invoke.Invoke()
}
elseif($Action -eq 'Scroll'){
 $scroll=$null
 if(!$element.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$scroll)){throw 'scroll_not_supported'}
 $scroll.Scroll([System.Windows.Automation.ScrollAmount]::NoAmount,[System.Windows.Automation.ScrollAmount]::LargeIncrement)
}
elseif($Action -eq 'Key'){
 if(!$Key){throw 'key_required'}
 $focus=[System.Windows.Automation.AutomationElement]::FocusedElement
 $walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
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
@{state='dispatched';verified_sent=$false;clickStartedAt=$clickStartedAt;clickEndedAt=[DateTimeOffset]::Now.ToString('o')} | ConvertTo-Json -Compress
