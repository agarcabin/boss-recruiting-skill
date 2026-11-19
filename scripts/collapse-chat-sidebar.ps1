param([Parameter(Mandatory=$true)][string]$ChatTitle)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$resolved=& (Join-Path $PSScriptRoot 'resolve-recruiting-window.ps1') -ChatTitle $ChatTitle | ConvertFrom-Json
if(!$resolved -or $resolved.state -ne 'resolved'){throw 'sidebar_current_chat_unavailable'}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$resolved.window.hwnd)
$condition=[System.Windows.Automation.PropertyCondition]::new(
 [System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
function Read-Sidebar {
 $controls=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$condition)|Where-Object {
  !$_.Current.IsOffscreen -and $_.Current.Name -match '^(Hide sidebar|Close sidebar|隐藏侧边栏|隐藏边栏|收起侧边栏|关闭侧边栏|收起聊天列表|Show sidebar|Open sidebar|显示侧边栏|展开侧边栏|打开侧边栏)$'
 })
 if($controls.Count -ne 1){throw 'sidebar_control_not_unique'}
 $control=$controls[0]
 # Only native host chrome or this exact chat's app document, never BOSS content.
 $cursor=$control;$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
 while($cursor -and ($cursor.GetRuntimeId() -join ',') -ne ($root.GetRuntimeId() -join ',')){
  if($cursor.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){
   $value=$null
   if($cursor.Current.Name -ne $ChatTitle -or !$cursor.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value) -or $value.Current.Value -notlike 'app://*/index.html*'){throw 'sidebar_outside_current_chat'}
   break
  }
  $cursor=$walker.GetParent($cursor)
 }
 return $control
}
$button=Read-Sidebar
$changed=$false
if($button.Current.Name -match '^(Hide|Close|隐藏|收起|关闭)'){
 $expand=$null;$invoke=$null
 if($button.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$expand)){
  $expand.Collapse()
 }elseif($button.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){
  $invoke.Invoke()
 }else{throw 'sidebar_control_action_not_supported'}
 $changed=$true
 for($i=0;$i -lt 8;$i++){
  Start-Sleep -Milliseconds 150
  $button=Read-Sidebar
  if($button.Current.Name -match '^(Show|Open|显示|展开|打开)'){break}
 }
}
if($button.Current.Name -notmatch '^(Show|Open|显示|展开|打开)'){throw 'sidebar_collapse_unconfirmed'}
@{state='collapsed';changed=$changed;chat_title=$ChatTitle}|ConvertTo-Json -Compress
