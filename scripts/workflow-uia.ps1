param(
 [ValidateSet('Select','FilterState','LayoutState','PageJob','ResumePresence','Resume','ResumeFull','PreferredLocation','Greeting','Next','Close','CoworkerTab','RelatedClose','CardOpen')][string]$Action='Select',
 [long]$WindowHandle,[string]$SkipFile,[string]$CardRuntime
)
$OutputEncoding=[Text.UTF8Encoding]::new($false);[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient;Add-Type -AssemblyName UIAutomationTypes
if(!('BossUiaDpi' -as [type])){
 Add-Type 'using System;using System.Runtime.InteropServices;public static class BossUiaDpi{[DllImport("user32.dll")]public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr v);}'
}
[void][BossUiaDpi]::SetThreadDpiAwarenessContext([IntPtr](-4))
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')
. (Join-Path $PSScriptRoot 'coworker-tab-selection.ps1')
. (Join-Path $PSScriptRoot 'filter-control.ps1')

if(!$WindowHandle){
 $null=Get-BossBrowserRoot
 $WindowHandle=[long](Get-Content -LiteralPath $env:BOSS_BROWSER_BINDING -Raw -Encoding UTF8|ConvertFrom-Json).hwnd
}

$root=(Get-BossBrowserRoot $WindowHandle)
$null=Dismiss-BossLoginNotice -Handle $WindowHandle
$dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
$docs=@()
foreach($d in (Get-BossDocuments $root)){
 $v=$null
 if(!$d.Current.IsOffscreen -and $d.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v) -and $v.Current.Value -match '^https://www\.zhipin\.com/web/(chat/recommend|frame/(recommend|c-resume)/)'){$docs+=@{element=$d;url=$v.Current.Value}}
}
if(!$docs.Count){throw 'boss_document_unavailable'}
function Target($node,$url){return @{browser_binding_id=(Get-BossBindingId);hwnd=$WindowHandle;runtime_id=$node.GetRuntimeId();name=$node.Current.Name;class_name=$node.Current.ClassName;document_url=$url}}
if($Action -eq 'PreferredLocation'){
 $headerCondition=[System.Windows.Automation.OrCondition]::new([System.Windows.Automation.Condition[]]@(
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'牛人分析器'),
  [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,'BOSS牛人分析器')
 ))
 $headers=@();$headerIds=[Collections.Generic.HashSet[string]]::new()
 foreach($doc in $docs|Where-Object {$_.url -notlike '*c-resume*'}){
  foreach($node in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$headerCondition)){
   if(!$node.Current.IsOffscreen -and $headerIds.Add(($node.GetRuntimeId() -join ','))){$headers+=,$node}
  }
 }
 if($headers.Count -ne 1){@{state='unknown';reason='unique_analyzer_panel_unavailable'}|ConvertTo-Json -Compress;exit}
 $walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
 $cursor=$headers[0];$panel=$null;$insideCard=$false
 for($level=0;$cursor -and $level -lt 12;$level++){
  if($cursor.Current.ClassName -match 'card-item|resume-item|resume-text'){ $insideCard=$true;break }
  if($cursor.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){break}
  if($level -gt 0 -and !$cursor.Current.IsOffscreen -and $cursor.Current.BoundingRectangle.Width -le $root.Current.BoundingRectangle.Width*0.65){$panel=$cursor}
  $cursor=$walker.GetParent($cursor)
 }
 if($insideCard -or !$panel){@{state='unknown';reason='analyzer_scope_unconfirmed'}|ConvertTo-Json -Compress;exit}
 $labels=@();$hiddenLabel=$false;$seenLabels=[Collections.Generic.HashSet[string]]::new()
 $textCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
 $panelTexts=@($panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$textCondition))
 if($panelTexts.Count -gt 120){@{state='unknown';reason='analyzer_scope_too_broad'}|ConvertTo-Json -Compress;exit}
 foreach($node in $panelTexts){
   if($node.Current.Name -match '^偏好地点(?:\s|[：:]|$)'){
    if($node.Current.IsOffscreen){$hiddenLabel=$true}
    elseif($seenLabels.Add(($node.GetRuntimeId() -join ','))){$labels+=,$node}
   }
 }
 if($labels.Count -eq 0){
  $complete=($panel.Current.ItemStatus -in @('ready','complete','loaded') -or @($panelTexts|Where-Object {!$_.Current.IsOffscreen -and $_.Current.Name -in @('分析完成','解析完成')}).Count -gt 0)
  $unread=@($panelTexts|Where-Object {$_.Current.Name -and $_.Current.IsOffscreen}).Count -gt 0
  $loading=@($panelTexts|Where-Object {$_.Current.Name -match '加载中|分析中|正在解析|展开更多'}).Count -gt 0
  $expandCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::IsExpandCollapsePatternAvailableProperty,$true)
  foreach($node in $panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$expandCondition)){
   $expander=$null
   if($node.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$expander) -and $expander.Current.ExpandCollapseState -in @([System.Windows.Automation.ExpandCollapseState]::Collapsed,[System.Windows.Automation.ExpandCollapseState]::PartiallyExpanded)){$unread=$true}
  }
  $scroll=$null
  $canScroll=$panel.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$scroll) -and $scroll.Current.VerticallyScrollable
  $scrollCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::IsScrollPatternAvailableProperty,$true)
  foreach($node in $panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$scrollCondition)){
   $childScroll=$null
   if($node.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$childScroll) -and $childScroll.Current.VerticallyScrollable){$canScroll=$true}
  }
  $absent=$complete -and !$hiddenLabel -and !$unread -and !$loading -and !$canScroll
  @{state=$(if($absent){'absent'}else{'unknown'});source='directed_analyzer_preference';reason=$(if($absent){'completed_analyzer_has_no_preference_field'}else{'analyzer_not_completely_inspected'})}|ConvertTo-Json -Compress;exit
 }
 if($labels.Count -ne 1){@{state='unknown';reason='preference_label_not_unique'}|ConvertTo-Json -Compress;exit}
 $label=$labels[0];$text=($label.Current.Name -replace '^偏好地点[：:\s]*','').Trim()
 if(!$text){
  $parent=$walker.GetParent($label)
  if($parent -and $parent.Current.ControlType -ne [System.Windows.Automation.ControlType]::Document -and $parent.Current.BoundingRectangle.Width -le $root.Current.BoundingRectangle.Width*0.65){
   $rowTexts=@($parent.FindAll([System.Windows.Automation.TreeScope]::Descendants,$textCondition)|Where-Object {!$_.Current.IsOffscreen -and $_.Current.Name})
   $next=$walker.GetNextSibling($label)
   if($rowTexts.Count -eq 2 -and $next -and !$next.Current.IsOffscreen -and $next.Current.ControlType -eq [System.Windows.Automation.ControlType]::Text -and ($next.GetRuntimeId() -join ',') -eq ($rowTexts[1].GetRuntimeId() -join ',')){$text=$next.Current.Name}
  }
 }
 if($text -match '(?:现居|年龄|性别|薪资|期望职位|工作地点|任职|籍贯)\s*[：:]'){$text=''}
 @{state=$(if($text){'present'}else{'unknown'});text=$text;source='directed_analyzer_preference';label_runtime_id=$label.GetRuntimeId()}|ConvertTo-Json -Depth 4 -Compress;exit
}
if($Action -in @('FilterState','LayoutState')){
 $buttons=@();$seenButtons=[Collections.Generic.HashSet[string]]::new()
 $fc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'filter-label-wrap')
 foreach($doc in $docs|Where-Object {$_.url -notlike '*c-resume*'}){
  foreach($node in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$fc)){
   if(!$node.Current.IsOffscreen -and $seenButtons.Add(($node.GetRuntimeId() -join ','))){$buttons+=,$node}
  }
 }
 # BOSS exposes the filter label as Text on some layouts, not Button.
 foreach($type in @([System.Windows.Automation.ControlType]::Button,[System.Windows.Automation.ControlType]::Text)){
  if($buttons.Count){break}
  $condition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,$type)
  foreach($doc in $docs|Where-Object {$_.url -notlike '*c-resume*'}){
   foreach($node in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$condition)){
    if(!$node.Current.IsOffscreen -and (Test-BossFilterLabel $node.Current.Name) -and $seenButtons.Add(($node.GetRuntimeId() -join ','))){$buttons+=,$node}
   }
  }
 }
 if($buttons.Count -ne 1){@{state='unknown';reason=$(if($buttons.Count){'filter_control_not_unique'}else{'filter_control_not_found'});match_count=$buttons.Count}|ConvertTo-Json -Compress;exit}
 $button=$buttons[0];$rect=$button.Current.BoundingRectangle;$view=$root.Current.BoundingRectangle
 if($Action -eq 'LayoutState'){
  $headerFits=(!$button.Current.IsOffscreen -and $rect.Left -ge $view.Left -and $rect.Right -le $view.Right -and $rect.Bottom -le $view.Bottom -and $rect.Top -ge $view.Top)
  $cardFits=$true
  $cc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'card-item')
  foreach($doc in $docs|Where-Object {$_.url -notlike '*c-resume*'}){
   foreach($card in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cc)){
    if($card.Current.IsOffscreen){continue}
    $cr=$card.Current.BoundingRectangle
    if($cr.Left -lt $view.Left-2 -or $cr.Right -gt $view.Right+2){$cardFits=$false}
   }
  }
  @{state='read';fits=($headerFits -and $cardFits);header_fits=$headerFits;cards_fit_horizontally=$cardFits}|ConvertTo-Json -Compress;exit
 }
 $labels=@($button.Current.Name)
 $tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
 foreach($node in $button.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)){if(!$node.Current.IsOffscreen){$labels+=,$node.Current.Name}}
 $counts=@($labels|ForEach-Object {[regex]::Matches($_,'\d+')|ForEach-Object {[int]$_.Value}}|Select-Object -Unique)
 if($counts.Count -gt 1){@{state='unknown';reason='filter_count_ambiguous'}|ConvertTo-Json -Compress;exit}
 @{state='read';count=$(if($counts.Count){$counts[0]}else{0});has_number=($counts.Count -gt 0)}|ConvertTo-Json -Compress;exit
}
if($Action -eq 'RelatedClose'){
 $cc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'boss-popup__close')
 $hits=@()
 foreach($node in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cc)){
  if($node.Current.IsOffscreen){continue}
  $wrapper=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($node)
  $dialog=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($wrapper)
  if($wrapper.Current.ClassName -match '\banonymous-geek-guide-list-wrapper\b' -and $dialog.Current.ClassName -match '(^| )active($| )' -and $dialog.Current.ClassName -notmatch 'deactive'){
   $hits+=@{label='Close related recommendations';target=(Target $node 'https://www.zhipin.com/web/chat/recommend')}
  }
 }
 if($hits.Count -eq 1){@{state='found';match=$hits[0]}|ConvertTo-Json -Depth 6 -Compress}else{@{state='unavailable';count=$hits.Count}|ConvertTo-Json -Compress}
 exit
}
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
if($Action -eq 'CardOpen'){
 $hits=@();$seen=[Collections.Generic.HashSet[string]]::new()
 foreach($doc in $docs){
  if($doc.url -like '*c-resume*'){continue}
  foreach($card in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)){
   $classes=$card.Current.ClassName -split '\s+'
   if(!($classes -contains 'card-item') -and !($classes -contains 'candidate-card-wrap')){continue}
   $rid=$card.GetRuntimeId() -join ','
   if($rid -ne $CardRuntime -or $card.Current.IsOffscreen -or !$seen.Add($rid)){continue}
   $open=Invoker $card
   if($open){$hits+=@{target=(Target $open $doc.url)}}
  }
 }
 if($hits.Count -eq 1){@{state='found';match=$hits[0]}|ConvertTo-Json -Depth 6 -Compress}else{@{state='unavailable';count=$hits.Count}|ConvertTo-Json -Compress}
 exit
}
if($Action -eq 'Select'){
 $skip=@();if($SkipFile -and (Test-Path -LiteralPath $SkipFile)){$skip=@(Get-Content -LiteralPath $SkipFile -Raw|ConvertFrom-Json)}
 $skip=@($skip|Where-Object {$_ -is [string]})
 $seen=[Collections.Generic.HashSet[string]]::new();$cards=@();$ordered=@();$scroll=@()
 foreach($doc in $docs){
  if($doc.url -like '*c-resume*'){continue}
  $cc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'card-item')
  foreach($card in $doc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cc)){
   if($card.Current.IsOffscreen){continue}
   if($card.Current.Name -match '当前职位可升级曝光效果|您的职位更新未满24小时|去升级|热搜牛人推荐|广告牛人推荐|广告.*牛人推荐|广告推荐|查看更多'){continue}
   $ancestor=$card;$scrollPercent=-1
   for($depth=0;$ancestor -and $depth -lt 10;$depth++){
    $sp=$null
    if($ancestor.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern,[ref]$sp) -and $sp.Current.VerticallyScrollable){
     $scrollPercent=$sp.Current.VerticalScrollPercent
     if($scrollPercent -lt 100){$scroll+=,(Target $ancestor $doc.url)}
     break
    }
    $ancestor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($ancestor)
   }
   $units=@();$child=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetFirstChild($card)
   while($child){
    if(($child.Current.ClassName -split '\s+') -contains 'candidate-card-wrap'){$units+=,$child}
    $child=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetNextSibling($child)
   }
   if(!$units.Count){$units=@($card)}
   $viewport=$doc.element.Current.BoundingRectangle
   foreach($unit in $units){
    $rid=$unit.GetRuntimeId() -join ','
    if(!$seen.Add($rid)){continue}
    if(($unit.Current.ClassName -split '\s+') -contains 'anonymous-geek-guide-card'){continue}
    if($unit.Current.Name -eq '广告'){continue}
    $wrapped=$unit.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
    if(@($wrapped|Where-Object {$_.Current.Name -eq '广告'}).Count){continue}
    $ordered+=,$rid
    if($rid -in $skip){continue}
    $viewed=@($wrapped|Where-Object {$_.Current.ClassName -match '\b(candidate-card-wrap|card-inner)\b.*\bhas-viewed\b'}).Count -gt 0 -or $unit.Current.ClassName -match '\bhas-viewed\b'
    if($viewed){continue}
    $nameNode=@($wrapped|Where-Object {$_.Current.ClassName -match '(^|[- ])name($|[- ])' -and $_.Current.Name -and $_.Current.Name.Length -lt 35}|Select-Object -First 1)
    $avatarName=@($wrapped|Where-Object {$_.Current.ClassName -eq 'avatar' -and $_.Current.Name -and $_.Current.Name.Length -lt 35 -and $_.Current.Name -notmatch '(?i)头像|图片|说明|avatar|profile'}|Select-Object -First 1)
    $actionButton=@($wrapped|Where-Object {$_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button -and $_.Current.Name -in @('打招呼','继续沟通','继续打招呼')}|Select-Object -First 1)
    $fallbackName=@($wrapped|Where-Object {$_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Text -and $_.Current.Name}|ForEach-Object {
      $candidateName=($_.Current.Name -replace '\s*[.。]\s*要获取缺失的图片说明.*$','').Trim()
      if($candidateName -and $candidateName -notmatch '^(面议|\d.*K|\d+岁|\d+年|.*活跃$|初中及以下|高中|中专/中技|大专|本科|离职-|在职-|温州|普工|组装|操作工|打招呼)$' -and $candidateName.Length -lt 30){$candidateName}
    }|Select-Object -First 1)
    if(!$nameNode.Count -and !$avatarName.Count -and !$actionButton.Count){continue}
    $name=if($nameNode.Count){$nameNode[0].Current.Name}elseif($avatarName.Count){$avatarName[0].Current.Name}elseif($fallbackName.Count){$fallbackName[0]}else{'姓名未暴露·卡片'+($cards.Count+1)}
    $open=Invoker $unit
    $rect=$unit.Current.BoundingRectangle
    $business='';$aid=$unit.Current.AutomationId
    if($aid -match '^(?:geek|candidate|resume)[-_]([A-Za-z0-9_-]{12,})$'){$business=$Matches[1]}
    $visibleWidth=[math]::Max(0,[math]::Min($rect.Right,$viewport.Right)-[math]::Max($rect.Left,$viewport.Left))
    $visibleHeight=[math]::Max(0,[math]::Min($rect.Bottom,$viewport.Bottom)-[math]::Max($rect.Top,$viewport.Top))
    $summary=($wrapped|Where-Object {$_.Current.Name}|ForEach-Object {$_.Current.Name}) -join "`n"
    if(!$summary){$summary=$card.Current.Name}
    $cards+=@{candidate_id=$(if($business){'boss-geek:'+$business}else{'uia-card:'+$rid});business_id=$business;candidate_name=$name;card_runtime=$rid;card_target=(Target $unit $doc.url);open_target=$(if($open){Target $open $doc.url}else{$null});hwnd=$WindowHandle;summary=$summary;readable_text=$summary;scroll_percent=$scrollPercent;bounds=@{x=$rect.X;y=$rect.Y;width=$rect.Width;height=$rect.Height};fully_visible=($visibleWidth -gt 0 -and $visibleHeight -gt 0)}
   }
  }
 }
 if($cards.Count){$cards=@($cards|Sort-Object @{Expression={[math]::Round($_.bounds.y/18)}},@{Expression={$_.bounds.x}});@{state='candidate';candidate=$cards[0];candidates=$cards;scroll_target=$(if($scroll.Count){$scroll[0]}else{$null});ordered_runtime_ids=$ordered;resume_open=(@($docs|Where-Object {$_.url -like '*c-resume*'}).Count -gt 0)}|ConvertTo-Json -Depth 7 -Compress}
 else{
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
 @{state=$(if($resumeDocs.Count){'present'}else{'absent'});hwnd=$WindowHandle;view_signature=(@($signal) -join ';');document_target=$(if($resumeDocs.Count){Target $resumeDocs[-1].element $resumeDocs[-1].url}else{$null})}|ConvertTo-Json -Depth 6 -Compress;exit
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
   if($full){$resumeText=(@($resumeText,$full)|Where-Object {$_}) -join "`n";$complete=$true}
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
  $sectionConditions=[System.Windows.Automation.Condition[]]@('经历概览','期望职位','期望岗位','求职期望','个人优势','工作经历','教育经历','项目经历','实习经历','自我评价','专业技能','资格证书'|ForEach-Object {
   [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$_)
  })
  $hc=[System.Windows.Automation.OrCondition]::new($sectionConditions)
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
     $selection=$null;$patternSelected=$false
     if($item.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$selection)){$patternSelected=$selection.Current.IsSelected}
     $selected=Test-CoworkerTabSelection $selected $patternSelected $item.Current.ClassName
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
  # The resume drawer X is an unnamed close-btn under boss-layer__lock-scroll.
  # Several hidden resume panes can stay in the tree; the last one is the top.
  $lastClose=$null
  if(@($docs|Where-Object {$_.url -like '*c-resume*'}).Count){
   $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty,'close-btn')
   foreach($closeDoc in $docs){
    foreach($node in $closeDoc.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)){
     if($node.Current.IsOffscreen){continue}
     $parent=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($node)
     if($parent.Current.ClassName -match 'boss-layer__lock-scroll|lib-standard-resume'){
      $lastClose=@{label='关闭';target=(Target $node $closeDoc.url)}
     }
    }
   }
  }
  if($lastClose){$hits=@($lastClose)}
 }
}
if($hits.Count -eq 1){@{state='found';match=$hits[0]}|ConvertTo-Json -Depth 6 -Compress}else{@{state='unavailable';reason='current_control_not_unique';count=$hits.Count}|ConvertTo-Json -Compress}
