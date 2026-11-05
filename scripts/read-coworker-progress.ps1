param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [string]$DocumentUrlLike = "*zhipin.com/web/chat/recommend*",
    [switch]$CoworkerTabConfirmed
)

# Read-only, directed UIA. Caller first verifies/selects the visible coworker tab.
# No CUA, DOM, page scripts, clipboard, navigation, clicking or scrolling here.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
. (Join-Path $PSScriptRoot 'boss-browser-binding.ps1')


function Emit-Observation([string]$State, [string]$Timestamp, [string]$Evidence, [object[]]$Entries=@(), [bool]$Complete=$false) {
    [pscustomobject]@{
        state = $State
        first_greeting_at = $Timestamp
        evidence = $Evidence
        lookup_completed = ($State -eq "not_found")
        records = @($Entries)
        records_complete = $Complete
    } | ConvertTo-Json -Depth 6 -Compress
}

try {
    $root = (Get-BossBrowserRoot $WindowHandle)
    $documentCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Document)
    $documents = (Get-BossDocuments $root)
    $matchingDocuments = @()
    foreach ($document in $documents) {
        $value = $null
        if ($document.Current.Name -in @("BOSS直聘","推荐牛人") -and
            $document.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$value) -and
            $value.Current.Value -like $DocumentUrlLike -and -not $document.Current.IsOffscreen) {
            $matchingDocuments += $document
        }
    }
    if ($matchingDocuments.Count -ne 1) { throw "coworker_document_not_unique" }
    $scope = $matchingDocuments[0]
    $headerCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, "同事沟通进度")
    $headers = @($scope.FindAll([System.Windows.Automation.TreeScope]::Descendants, $headerCondition) |
        Where-Object { -not $_.Current.IsOffscreen })
    if ($headers.Count -eq 0) {
        $fallbackHeaders=New-Object System.Collections.Generic.List[object]
        $seenHeaders=New-Object 'System.Collections.Generic.HashSet[string]'
        foreach($other in $documents){
            $otherValue=$null
            if($other.Current.Name -notin @('BOSS直聘','推荐牛人') -or $other.Current.IsOffscreen -or
               -not $other.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$otherValue) -or
               $otherValue.Current.Value -notmatch '^https://www\.zhipin\.com/web/(chat/recommend(?:[?]|$)|frame/(recommend|c-resume)/)'){continue}
            foreach($found in $other.FindAll([System.Windows.Automation.TreeScope]::Descendants,$headerCondition)){
                if(!$found.Current.IsOffscreen -and $seenHeaders.Add(($found.GetRuntimeId() -join ','))){
                    $fallbackHeaders.Add([pscustomobject]@{header=$found;document=$other})
                }
            }
        }
        if($fallbackHeaders.Count -eq 0){
            Emit-Observation "not_found" "" "UIA:唯一可见起始BOSS文档及当前实际存在的主推荐/推荐iframe/简历iframe均定向查询同事沟通进度，未找到；按用户指定视为未沟通"
            exit
        }
        if($fallbackHeaders.Count -ne 1){throw 'coworker_header_not_unique'}
        $scope=$fallbackHeaders[0].document
        $headers=@($fallbackHeaders[0].header)
    }
    if ($headers.Count -ne 1) { throw "coworker_header_not_unique" }
    if (-not $CoworkerTabConfirmed) { throw "coworker_tab_not_confirmed" }
    $header = $headers[0]
    $headerRect = $header.Current.BoundingRectangle
    $documentRect = $scope.Current.BoundingRectangle
    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $panel = $header
    $texts = @()
    $records = @()
    $foundPanel = $false
    $historyComplete = $true
    $textCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Text)
    for ($level = 0; $level -lt 6; $level++) {
        $panel = $walker.GetParent($panel)
        if ($null -eq $panel -or $panel.Current.ControlType -eq [System.Windows.Automation.ControlType]::Document) { break }
        $rect = $panel.Current.BoundingRectangle
        # Never escalate a missing panel into a resume/page-wide scan.
        if ($rect.Width -gt ($documentRect.Width * 0.65) -or $rect.Height -gt ($documentRect.Height * 0.65)) { break }
        $scroll = $null
        if ($panel.TryGetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern, [ref]$scroll) -and
            $scroll.Current.VerticallyScrollable) {
            $historyComplete = $false
        }
        $nodes = $panel.FindAll([System.Windows.Automation.TreeScope]::Descendants, $textCondition)
        if ($nodes.Count -gt 120) { throw "coworker_panel_scope_too_large" }
        $texts = @($nodes | Where-Object {
            -not $_.Current.IsOffscreen -and $_.Current.BoundingRectangle.Top -ge $headerRect.Top
        } | ForEach-Object {
            [pscustomobject]@{ name = $_.Current.Name; rect = $_.Current.BoundingRectangle }
        })
        $records = @($texts | Where-Object { $_.name -match '向\s*Ta\s*发起沟通' } |
            Sort-Object @{Expression={$_.rect.Top}}, @{Expression={$_.rect.Left}})
        if ($records.Count -gt 0) { $foundPanel = $true; break }
        if (@($texts | Where-Object { $_.name -match '^(暂无(同事)?沟通(记录|进度)?|还没有同事.*沟通|暂无记录)$' }).Count -gt 0) {
            Emit-Observation "empty" "" "UIA:已选同事沟通进度，限定面板内明确显示无记录"
            exit
        }
    }
    if (-not $foundPanel) { throw "coworker_first_record_not_readable" }
    $entries=@()
    for($index=0;$index -lt $records.Count;$index++){
        $entry=$records[$index]
        $bottom=if($index+1 -lt $records.Count){$records[$index+1].rect.Top}else{$panel.Current.BoundingRectangle.Bottom}
        $entryTexts=@($texts|Where-Object {$_.rect.Top -ge $entry.rect.Top -and $_.rect.Top -lt $bottom})
        $dates=@($entryTexts|ForEach-Object {
            [regex]::Matches($_.name,'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?')|ForEach-Object {$_.Value}
        }|Select-Object -Unique)
        $timestamp=if($dates.Count -eq 1){$dates[0]}else{''}
        if(!$timestamp){$historyComplete=$false}
        $entries+=@{greeting_at=$timestamp;evidence=($entryTexts.name -join '；')}
    }
    # Offscreen records or load-more controls prevent an all-old conclusion.
    if(@($nodes|Where-Object {$_.Current.IsOffscreen -and $_.Current.Name -match '向\s*Ta\s*发起沟通'}).Count){$historyComplete=$false}
    if(@($texts|Where-Object {$_.name -match '加载更多|查看更多|展开更多'}).Count){$historyComplete=$false}
    Emit-Observation 'records' $entries[0].greeting_at ("UIA:同事沟通进度逐条检查，共$($entries.Count)条；"+($entries.evidence -join '；')) $entries $historyComplete
}
catch {
    Emit-Observation "unavailable" "" $_.Exception.Message
}
