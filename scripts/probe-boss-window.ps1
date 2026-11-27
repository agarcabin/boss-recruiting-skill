$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')
$null=Get-BossBrowserRoot
$null=Dismiss-BossLoginNotice
$binding=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
@{state='bound';hwnd=$binding.hwnd;process_id=$binding.process_id;binding_id=$binding.binding_id}|ConvertTo-Json -Compress
