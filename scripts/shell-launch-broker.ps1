param(
 [Parameter(Mandatory=$true)][string]$PythonPath,
 [Parameter(Mandatory=$true)][string]$Bootstrap,
 [Parameter(Mandatory=$true)][string]$Request,
 [Parameter(Mandatory=$true)][string]$Token
)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
if($Token -notmatch '^[a-f0-9]{32}$'){throw 'invalid_recruiting_launch_token'}
foreach($path in @($PythonPath,$Bootstrap,$Request)){
 if(!(Test-Path -LiteralPath $path -PathType Leaf)){throw 'launch_broker_file_missing'}
}
$arguments='-X utf8 "'+[IO.Path]::GetFullPath($Bootstrap)+'" --request "'+[IO.Path]::GetFullPath($Request)+'" --token "'+$Token+'" --transport shell'
$shell=New-Object -ComObject 'Shell.Application'
$null=$shell.ShellExecute([IO.Path]::GetFullPath($PythonPath),$arguments,
 [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Bootstrap)),'open',0)
@{state='dispatched';transport='shell'}|ConvertTo-Json -Compress
