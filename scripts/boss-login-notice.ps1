# BOSS "account already logged in" tab-modal: fail-closed native dismissal.
#
# Chromium exposes this dialog as a separate RootView window under the host
# window, not as a descendant of the BOSS Document. Enumerate from the host
# handle, match the exact notice text, and dispatch the unique confirm button
# once. Never guess: multiple confirm buttons or an unconfirmed dismissal stop
# the caller.

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$script:BossLoginNoticeConfirmNames=@('确定','确认','OK')

function Test-BossLoginNoticeWindowName {
 param([string]$Name)
 if([string]::IsNullOrWhiteSpace($Name)){return $false}
 return $Name.ToLowerInvariant().Contains('zhipin.com')
}

function Test-BossLoginNoticeBody {
 param([string]$Name)
 if([string]::IsNullOrWhiteSpace($Name)){return $false}
 return [bool]($Name -match '登录过|请勿重复登录')
}

function Test-BossLoginNoticeConfirmName {
 param([string]$Name)
 if([string]::IsNullOrWhiteSpace($Name)){return $false}
 return ($script:BossLoginNoticeConfirmNames -contains $Name.Trim())
}

function Get-BossLoginNoticeField {
 param([object]$Element,[string]$Field)
 try{return $Element.Current.$Field}catch{return $null}
}

function Get-BossLoginNoticeCandidates {
 param([object]$Root)
 if($null -eq $Root){return @()}
 $windowCondition=[System.Windows.Automation.PropertyCondition]::new(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
  [System.Windows.Automation.ControlType]::Window)
 $textCondition=[System.Windows.Automation.PropertyCondition]::new(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
  [System.Windows.Automation.ControlType]::Text)
 $buttonCondition=[System.Windows.Automation.PropertyCondition]::new(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
  [System.Windows.Automation.ControlType]::Button)
 try{$windows=@($Root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$windowCondition))}catch{return @()}
 $result=@()
 foreach($window in $windows){
  $name=Get-BossLoginNoticeField $window 'Name'
  if(!(Test-BossLoginNoticeWindowName $name)){continue}
  $texts=@()
  try{$nodes=@($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$textCondition))}catch{$nodes=@()}
  foreach($node in $nodes){
   $text=Get-BossLoginNoticeField $node 'Name'
   if(Test-BossLoginNoticeBody $text){$texts+=$text}
  }
  if(!$texts.Count){continue}
  $buttons=@()
  try{$nodes=@($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$buttonCondition))}catch{$nodes=@()}
  foreach($node in $nodes){
   $buttonName=Get-BossLoginNoticeField $node 'Name'
   if(!(Test-BossLoginNoticeConfirmName $buttonName)){continue}
   if(Get-BossLoginNoticeField $node 'IsOffscreen'){continue}
   $buttons+=[pscustomobject]@{name=$buttonName;offscreen=$false;element=$node}
  }
  $result+=[pscustomobject]@{
   name=$name
   offscreen=[bool](Get-BossLoginNoticeField $window 'IsOffscreen')
   texts=$texts
   buttons=$buttons
  }
 }
 return $result
}

function Select-BossLoginNoticeTarget {
 param([object[]]$Candidates)
 $targets=@($Candidates|Where-Object {
  if($null -eq $_){return $false}
  if(!(Test-BossLoginNoticeWindowName $_.name)){return $false}
  return @(@($_.texts)|Where-Object {Test-BossLoginNoticeBody $_}).Count -gt 0
 })
 if(!$targets.Count){return $null}
 if($targets.Count -ne 1){throw 'boss_login_notice_dialog_not_unique'}
 $buttons=@($targets[0].buttons|Where-Object {
  $null -ne $_ -and (Test-BossLoginNoticeConfirmName $_.name) -and !$_.offscreen
 })
 if($buttons.Count -ne 1){throw ('boss_login_notice_confirm_not_unique:'+$buttons.Count)}
 return [pscustomobject]@{dialog=$targets[0];button=$buttons[0]}
}

function Invoke-BossLoginNoticeButton {
 param([object]$Button,[scriptblock]$Dispatch=$null)
 if($Dispatch){& $Dispatch $Button;return 'injected'}
 $element=$Button.element
 $legacy=$null;$hasLegacy=$false
 try{$hasLegacy=$element.TryGetCurrentPattern([System.Windows.Automation.LegacyIAccessiblePattern]::Pattern,[ref]$legacy)}catch{$hasLegacy=$false}
 if($hasLegacy -and $null -ne $legacy){
  $action=$null
  try{$action=$legacy.Current.DefaultAction}catch{$action=$null}
  if($action){
   # Dispatch exactly once; a failed MSAA route must not be retried through Invoke.
   $legacy.DoDefaultAction()
   return 'msaa_default_action'
  }
 }
 $invoke=$null
 try{$hasInvoke=$element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)}catch{$hasInvoke=$false}
 if($hasInvoke -and $null -ne $invoke){
  $invoke.Invoke()
  return 'uia_invoke'
 }
 throw 'native_action_pattern_unavailable'
}

function Get-BossLoginNoticeHandle {
 param([long]$Handle=0)
 if($Handle){return $Handle}
 if(!$env:BOSS_BROWSER_BINDING -or !(Test-Path -LiteralPath $env:BOSS_BROWSER_BINDING)){return 0}
 try{
  $binding=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
  return [long]$binding.hwnd
 }catch{return 0}
}

function Dismiss-BossLoginNotice {
 param([long]$Handle=0,[int]$TimeoutMs=2000,[scriptblock]$Dispatch=$null)
 $Handle=Get-BossLoginNoticeHandle $Handle
 if(!$Handle){return @{state='not_found'}}
 try{$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Handle)}catch{throw 'boss_login_notice_host_unavailable'}
 $target=Select-BossLoginNoticeTarget @(Get-BossLoginNoticeCandidates $root)
 if($null -eq $target){return @{state='not_found'}}
 $route=Invoke-BossLoginNoticeButton $target.button $Dispatch
 $deadline=[DateTime]::UtcNow.AddMilliseconds([Math]::Max(0,$TimeoutMs))
 while($true){
  $remaining=@()
  try{
   $fresh=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$Handle)
   $remaining=@(Get-BossLoginNoticeCandidates $fresh|Where-Object {!$_.offscreen})
  }catch{$remaining=@()}
  if(!$remaining.Count){
   return @{state='dismissed';route=$route;dialog=$target.dialog.name}
  }
  if([DateTime]::UtcNow -ge $deadline){break}
  Start-Sleep -Milliseconds 150
 }
 throw 'boss_login_notice_dismiss_unconfirmed'
}
