param([Parameter(Mandatory=$true)][string]$Binding,[ValidateSet('Probe','Stop')][string]$Action='Probe')
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$b=Get-Content -LiteralPath $Binding -Raw | ConvertFrom-Json
if($b.kind -ne 'uia' -or !$b.chat_marker -or !$b.scope_runtime_id -or !$b.hwnd -or !$b.process_id -or !$b.process_started_at){throw 'incomplete_chat_specific_binding'}
$process=Get-Process -Id $b.process_id -ErrorAction Stop
if($process.StartTime.ToUniversalTime().Ticks -ne ([datetime]$b.process_started_at).ToUniversalTime().Ticks){throw 'bound_process_replaced'}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$b.hwnd)
if($root.Current.ProcessId -ne $b.process_id){throw 'bound_window_replaced'}
function Get-BoundScope {
if($b.chat_title){
 $dc=[System.Windows.Automation.AndCondition]::new(
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document),
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$b.chat_title))
 $documents=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc)|Where-Object {!$_.Current.IsOffscreen})
 if($documents.Count -ne 1){throw 'bound_chat_document_not_active'}
 $container=$documents[0]
 $tb=$container.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.AndCondition]::new(
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ToolBar),
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'聊天工具栏')))
 if(!$tb -or !$tb.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$b.chat_title))){throw 'bound_chat_toolbar_mismatch'}
}else{$container=$root}
$scopeCondition=[System.Windows.Automation.AndCondition]::new([System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Group),[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'对话'))
$scopes=@($container.FindAll([System.Windows.Automation.TreeScope]::Descendants,$scopeCondition)|Where-Object {!$_.Current.IsOffscreen -and ($b.chat_title -or (($_.GetRuntimeId() -join ',') -eq ($b.scope_runtime_id -join ',')))})
if($scopes.Count -ne 1){throw 'bound_chat_scope_not_found'}
$scope=$scopes[0]
if(!$b.chat_title){
 $markerCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$b.chat_marker)
 if(!$scope.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$markerCondition)){throw 'bound_chat_marker_not_present'}
}
return $scope
}
function Test-IdleScope($scope){
 $idleButtons=@($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button))|Where-Object {
   !$_.Current.IsOffscreen -and $_.Current.Name -in @('发送','发送消息','开启语音聊天','Send','Start voice chat')})
 return $idleButtons.Count -gt 0
}
$scope=Get-BoundScope
$buttonCondition=[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$b.stop_name))
$buttons=@($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$buttonCondition) | Where-Object {!$_.Current.IsOffscreen -and $_.Current.IsEnabled})
if($buttons.Count -eq 0){
 if(Test-IdleScope $scope){@{state='idle';kind='uia';chat_marker=$b.chat_marker}|ConvertTo-Json -Compress;exit 0}
 throw 'stop_or_idle_state_unavailable'
}
if($buttons.Count -ne 1){throw 'unique_active_stop_button_required'}
$invoke=$null
if(!$buttons[0].TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw 'stop_button_has_no_invoke'}
if($Action -eq 'Stop'){
 $invoke.Invoke()
 $confirmed=$false
 for($i=0;$i -lt 20;$i++){
  Start-Sleep -Milliseconds 100
  try{
   $scope=Get-BoundScope
   $remaining=@($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$buttonCondition) | Where-Object {!$_.Current.IsOffscreen -and $_.Current.IsEnabled})
   if($remaining.Count -eq 0 -and (Test-IdleScope $scope)){$confirmed=$true;break}
  }catch [System.Windows.Automation.ElementNotAvailableException] {continue}
 }
 if(!$confirmed){throw 'turn_interrupt_not_confirmed'}
}
@{state= $(if($Action -eq 'Stop'){'interrupted'}else{'ready'});kind='uia';chat_marker=$b.chat_marker} | ConvertTo-Json -Compress
