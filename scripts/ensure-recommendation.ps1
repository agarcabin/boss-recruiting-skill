$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')
$root=Get-BossBrowserRoot
$null=Dismiss-BossLoginNotice
$value=$null
if(!$root.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value)){throw 'boss_url_unavailable'}
if($value.Current.Value -match '^https://www\.zhipin\.com/web/chat/recommend(?:[/?#]|$)'){
 @{state='ready';navigated=$false}|ConvertTo-Json -Compress;exit
}
$condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'推荐牛人')
$links=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$condition)|Where-Object {
 !$_.Current.IsOffscreen -and $_.Current.IsEnabled -and $_.Current.ControlType -in @([System.Windows.Automation.ControlType]::Hyperlink,[System.Windows.Automation.ControlType]::Button)
})
if($links.Count -ne 1){throw 'recommendation_navigation_not_unique'}
Assert-BossBrowserTarget $links[0]
$invoke=$null
if(!$links[0].TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw 'recommendation_navigation_not_invokable'}
$invoke.Invoke()
for($attempt=0;$attempt -lt 20;$attempt++){
 Start-Sleep -Milliseconds 250
 # Document loss cannot prove which tab replaced it. Keep the original
 # binding and require attention instead of binding a different BOSS tab.
 $root=Get-BossBrowserRoot
 $null=Dismiss-BossLoginNotice
 $value=$null
 if($root.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value) -and $value.Current.Value -match '^https://www\.zhipin\.com/web/chat/recommend(?:[/?#]|$)'){
  @{state='ready';navigated=$true}|ConvertTo-Json -Compress;exit
 }
}
throw 'recommendation_navigation_not_confirmed'
