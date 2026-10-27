param([Parameter(Mandatory=$true)][string]$Target,[Parameter(Mandatory=$true)][string]$Deadline,[ValidateSet('Invoke','SendText','Probe','Scroll')][string]$Action='Invoke',[string]$TextFile)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$t=Get-Content -LiteralPath $Target -Raw | ConvertFrom-Json
$clickStartedAt=[DateTimeOffset]::Now.ToString('o')
if(!$t.hwnd -or !$t.runtime_id -or !$t.name -or (!$t.candidate_name -and $Action -ne 'Scroll') -or !$t.document_url){throw 'target_identity_required'}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$t.hwnd)
$condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::RuntimeIdProperty,[int[]]$t.runtime_id)
$named=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$t.name)
$elements=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$named)|Where-Object {($_.GetRuntimeId() -join ",") -eq ($t.runtime_id -join ",")})
if($elements.Count -ne 1){throw 'target_runtime_id_not_found'}
$element=$elements[0]
if(!$element -or $element.Current.IsOffscreen -or !$element.Current.IsEnabled -or $element.Current.Name -ne $t.name){throw 'target_stale_or_mismatched'}
if($element.Current.Name -match '举报|不合适|删除'){throw 'forbidden_target'}
$node=$element;$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker;$candidate=($Action -eq 'Scroll');$document=$false
for($i=0;$node -and $i -lt 35;$i++){
 if($t.candidate_name -and $node.Current.Name.Contains([string]$t.candidate_name)){$candidate=$true}
 if($t.candidate_scope_runtime_id -and ($node.GetRuntimeId() -join ",") -eq ($t.candidate_scope_runtime_id -join ",")){
  $identity=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$t.candidate_name)
  if($node.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$identity)){$candidate=$true}
 }
 if($node.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){$v=$null;if($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -eq $t.document_url){$document=$true}}
 $node=$walker.GetParent($node)
}
if(!$candidate -or !$document){throw 'candidate_or_document_mismatch'}
if([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($Deadline)){throw 'run_expired_before_action'}
if($Action -eq 'Probe'){}
elseif($Action -eq 'Scroll'){$scroll=$null;if(!$element.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$scroll)){throw 'scroll_not_supported'};$scroll.Scroll([System.Windows.Automation.ScrollAmount]::NoAmount,[System.Windows.Automation.ScrollAmount]::LargeIncrement)}
elseif($Action -eq 'Invoke'){$invoke=$null;if(!$element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw 'invoke_not_supported'};$clickStartedAt=[DateTimeOffset]::Now.ToString('o');$invoke.Invoke()}
else{
 Add-Type -AssemblyName System.Windows.Forms
 $focus=[System.Windows.Automation.AutomationElement]::FocusedElement
 if(!$focus -or ($focus.GetRuntimeId() -join ',') -ne ($element.GetRuntimeId() -join ',') -or $element.Current.ControlType -ne [System.Windows.Automation.ControlType]::Edit){throw 'chat_input_not_focused'}
 [System.Windows.Forms.Clipboard]::SetText([IO.File]::ReadAllText($TextFile))
 [System.Windows.Forms.SendKeys]::SendWait('^v')
 if([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($Deadline)){throw 'run_expired_before_enter'}
 $clickStartedAt=[DateTimeOffset]::Now.ToString('o');[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
}
@{state='dispatched';verified_sent=$false;clickStartedAt=$clickStartedAt;clickEndedAt=[DateTimeOffset]::Now.ToString('o');bounds=@{x=$element.Current.BoundingRectangle.X;y=$element.Current.BoundingRectangle.Y;width=$element.Current.BoundingRectangle.Width;height=$element.Current.BoundingRectangle.Height}}|ConvertTo-Json -Compress
