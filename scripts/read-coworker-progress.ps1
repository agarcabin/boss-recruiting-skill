param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [string]$DocumentUrlLike = "*zhipin.com/web/chat/recommend*",
    [Parameter(Mandatory = $true)][switch]$CoworkerTabConfirmed
)

# Read-only, directed UIA. Caller first verifies/selects the visible coworker tab.
# No CUA, DOM, page scripts, clipboard, navigation, clicking or scrolling here.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Emit-Observation([string]$State, [string]$Timestamp, [string]$Evidence) {
    [pscustomobject]@{
        state = $State
        first_greeting_at = $Timestamp
        evidence = $Evidence
    } | ConvertTo-Json -Depth 4 -Compress
}

if (-not $CoworkerTabConfirmed) {
    Emit-Observation "unavailable" "" "coworker_tab_not_confirmed"
    exit
}

try {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
    $documentCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Document)
    $documents = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $documentCondition)
    $matchingDocuments = @()
    foreach ($document in $documents) {
        $value = $null
        if ($document.Current.Name -eq "BOSS直聘" -and
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
    if ($headers.Count -ne 1) { throw "coworker_header_not_unique" }
    $header = $headers[0]
    $headerRect = $header.Current.BoundingRectangle
    $documentRect = $scope.Current.BoundingRectangle
    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $panel = $header
    $texts = @()
    $records = @()
    $foundPanel = $false
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
            $scroll.Current.VerticallyScrollable -and $scroll.Current.VerticalScrollPercent -gt 0) {
            throw "coworker_panel_not_at_top"
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
    $first = $records[0]
    # Identify the first visual entry, never sort by date or inspect a later row instead.
    $bottom = if ($records.Count -gt 1) { $records[1].rect.Top } else { $panel.Current.BoundingRectangle.Bottom }
    $firstTexts = @($texts | Where-Object { $_.rect.Top -ge $first.rect.Top -and $_.rect.Top -lt $bottom })
    $dates = @($firstTexts | ForEach-Object {
        [regex]::Matches($_.name, '\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?') |
            ForEach-Object { $_.Value }
    } | Select-Object -Unique)
    if ($dates.Count -ne 1) { throw "first_coworker_time_missing_or_ambiguous" }
    Emit-Observation "first_record" $dates[0] ("UIA:同事沟通进度首条；" + $first.name + "；" + $dates[0])
}
catch {
    Emit-Observation "unavailable" "" $_.Exception.Message
}
