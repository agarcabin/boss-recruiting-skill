param([Parameter(Mandatory=$true)][string]$ChatTitle)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$desktop=[System.Windows.Automation.AutomationElement]::RootElement
$windows=$desktop.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
$hits=[Collections.Generic.List[object]]::new()
$dc=[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$ChatTitle))
foreach($window in $windows){
 try{
  if($window.Current.IsOffscreen -or !$window.Current.NativeWindowHandle){continue}
  $process=Get-Process -Id $window.Current.ProcessId -ErrorAction Stop
  if($process.ProcessName -notin @('Codex','ChatGPT')){continue}
  $docs=@($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc)|Where-Object {
   $v=$null; !$_.Current.IsOffscreen -and $_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -like 'app://*/index.html*'
  })
  if($docs.Count -eq 1){$hits.Add([pscustomobject]@{hwnd=$window.Current.NativeWindowHandle;process_id=$window.Current.ProcessId;process=$process.ProcessName;chat_title=$ChatTitle;document_runtime_id=$docs[0].GetRuntimeId()})}
 }catch [System.Windows.Automation.ElementNotAvailableException]{continue}
}
if($hits.Count -ne 1){@{state='unavailable';reason='unique_visible_chat_window_required';count=$hits.Count}|ConvertTo-Json -Compress;exit 1}
@{state='resolved';window=$hits[0]}|ConvertTo-Json -Depth 5 -Compress
