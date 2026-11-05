param(
 [ValidateSet('Select','PageJob','ResumePresence','Resume','ResumeFull','Greeting','Next','Close','CoworkerTab')][string]$Action='Select',
 [long]$WindowHandle,[string]$SkipFile,[string]$CardRuntime
)
$OutputEncoding=[Text.UTF8Encoding]::new($false);[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient;Add-Type -AssemblyName UIAutomationTypes
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')

if(!$WindowHandle){
 $null=Get-BossBrowserRoot
 $WindowHandle=[long](Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json).hwnd
}

$root=(Get-BossBrowserRoot $WindowHandle)
$dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
$docs=@()
foreach($d in (Get-BossDocuments $root)){
 $v=$null
 if(!$d.Current.IsOffscreen -and $d.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -match '^https://www\.zhipin\.com/web/(chat/recommend|frame/(recommend|c-resume)/)'){$docs+=@{element=$d;url=$v.Current.Value}}
}
if(!$docs.Count){throw 'boss_document_unavailable'}
function Target($node,$url){return @{browser_binding_id=(Get-BossBindingId);hwnd=$WindowHandle;runtime_id=$node.GetRuntimeId();name=$node.Current.Name;class_name=$node.Current.ClassName;document_url=$url}}
if($Action -eq 'PageJob'){
 $labels=[Collections.Generic.HashSet[string]]::new()
 foreach($class in @('job-select','job-name','position-select','selected-job')){
  $jc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,$class)
  foreach($node in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$jc)){
   if(!$node.Current.IsOffscreen -and $node.Current.Name){[void]$labels.Add($node.Current.Name)}
  }
 }
 @{state=$(if($labels.Count -eq 1){'read'}else{'unknown'});display_name=$(if($labels.Count -eq 1){@($labels)[0]}else{$null});source='directed_job_selector_uia'}|ConvertTo-Json -Compress;exit
}
function Invoker($node){
 $p=$null
 if($node.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p)){return $node}
 $queue=[Collections.Generic.Queue[object]]::new();$queue.Enqueue(@{node=$node;depth=0});$count=0
 while($queue.Count -and $count -lt 100){
  $item=$queue.Dequeue();$count++;$p=$null
  if($item.node.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p) -and $item.node.Current.Name -notmatch '打招呼|继续沟通|举报|不合适|删除|收藏'){return $item.node}
  if($item.depth -ge 4){continue}
  $child=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetFirstChild($item.node)
  while($child){$queue.Enqueue(@{node=$child;depth=$item.depth+1});$child=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetNextSibling($child)}
 }
 return $null
}
if($Action -eq 'Select'){
 $skip=@();if($SkipFile -and (Test-Path -LiteralPath $SkipFile)){$skip=@(Get-Content -LiteralPath $SkipFile -Raw|ConvertFrom-Json)}
 $seen=[Collections.Generic.HashSet[string]]::new();$cards=@();$ordered=@()
 foreach($doc in $docs){
  if($doc.url -like '*c-resume*'){continue}
  $cc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'card-item')
  foreach($card in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cc)){
   $rid=$card.GetRuntimeId() -join ','
   if($card.Current.IsOffscreen -or !$seen.Add($rid)){continue}
   $ordered+=,$rid
   if($rid -in $skip){continue}
   $wrapped=$card.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
   $viewed=@($wrapped|Where-Object {$_.Current.ClassName -match '\b(candidate-card-wrap|card-inner)\b.*\bhas-viewed\b'}).Count -gt 0
   if($viewed){continue}
   $nameNode=@($wrapped|Where-Object {$_.Current.ClassName -match '(^|[- ])name($|[- ])' -and $_.Current.Name -and $_.Current.Name.Length -lt 35}|Select-Object -First 1)
   $avatarName=@($wrapped|Where-Object {$_.Current.ClassName -eq 'avatar' -and $_.Current.Name -and $_.Current.Name.Length -lt 35 -and $_.Current.Name -notmatch '(?i)头像|图片|说明|avatar|profile'}|Select-Object -First 1)
   $name=if($nameNode.Count){$nameNode[0].Current.Name}elseif($avatarName.Count){$avatarName[0].Current.Name}else{'姓名未暴露·卡片'+($cards.Count+1)}
   $open=Invoker $card
   $cards+=@{candidate_id='uia-card:'+$rid;candidate_name=$name;card_runtime=$rid;card_target=(Target $card $doc.url);open_target=$(if($open){Target $open $doc.url}else{$null});hwnd=$WindowHandle;summary=$card.Current.Name}
  }
 }
 if($cards.Count){@{state='candidate';candidate=$cards[0];ordered_runtime_ids=$ordered;resume_open=(@($docs|Where-Object {$_.url -like '*c-resume*'}).Count -gt 0)}|ConvertTo-Json -Depth 7 -Compress}
 else{
  $scroll=@()
  foreach($doc in $docs){$p=$null;if($doc.element.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$p) -and $p.Current.VerticallyScrollable -and $p.Current.VerticalScrollPercent -lt 100){$scroll+=,(Target $doc.element $doc.url)}}
  @{state='no_visible_candidate';scroll_target=$(if($scroll.Count){$scroll[0]}else{$null})}|ConvertTo-Json -Depth 6 -Compress
 }
 exit
}
if($Action -eq 'ResumePresence'){
 $resumeDocs=@($docs|Where-Object {$_.url -like '*c-resume*'})
 # Navigation can observe control structure changes without reading next-person
 # text before the colleague check. Never read Name/TextPattern for this signal.
 $signal=[Collections.Generic.HashSet[string]]::new()
 foreach($doc in $docs|Where-Object {$_.url -notlike '*c-resume*'}){
  $pc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'经历概览')
  foreach($header in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$pc)){
   if($header.Current.IsOffscreen){continue}
   $panel=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($header)
   if(!$panel -or $panel.Current.ClassName -ne 'resume-item-detail'){continue}
   $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
   foreach($node in @($panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc))|Select-Object -First 120){if(!$node.Current.IsOffscreen){[void]$signal.Add(($node.GetRuntimeId() -join ','))}}
  }
 }
 @{state=$(if($resumeDocs.Count){'present'}else{'absent'});hwnd=$WindowHandle;view_signature=(@($signal) -join ';');document_target=$(if($resumeDocs.Count){Target $resumeDocs[0].element $resumeDocs[0].url}else{$null})}|ConvertTo-Json -Depth 6 -Compress;exit
}
if($Action -in @('Resume','ResumeFull')){
 $parts=@();$seen=[Collections.Generic.HashSet[string]]::new()
 foreach($doc in $docs|Where-Object {$_.url -like '*c-resume*'}){
  $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
  foreach($text in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)){
   if(!$text.Current.IsOffscreen -and $text.Current.Name -and $seen.Add(($text.GetRuntimeId() -join ','))){$parts+=,$text.Current.Name}
  }
 }
 $resumeText=$parts -join "`n"
 $complete=$false
 # TextPattern exposes the entire readable document, including below the fold.
 foreach($doc in $docs|Where-Object {$_.url -like '*c-resume*'}){
  $tp=$null
  if($doc.element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$tp)){
   $full=$tp.DocumentRange.GetText(-1)
   if($full){$resumeText=$full;$complete=$true}
  }
 }
 if($Action -eq 'ResumeFull' -and !$complete){
  $collected=[Collections.Generic.HashSet[string]]::new()
  foreach($part in $parts){[void]$collected.Add($part)}
  foreach($doc in $docs|Where-Object {$_.url -like '*c-resume*'}){
   $nodes=@($doc.element)+@($doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::IsScrollPatternAvailableProperty,$true)))
   $ancestor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($doc.element)
   for($level=0;$ancestor -and $level -lt 12;$level++){
    try{Assert-BossBrowserTarget $ancestor $WindowHandle}catch{break}
    $nodes+=,$ancestor
    $ancestor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($ancestor)
   }
   $scrollers=@($nodes|Where-Object {$sp=$null;!$_.Current.IsOffscreen -and $_.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$sp) -and $sp.Current.VerticallyScrollable})
   $preferred=@($scrollers|Where-Object {$_.Current.ClassName -eq 'resume-detail-wrap' -or $_.Current.AutomationId -eq 'resume'})
   if($preferred.Count -eq 1){$scrollers=$preferred}
   if($scrollers.Count -gt 1){throw 'resume_scroll_scope_ambiguous'}
   if(!$scrollers.Count){
    $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
    $allText=@($doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc))
    if($allText.Count -and !@($allText|Where-Object {$_.Current.IsOffscreen -and $_.Current.Name}).Count){$complete=$true}
    continue
   }
   $scroller=$scrollers[0];$sp=$null;[void]$scroller.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$sp)
   $original=$sp.Current.VerticalScrollPercent
   try{
    Assert-BossBrowserTarget $scroller $WindowHandle
    $sp.SetScrollPercent(-1,0)
    for($page=0;$page -lt 40;$page++){
     Start-Sleep -Milliseconds 100
     Assert-BossBrowserTarget $scroller $WindowHandle
     $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
     foreach($node in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)){if(!$node.Current.IsOffscreen -and $node.Current.Name){[void]$collected.Add($node.Current.Name)}}
     if($sp.Current.VerticalScrollPercent -ge 99.9){$complete=$true;break}
     Assert-BossBrowserTarget $scroller $WindowHandle
     $sp.Scroll([System.Windows.Automation.ScrollAmount]::NoAmount,[System.Windows.Automation.ScrollAmount]::LargeIncrement)
    }
   }finally{Assert-BossBrowserTarget $scroller $WindowHandle;$sp.SetScrollPercent(-1,$original)}
  }
  if($collected.Count){$resumeText=@($collected) -join "`n"}
 }
 $parts=@()
 # The user-visible right-hand employment overview can be sufficient for a direct
 # employer/role match. Read that bounded panel before considering a long OCR.
 foreach($doc in $docs|Where-Object {$_.url -notlike '*c-resume*'}){
  $hc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'经历概览')
  foreach($header in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$hc)){
   if($header.Current.IsOffscreen){continue}
   $panel=$header;$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
   for($level=0;$panel -and $level -lt 5;$level++){
    $panel=$walker.GetParent($panel)
    if(!$panel -or $panel.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){break}
    if($panel.Current.BoundingRectangle.Width -gt $doc.element.Current.BoundingRectangle.Width*0.65){break}
    $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
    $texts=@($panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)|Where-Object {!$_.Current.IsOffscreen -and $_.Current.Name})
    if($texts.Count -gt 120){break}
    if($texts.Count -gt 2){
     foreach($text in $texts){if($seen.Add(($text.GetRuntimeId() -join ','))){$parts+=,$text.Current.Name}}
     break
    }
   }
  }
 }
 $resumeDocs=@($docs|Where-Object {$_.url -like '*c-resume*'})
 $detailName='';$identity=''
 foreach($rd in $resumeDocs){
  $nc=[System.Windows.Automation.OrCondition]::new(
   [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'geek-name'),
   [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'name'))
  $nameNode=@($rd.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)|Where-Object {!$_.Current.IsOffscreen -and $_.Current.Name}|Select-Object -First 1)
  if($nameNode.Count){$detailName=$nameNode[0].Current.Name}
  if($rd.url -match '(?:encryptId|encryptGeekId|geekId|resumeId)=([^&]+)'){$identity='resume:'+$Matches[1]}
 }
 if(!$identity -and $resumeText.Length -ge 80){
  $sha=[Security.Cryptography.SHA256]::Create()
  try{$identity='resume:'+([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($detailName+"`n"+$resumeText)))).Replace('-','')}finally{$sha.Dispose()}
 }
 $overviewText=$parts -join "`n"
 @{state='read';read_complete=$complete;candidate_id=$identity;candidate_name=$detailName;keyword_text=(@($resumeText,$overviewText)|Where-Object {$_}) -join "`n";resume_text=$resumeText;overview_text=$overviewText;source='directed_resume_and_overview_uia';hwnd=$WindowHandle;document_target=$(if($resumeDocs.Count){Target $resumeDocs[0].element $resumeDocs[0].url}else{$null})}|ConvertTo-Json -Depth 6 -Compress;exit
}
$hits=@();$seen=[Collections.Generic.HashSet[string]]::new()
foreach($doc in $docs){
 $scope=$doc.element
 if($CardRuntime){
  $cc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'card-item')
  $card=@($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cc)|Where-Object {($_.GetRuntimeId() -join ',') -eq $CardRuntime})
  if(!$card.Count){continue};$scope=$card[0]
 }
 $names=if($Action -eq 'Greeting'){@('打招呼','继续沟通','继续打招呼')}elseif($Action -eq 'Close'){@('关闭')}elseif($Action -eq 'CoworkerTab'){@('同事沟通进度')}else{@()}
 foreach($name in $names){
  $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$name)
  foreach($node in $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)){
   if($node.Current.IsOffscreen -or !$seen.Add(($node.GetRuntimeId() -join ','))){continue}
   if($Action -eq 'Greeting' -and !$CardRuntime -and @($docs|Where-Object {$_.url -like '*c-resume*'}).Count){
    # Locate the floating resume button, excluding same-named list buttons behind it.
    $p=$node;$floating=$false
    for($depth=0;$p -and $depth -lt 10;$depth++){
     if($p.Current.ClassName -match 'resumeGreet|lib-standard-resume|dialog-footer'){$floating=$true;break}
     $p=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($p)
    }
    if(!$floating){continue}
   }
   if($Action -eq 'CoworkerTab'){
    $item=$node;$selected=$false;$tabTarget=$null
    for($i=0;$item -and $i -lt 3;$i++){
     $selection=$null
     if($item.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$selection)){$selected=$selection.Current.IsSelected}
     if($item.Current.ClassName -match '(^|\s)(active|selected)(\s|$)'){$selected=$true}
     $inv=$null;if(!$tabTarget -and $item.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$inv)){$tabTarget=Target $item $doc.url}
     $item=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($item)
    }
    $hits+=@{selected=$selected;target=$tabTarget;label=$name};continue
   }
   $p=$null;$actual=$node
   for($level=0;$actual -and $level -lt 3;$level++){
    if($actual.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p)){$hits+=@{label=$name;target=(Target $actual $doc.url)};break}
    $actual=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($actual)
   }
  }
 }
 if($Action -eq 'Next'){
  $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'turn-btn next')
  foreach($node in $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)){if(!$node.Current.IsOffscreen -and $seen.Add(($node.GetRuntimeId() -join ','))){$hits+=@{target=(Target $node $doc.url)}}}
 }
 if($Action -eq 'Close'){
  # Live BOSS resume X is an unnamed Group, not a button named 关闭.
  $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'close-btn')
  foreach($node in $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)){
   if($node.Current.IsOffscreen){continue}
   $parent=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($node)
   $invoke=$null
   if($parent.Current.ClassName -match '\blib-standard-resume\b' -and $node.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke) -and $seen.Add(($node.GetRuntimeId() -join ','))){$hits+=@{label='关闭';target=(Target $node $doc.url)}}
  }
 }
}
if($hits.Count -eq 1){@{state='found';match=$hits[0]}|ConvertTo-Json -Depth 6 -Compress}else{@{state='unavailable';reason='current_control_not_unique';count=$hits.Count}|ConvertTo-Json -Compress}
