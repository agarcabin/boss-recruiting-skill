param([long]$WindowHandle=0,[Parameter(Mandatory=$true)][string]$ChatMarker,[Parameter(Mandatory=$true)][string]$Output)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
if(!$WindowHandle){
 $matching=@()
 foreach($proc in @(Get-Process -Name ChatGPT,Codex -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0})){
  try{
   $window=[System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
   $document=$window.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.AndCondition]::new(
    [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document),
    [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$ChatMarker)))
   if($document -and !$document.Current.IsOffscreen){$matching+=@($proc.MainWindowHandle)}
  }catch{}
 }
 if($matching.Count -ne 1){throw 'unique_matching_codex_window_required'}
 $WindowHandle=[long]$matching[0]
}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
$condition=[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Group),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'对话'))
$docCondition=[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$ChatMarker))
$documents=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$docCondition)|Where-Object {$value=$null;$_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value) -and $value.Current.Value -like 'app://*/index.html*'})
if($documents.Count -ne 1 -or $documents[0].Current.IsOffscreen){throw 'unique_matching_chat_document_required'}
$document=$documents[0]
$toolbar=$document.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.AndCondition]::new(
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ToolBar),
 [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'聊天工具栏')))
if(!$toolbar -or !$toolbar.FindFirst([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$ChatMarker))){throw 'active_chat_toolbar_mismatch'}
$scopes=@($document.FindAll([System.Windows.Automation.TreeScope]::Descendants,$condition)|Where-Object {!$_.Current.IsOffscreen})
if($scopes.Count -ne 1){throw 'unique_matching_chat_required'}
$pidValue=$root.Current.ProcessId
$binding=@{kind='uia';hwnd=$WindowHandle;process_id=$pidValue;process_started_at=(Get-Process -Id $pidValue).StartTime.ToUniversalTime().ToString('o');scope_runtime_id=$scopes[0].GetRuntimeId();chat_marker=$ChatMarker;chat_title=$ChatMarker;document_runtime_id=$document.GetRuntimeId();stop_name='停止'}
$file=[IO.Path]::GetFullPath($Output)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($file))|Out-Null
$binding|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $file -Encoding UTF8
& (Join-Path $PSScriptRoot 'codex-stop.ps1') -Binding $file -Action Probe
