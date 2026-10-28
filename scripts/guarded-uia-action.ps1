param([Parameter(Mandatory=$true)][string]$Target,[Parameter(Mandatory=$true)][string]$Deadline,[ValidateSet('Invoke','SendText','Probe','Scroll','Key')][string]$Action='Invoke',[string]$TextFile,[ValidateSet('Right','Left','Escape')][string]$Key)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$t=Get-Content -LiteralPath $Target -Raw | ConvertFrom-Json
$clickStartedAt=[DateTimeOffset]::Now.ToString('o')
if(!$t.hwnd -or !$t.runtime_id -or $null -eq $t.name -or (!$t.candidate_name -and $Action -notin @('Scroll','Key')) -or !$t.document_url){throw 'target_identity_required'}
if([string]::IsNullOrWhiteSpace([string]$t.name) -and [string]::IsNullOrWhiteSpace([string]$t.class_name)){throw 'unnamed_target_requires_class_name'}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr][long]$t.hwnd)
$documentCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
$documents=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$documentCondition)
$matchingDocuments=@()
foreach($candidateDocument in $documents){
 $documentValue=$null
 if($candidateDocument.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$documentValue) -and $documentValue.Current.Value -eq $t.document_url){$matchingDocuments+=,$candidateDocument}
}
if($matchingDocuments.Count -ne 1){throw 'target_document_not_unique'}
$documentScope=$matchingDocuments[0]
$conditions=[System.Collections.Generic.List[System.Windows.Automation.Condition]]::new()
$conditions.Add([System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::RuntimeIdProperty,[int[]]$t.runtime_id))
$conditions.Add([System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$t.name))
if(-not [string]::IsNullOrWhiteSpace([string]$t.class_name)){$conditions.Add([System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,[string]$t.class_name))}
$matchCondition=if($conditions.Count -eq 1){$conditions[0]}else{[System.Windows.Automation.AndCondition]::new($conditions.ToArray())}
$elements=if($Action -eq 'Key' -and ($documentScope.GetRuntimeId() -join ",") -eq ($t.runtime_id -join ",")){@($documentScope)}else{@($documentScope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$matchCondition)|Where-Object {($_.GetRuntimeId() -join ",") -eq ($t.runtime_id -join ",")})}
if($elements.Count -ne 1){throw 'target_runtime_id_not_found'}
$element=$elements[0]
if(!$element -or $element.Current.IsOffscreen -or !$element.Current.IsEnabled -or $element.Current.Name -ne $t.name -or ($t.class_name -and $element.Current.ClassName -ne $t.class_name)){throw 'target_stale_or_mismatched'}
if($element.Current.Name -match '举报|不合适|删除'){throw 'forbidden_target'}
$node=$element;$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker;$candidate=($Action -in @('Scroll','Key'));$document=$false
for($i=0;$node -and $i -lt 35;$i++){
 if($t.candidate_name -and $node.Current.Name.Contains([string]$t.candidate_name)){$candidate=$true}
 if($t.candidate_scope_runtime_id -and ($node.GetRuntimeId() -join ",") -eq ($t.candidate_scope_runtime_id -join ",")){
  $identity=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,[string]$t.candidate_name)
  if($node.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$identity)){$candidate=$true}
  # Canvas resumes expose no name. Navigation alone can bind to the current
  # resume document inside the exact overlay; safe_action checks the active ledger key.
  if($Action -in @('Invoke','Probe') -and $t.class_name -in @('turn-btn next','turn-btn prev') -and
     $element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Group -and
     $node.Current.ClassName -like 'lib-standard-resume *' -and $t.navigation_resume_runtime_id){
   $overlayRuntime=($node.GetRuntimeId() -join ',')
   $resumeMatches=@($documents|Where-Object {
    $resumeValue=$null
    $resumeValid=($_.GetRuntimeId() -join ',') -eq ($t.navigation_resume_runtime_id -join ',') -and
    !$_.Current.IsOffscreen -and
    $_.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$resumeValue) -and
    $resumeValue.Current.Value -like 'https://www.zhipin.com/web/frame/c-resume/*'
    $resumeAncestor=$_;$sameOverlay=$false
    if($resumeValid){for($j=0;$resumeAncestor -and $j -lt 8;$j++){
     if(($resumeAncestor.GetRuntimeId() -join ',') -eq $overlayRuntime){$sameOverlay=$true;break}
     $resumeAncestor=$walker.GetParent($resumeAncestor)
    }}
    $resumeValid -and $sameOverlay
   })
   if($resumeMatches.Count -eq 1){$candidate=$true}
  }
 }
 if($node.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){$v=$null;if($node.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -eq $t.document_url){$document=$true}}
 $node=$walker.GetParent($node)
}
if(!$candidate -or !$document){throw 'candidate_or_document_mismatch'}
if([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($Deadline)){throw 'run_expired_before_action'}
if($Action -eq 'Probe'){}
elseif($Action -eq 'Scroll'){$scroll=$null;if(!$element.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$scroll)){throw 'scroll_not_supported'};$scroll.Scroll([System.Windows.Automation.ScrollAmount]::NoAmount,[System.Windows.Automation.ScrollAmount]::LargeIncrement)}
elseif($Action -eq 'Invoke'){$invoke=$null;if(!$element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){throw 'invoke_not_supported'};$clickStartedAt=[DateTimeOffset]::Now.ToString('o');$invoke.Invoke()}
elseif($Action -eq 'Key'){
 if(!$Key){throw 'key_required'}
 $focusNode=[System.Windows.Automation.AutomationElement]::FocusedElement;$focusInDocument=$false
 for($i=0;$focusNode -and $i -lt 35;$i++){
  if($focusNode.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){$v=$null;if($focusNode.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -eq $t.document_url){$focusInDocument=$true;break}}
  $focusNode=$walker.GetParent($focusNode)
 }
 if(!$focusInDocument){throw 'keyboard_focus_outside_target_document'}
 Add-Type -AssemblyName System.Windows.Forms
 $keyToken=@{Right='{RIGHT}';Left='{LEFT}';Escape='{ESC}'}[$Key]
 $clickStartedAt=[DateTimeOffset]::Now.ToString('o');[System.Windows.Forms.SendKeys]::SendWait($keyToken)
}
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
