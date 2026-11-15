# Resolve a fresh menu/button for every probe; never send Escape to the page.
function Close-PageZoomMenu {
 param([Parameter(Mandatory=$true)][scriptblock]$Probe,[int]$Attempts=8,[int]$DelayMs=100)
 $last='menu_remains_visible'
 for($attempt=0;$attempt -lt $Attempts;$attempt++){
  try {
   $view=& $Probe
   if(!$view.expanded -and !$view.menu_visible){return}
   & $view.collapse
  } catch {
   $last=$_.Exception.Message
   if($last -match 'binding_changed|codex_iab|bound_chat|page_browser_options_not_unique'){throw}
  }
  if($DelayMs -gt 0){Start-Sleep -Milliseconds $DelayMs}
 }
 $view=& $Probe
 if($view.expanded -or $view.menu_visible){throw ('page_zoom_menu_not_closed: '+$last)}
}
