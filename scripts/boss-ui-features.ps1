param(
 [ValidateSet('Inspect','Favorite','Login','Sidebar')][string]$Action='Inspect',
 [long]$WindowHandle
)
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
if(!$WindowHandle){
 $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
 $matches=@($wins | Where-Object {
  try {$_.Current.NativeWindowHandle -and !$_.Current.IsOffscreen -and (Get-Process -Id $_.Current.ProcessId).ProcessName -in @('Codex','ChatGPT')} catch {$false}
 })
 if($matches.Count -ne 1){@{state='unavailable';reason='unique_codex_window_required';count=$matches.Count}|ConvertTo-Json -Compress;exit}
 $WindowHandle=$matches[0].Current.NativeWindowHandle
}
$root=[System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
$dc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Document)
$documents=@($root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$dc))
$boss=@();$app=@()
foreach($doc in $documents){
 $v=$null
 if($doc.Current.IsOffscreen -or !$doc.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$v)){continue}
 $url=$v.Current.Value
 if($url -match '^https://www\.zhipin\.com/web/(chat/recommend|frame/(recommend|c-resume)/)'){$boss+=@{element=$doc;url=$url}}
 elseif($url -like 'app://*/index.html*'){$app+=@{element=$doc;url=$url}}
}
function Make-Target($element,$url){
 $invoke=$null;$cursor=$element
 for($level=0;$cursor -and $level -lt 4;$level++){
  if($cursor.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$invoke)){
   return @{hwnd=$WindowHandle;runtime_id=$cursor.GetRuntimeId();name=$cursor.Current.Name;class_name=$cursor.Current.ClassName;document_url=$url}
  }
  $cursor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($cursor)
 }
 return $null
}
if($Action -eq 'Inspect'){
 $buttons=@()
 foreach($scope in $app){
  $bc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
  foreach($button in $scope.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$bc)){
   if(!$button.Current.IsOffscreen -and $button.Current.Name -match '(?i)sidebar|side panel|边栏|侧栏|聊天列表'){$buttons+=@{name=$button.Current.Name;runtime_id=$button.GetRuntimeId()}}
  }
 }
 @{state='inspected';hwnd=$WindowHandle;boss_documents=@($boss|ForEach-Object {$_.url});sidebar_buttons=$buttons}|ConvertTo-Json -Depth 5 -Compress;exit
}
if($Action -eq 'Sidebar'){
 $hits=@()
 foreach($scope in $app){
  $bc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
  foreach($button in $scope.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$bc)){
   if($button.Current.IsOffscreen){continue}
   if($button.Current.Name -match '^(Hide sidebar|Close sidebar|隐藏侧边栏|隐藏边栏|收起侧边栏|关闭侧边栏|收起聊天列表)$'){$hits+=@{target=(Make-Target $button $scope.url);state='expanded'}}
   elseif($button.Current.Name -match '^(Show sidebar|Open sidebar|显示侧边栏|展开侧边栏|打开侧边栏)$'){$hits+=@{state='collapsed'}}
  }
 }
 if($hits.Count -eq 1){$hits[0]|ConvertTo-Json -Depth 6 -Compress}else{@{state='unavailable';reason='sidebar_state_not_exposed';count=$hits.Count}|ConvertTo-Json -Compress};exit
}
if($Action -eq 'Favorite'){
 $hits=@();$seen=[Collections.Generic.HashSet[string]]::new()
 foreach($scope in $boss){
  foreach($label in @('已收藏','收藏','取消收藏')){
   $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$label)
   foreach($node in $scope.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)){
    if($node.Current.IsOffscreen){continue}
    $parent=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($node)
    # The user annotated the right-hand dialog-footer/like-icon-and-text control.
    $right=$node.Current.BoundingRectangle.Left -gt ($scope.element.Current.BoundingRectangle.Left+$scope.element.Current.BoundingRectangle.Width*0.5)
    if(!$right -and $node.Current.ClassName -notlike '*like-icon-and-text*' -and $parent.Current.ClassName -notlike '*like-icon-and-text*'){continue}
    $target=Make-Target $node $scope.url
    if(!$target -and $label -in @('已收藏','取消收藏')){
     $target=@{hwnd=$WindowHandle;runtime_id=$node.GetRuntimeId();name=$label;document_url=$scope.url}
    }
    if($target -and $seen.Add(($target.runtime_id -join ','))){$hits+=@{state=$(if($label -in @('已收藏','取消收藏')){'saved'}else{'unsaved'});target=$target;label=$label}}
   }
  }
 }
 if($hits.Count -eq 1){$hits[0]|ConvertTo-Json -Depth 6 -Compress}else{@{state='unavailable';reason='favorite_control_not_unique';count=$hits.Count}|ConvertTo-Json -Compress};exit
}
# Find the already-logged-in message first, then its bounded modal confirmation.
# This handles different dialog class names without acknowledging unrelated prompts.
$dialogs=@();$loginSeen=[Collections.Generic.HashSet[string]]::new()
$tc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
$walker=[System.Windows.Automation.TreeWalker]::RawViewWalker
foreach($scope in $boss){
 foreach($messageNode in $scope.element.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)){
  $message=$messageNode.Current.Name
  if($messageNode.Current.IsOffscreen -or $message.Length -gt 200 -or $message -notmatch '^(提示[：:]?\s*)?(你|您|当前账号)?已(经)?登[录陆]' -or $message -match '异地|其他设备|验证码|风险|安全验证'){continue}
  $panel=$messageNode
  for($level=0;$panel -and $level -lt 6;$level++){
   $panel=$walker.GetParent($panel)
   if(!$panel -or $panel.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document){break}
   $rect=$panel.Current.BoundingRectangle
   if($rect.Width -ge $scope.element.Current.BoundingRectangle.Width*0.96 -and $rect.Height -ge $scope.element.Current.BoundingRectangle.Height*0.8){break}
   $buttons=@();$seenButtons=[Collections.Generic.HashSet[string]]::new()
   foreach($label in @('确定','确认','我知道了')){
    $nc=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty,$label)
    foreach($node in $panel.FindAll([System.Windows.Automation.TreeScope]::Descendants,$nc)){
     if(!$node.Current.IsOffscreen){
      $target=Make-Target $node $scope.url
      if($target -and $seenButtons.Add(($target.runtime_id -join ','))){$buttons+=,$target}
     }
    }
   }
   if($buttons.Count -eq 1){
    if($loginSeen.Add(($buttons[0].runtime_id -join ','))){$dialogs+=@{state='present';target=$buttons[0];message=$message}}
    break
   }
   if($buttons.Count -gt 1){break}
  }
 }
}
if($dialogs.Count -eq 1){$dialogs[0]|ConvertTo-Json -Depth 6 -Compress}else{@{state=$(if(!$dialogs.Count){'absent'}else{'unavailable'});count=$dialogs.Count}|ConvertTo-Json -Compress}
