$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
. (Join-Path $PSScriptRoot 'boss-login-notice.ps1')

function Assert-True($Condition,[string]$Message) {
 if(!$Condition){throw $Message}
}

function New-Candidate([string]$Name,[string[]]$Texts,[object[]]$Buttons) {
 return [pscustomobject]@{name=$Name;offscreen=$false;texts=$Texts;buttons=$Buttons}
}

function New-Button([string]$Name) {
 return [pscustomobject]@{name=$Name;offscreen=$false;element=$null}
}

$checks=0

# Text and name matching stays narrow: only the known login notice is handled.
Assert-True (Test-BossLoginNoticeBody '您的账号已经登录过了，请勿重复登录。') 'login_notice_text_not_matched'
Assert-True (Test-BossLoginNoticeBody '请勿重复登录') 'short_notice_text_not_matched'
Assert-True (!(Test-BossLoginNoticeBody '确定要退出登录吗？')) 'unrelated_dialog_text_matched'
Assert-True (Test-BossLoginNoticeWindowName 'www.zhipin.com 显示') 'zhipin_window_not_matched'
Assert-True (!(Test-BossLoginNoticeWindowName 'www.example.com 显示')) 'foreign_window_matched'
$checks++

# A non-target popup with a confirm button must not be selected.
$candidates=@(New-Candidate 'www.zhipin.com 显示' @('确定要退出登录吗？') @(New-Button '确定'))
Assert-True ($null -eq (Select-BossLoginNoticeTarget $candidates)) 'non_target_popup_selected'
$checks++

# The unique confirm button is dispatched exactly once.
$candidates=@(New-Candidate 'www.zhipin.com 显示' @('您的账号已经登录过了，请勿重复登录。') @(New-Button '确定'))
$target=Select-BossLoginNoticeTarget $candidates
Assert-True ($null -ne $target) 'target_not_selected'
$script:dispatches=0
$route=Invoke-BossLoginNoticeButton $target.button {param($Button) $script:dispatches++}
Assert-True ($script:dispatches -eq 1) ('button_dispatch_count:'+$script:dispatches)
Assert-True ($route -eq 'injected') ('dispatch_route:'+$route)
$checks++

# Multiple confirm buttons stop the flow instead of guessing.
$candidates=@(New-Candidate 'www.zhipin.com 显示' @('您的账号已经登录过了，请勿重复登录。') @((New-Button '确定'),(New-Button '确认')))
$rejected=$false
try{$null=Select-BossLoginNoticeTarget $candidates}catch{
 if($_.Exception.Message -notlike 'boss_login_notice_confirm_not_unique*'){throw}
 $rejected=$true
}
Assert-True $rejected 'multiple_confirm_buttons_not_rejected'
$checks++

# Missing or non-confirm buttons also fail closed.
$candidates=@(New-Candidate 'www.zhipin.com 显示' @('您的账号已经登录过了，请勿重复登录。') @(New-Button '取消'))
$rejected=$false
try{$null=Select-BossLoginNoticeTarget $candidates}catch{
 if($_.Exception.Message -notlike 'boss_login_notice_confirm_not_unique*'){throw}
 $rejected=$true
}
Assert-True $rejected 'missing_confirm_button_not_rejected'
$checks++

@{state='passed';checks=$checks}|ConvertTo-Json -Compress
