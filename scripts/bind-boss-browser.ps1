param([Parameter(Mandatory=$true)][long]$WindowHandle,[Parameter(Mandatory=$true)][string]$ChatTitle,[Parameter(Mandatory=$true)][string]$TabId,[Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
$process=Get-Process -Id $root.Current.ProcessId
if($process.ProcessName -ne 'Codex'){throw 'external_browser_window_forbidden'}
$dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
$docs=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc))
$chats=@($docs|Where-Object {$v=$null;!$_.Current.IsOffscreen -and $_.Current.Name -eq $ChatTitle -and $_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -like 'app://*/index.html*'})
if($chats.Count -ne 1){throw 'current_codex_chat_not_unique'}
$boss=@($docs|Where-Object {$v=$null; !$_.Current.IsOffscreen -and $_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -match '^https://www\.zhipin\.com(?:/|$)'})
$top=@($boss|Where-Object {
 $cursor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($_);$nested=$false
 while($cursor){if(($cursor.GetRuntimeId() -join ',') -in @($boss|ForEach-Object {$_.GetRuntimeId() -join ','})){$nested=$true;break};$cursor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($cursor)}
 !$nested
})
if($top.Count -ne 1){throw 'unique_current_chat_boss_tab_required'}
$b=@{browser_target='codex_iab';binding_id=[guid]::NewGuid().ToString();tab_id=$TabId;chat_title=$ChatTitle;hwnd=$WindowHandle;process_id=$process.Id;process_started_ticks=$process.StartTime.ToUniversalTime().Ticks.ToString();document_runtime_id=$top[0].GetRuntimeId()}
$json=$b|ConvertTo-Json -Depth 5
[IO.File]::WriteAllText([IO.Path]::GetFullPath($OutputFile),$json,[Text.UTF8Encoding]::new($false))
@{state='bound';binding_file=[IO.Path]::GetFullPath($OutputFile);browser_target='codex_iab'}|ConvertTo-Json -Compress
