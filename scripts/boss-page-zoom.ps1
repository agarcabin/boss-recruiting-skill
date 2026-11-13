param([ValidateSet('Read','Set')][string]$Action='Read',[double]$Percent=100,[string]$ExpectedBinding)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')
$root=Get-BossBrowserRoot
$binding=Get-BossBindingId
if($ExpectedBinding -and $binding -ne $ExpectedBinding){throw 'zoom_binding_changed'}
# The managed UIA wrapper does not expose Transform2 in many WebViews. Use the
# current page's own browser toolbar, never an application/window zoom command.
$expandedByUs=$false;$expand=$null
try {
 $b=Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json
 $walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
 $chat=$root
 for($depth=0;$chat -and $depth -lt 16;$depth++){
  $chatUrl=$null
  if($chat.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document -and $chat.Current.Name -eq $b.chat_title -and
     $chat.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$chatUrl) -and $chatUrl.Current.Value -like 'app://*/index.html*'){break}
  $chat=$walker.GetParent($chat)
 }
 if(!$chat -or $depth -ge 16){throw 'bound_chat_chrome_not_found'}
 $rect=$root.Current.BoundingRectangle
 $bc=[System.Windows.Automation.AndCondition]::new(
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button),
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'浏览器选项'))
 $buttons=@($chat.FindAll([System.Windows.Automation.TreeScope]::Descendants,$bc)|Where-Object {
  $r=$_.Current.BoundingRectangle
  !$_.Current.IsOffscreen -and $r.Left -ge $rect.Left -and $r.Right -le $rect.Right -and
  $r.Bottom -le $rect.Top -and $r.Top -ge $rect.Top-140
 })
 if($buttons.Count -ne 1){throw 'page_browser_options_not_unique'}
 $expand=$buttons[0].GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
 if($expand.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded){$expand.Expand();$expandedByUs=$true;Start-Sleep -Milliseconds 100}
 function Get-PageZoomGroup {
  $null=Get-BossBrowserRoot
  if((Get-BossBindingId) -ne $binding){throw 'zoom_binding_changed'}
  $hostRoot=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$b.hwnd)
  $mc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Menu)
  $groups=@()
  $gc=[System.Windows.Automation.AndCondition]::new(
   [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Group),
   [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'缩放'))
  foreach($menu in $hostRoot.FindAll([System.Windows.Automation.TreeScope]::Descendants,$mc)){
   $mr=$menu.Current.BoundingRectangle
   if($menu.Current.IsOffscreen -or $mr.Left -lt $rect.Left-32 -or $mr.Right -gt $rect.Right+32 -or $mr.Top -lt $buttons[0].Current.BoundingRectangle.Bottom-8){continue}
   $groups+=@($menu.FindAll([System.Windows.Automation.TreeScope]::Descendants,$gc)|Where-Object {!$_.Current.IsOffscreen})
  }
  if($groups.Count -ne 1){throw 'page_zoom_group_not_unique'}
  return $groups[0]
 }
 function Read-PagePercent($group){
  $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
  $values=@($group.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)|Where-Object {$_.Current.Name -match '^\d+(?:\.\d+)?%$'}|ForEach-Object {[double]$_.Current.Name.TrimEnd('%')})
  if($values.Count -ne 1){throw 'page_zoom_percent_unavailable'}
  return $values[0]
 }
 function Wait-PageZoomState {
  param($ChangedFrom=$null)
  for($probe=0;$probe -lt 10;$probe++){
   try {
    $g=Get-PageZoomGroup
    $p=Read-PagePercent $g
    if($null -ne $ChangedFrom -and [math]::Abs($p-[double]$ChangedFrom) -lt .1){throw 'page_zoom_not_changed_yet'}
    return @{group=$g;percent=$p}
   } catch {
    if($_.Exception.Message -notmatch 'page_zoom_group_not_unique|page_zoom_percent_unavailable|page_zoom_not_changed_yet|element.*available'){throw}
    if($probe -eq 9){throw}
    if($expand.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded){$expand.Expand()}
    Start-Sleep -Milliseconds 100
   }
  }
 }
 $initial=Wait-PageZoomState;$group=$initial.group;$before=$initial.percent;$current=$before
 if($Action -eq 'Set'){
  if($Percent -lt 25 -or $Percent -gt 500){throw 'zoom_out_of_range'}
  for($attempt=0;[math]::Abs($current-$Percent) -gt .1 -and $attempt -lt 25;$attempt++){
   if([math]::Abs($current-$Percent) -lt 10){throw 'page_zoom_step_not_available'}
   $name=if($current -gt $Percent){'缩小'}else{'放大'}
   $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$name)
   $nodes=@($group.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)|Where-Object {!$_.Current.IsOffscreen -and $_.Current.IsEnabled})
   if($nodes.Count -ne 1){throw 'page_zoom_button_not_unique'}
   $invoke=$nodes[0].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
   $invoke.Invoke();Start-Sleep -Milliseconds 100
   $observed=Wait-PageZoomState $current;$group=$observed.group;$next=$observed.percent
   if([math]::Abs($next-$current) -lt .1){throw 'page_zoom_not_changed'}
   $current=$next
  }
  if([math]::Abs($current-$Percent) -gt .1){throw 'page_zoom_unconfirmed'}
 }
 @{state='read';binding_id=$binding;percent=$current;previous=$before;source='bound_page_browser_menu'}|ConvertTo-Json -Compress
} catch {
 @{state='unsupported';reason='independent_page_zoom_not_supported';detail=$_.Exception.Message;binding_id=$binding;percent=$current}|ConvertTo-Json -Compress
} finally {
 if($expand -and ($expandedByUs -or $Action -eq 'Set')){
  try{
   if($expand.Current.ExpandCollapseState -eq [System.Windows.Automation.ExpandCollapseState]::Expanded){$expand.Collapse();Start-Sleep -Milliseconds 120}
  }catch{}
 }
}
