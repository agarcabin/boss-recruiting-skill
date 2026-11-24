param(
 [ValidateSet('Start','Remove')][string]$Action='Start',
 [Parameter(Mandatory=$true)][string]$TaskName,
 [string]$PythonPath,[string]$Bootstrap,[string]$Request,[string]$Token
)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
if($TaskName -notmatch '^CodexRecruitingLaunch-[a-f0-9]{32}$'){throw 'invalid_recruiting_launch_task'}
$service=New-Object -ComObject 'Schedule.Service'
$service.Connect()
$folder=$service.GetFolder('\')
if($Action -eq 'Remove'){
 $folder.DeleteTask($TaskName,0)
 @{state='removed'}|ConvertTo-Json -Compress
 exit
}
if($Token -notmatch '^[a-f0-9]{32}$'){throw 'invalid_recruiting_launch_token'}
foreach($path in @($PythonPath,$Bootstrap,$Request)){
 if(!$path -or !(Test-Path -LiteralPath $path -PathType Leaf)){throw 'launch_broker_file_missing'}
}
$definition=$service.NewTask(0)
$definition.RegistrationInfo.Description='Same-user on-demand recruiting worker. No triggers; removed after the worker exits.'
$definition.Principal.LogonType=3  # Current interactive user; no password or elevation.
$definition.Principal.RunLevel=0
$definition.Settings.Hidden=$true
$definition.Settings.ExecutionTimeLimit='PT0S'
$definition.Settings.DisallowStartIfOnBatteries=$false
$definition.Settings.StopIfGoingOnBatteries=$false
$definition.Settings.MultipleInstances=2
$taskAction=$definition.Actions.Create(0)
$taskAction.Path=[IO.Path]::GetFullPath($PythonPath)
$taskAction.Arguments='-X utf8 "'+[IO.Path]::GetFullPath($Bootstrap)+'" --request "'+[IO.Path]::GetFullPath($Request)+'" --token "'+$Token+'"'
$taskAction.WorkingDirectory=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Bootstrap))
$task=$folder.RegisterTaskDefinition($TaskName,$definition,2,$null,$null,3,$null)
try {
 [void]$task.Run($null)
} catch {
 try{$folder.DeleteTask($TaskName,0)}catch{}
 throw
}
@{state='dispatched';transport='task_scheduler';task=$TaskName}|ConvertTo-Json -Compress
