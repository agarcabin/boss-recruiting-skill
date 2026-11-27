param([long]$WindowHandle=0,[int]$TimeoutMs=2000)
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'boss-login-notice.ps1')
Dismiss-BossLoginNotice -Handle $WindowHandle -TimeoutMs $TimeoutMs|ConvertTo-Json -Compress
