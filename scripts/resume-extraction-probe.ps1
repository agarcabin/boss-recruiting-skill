param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [int]$PreviewChars = 800
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Get-TokenEstimate([string]$Text) {
    if ([string]::IsNullOrEmpty($Text)) {
        return 0
    }
    $cjk = ([regex]::Matches($Text, "[\u3400-\u9FFF]")).Count
    return [math]::Ceiling($cjk + (($Text.Length - $cjk) / 4.0))
}

function Get-OutputJson($Value) {
    return $Value | ConvertTo-Json -Depth 6 -Compress
}

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
if ($null -eq $root) {
    throw "无法取得 Codex 窗口 UI Automation 根节点。"
}

$documentCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Document
)
$documents = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    $documentCondition
)

$resume = $null
$documentSummary = New-Object System.Collections.Generic.List[object]
for ($index = 0; $index -lt $documents.Count; $index++) {
    $document = $documents.Item($index)
    $valuePattern = $null
    $url = ""
    if ($document.TryGetCurrentPattern(
        [System.Windows.Automation.ValuePattern]::Pattern,
        [ref]$valuePattern
    )) {
        $url = $valuePattern.Current.Value
    }
    if ($url -like "*zhipin*") {
        $documentSummary.Add([pscustomobject]@{
            name = $document.Current.Name
            url = $url
            offscreen = $document.Current.IsOffscreen
        })
    }
    if ($url -like "*c-resume*") {
        $resume = $document
        break
    }
}

$stopwatch.Stop()
if ($null -eq $resume) {
    $result = [ordered]@{
        state = "refresh_detected"
        reason = "c_resume_document_missing"
        elapsedMs = $stopwatch.ElapsedMilliseconds
        documentCount = $documents.Count
        documents = $documentSummary
    }
    $json = Get-OutputJson $result
    Write-Output $json
    exit 0
}

$rect = $resume.Current.BoundingRectangle
$patterns = @(
    $resume.GetSupportedPatterns() |
        ForEach-Object { $_.ProgrammaticName }
)
$documentText = ""
$textPatternAvailable = $false
$textPattern = $null
if ($resume.TryGetCurrentPattern(
    [System.Windows.Automation.TextPattern]::Pattern,
    [ref]$textPattern
)) {
    $textPatternAvailable = $true
    $documentText = $textPattern.DocumentRange.GetText(-1)
}

$textCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Text
)
$textNodes = $resume.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    $textCondition
)

$allCondition = [System.Windows.Automation.Condition]::TrueCondition
$allDescendants = $resume.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    $allCondition
)
$typeCounts = @{}
for ($index = 0; $index -lt $allDescendants.Count; $index++) {
    $typeName = $allDescendants.Item($index).Current.ControlType.ProgrammaticName.Replace(
        "ControlType.",
        ""
    )
    if (-not $typeCounts.ContainsKey($typeName)) {
        $typeCounts[$typeName] = 0
    }
    $typeCounts[$typeName]++
}

$preview = $documentText.Substring(0, [Math]::Min($PreviewChars, $documentText.Length))
$result = [ordered]@{
    state = "ok"
    refreshDetected = $false
    elapsedMs = $stopwatch.ElapsedMilliseconds
    name = $resume.Current.Name
    url = $documentSummary |
        Where-Object { $_.url -like "*c-resume*" } |
        Select-Object -First 1 -ExpandProperty url
    rect = [ordered]@{
        left = [math]::Round($rect.Left)
        top = [math]::Round($rect.Top)
        width = [math]::Round($rect.Width)
        height = [math]::Round($rect.Height)
    }
    patterns = $patterns
    textPatternAvailable = $textPatternAvailable
    documentTextLength = $documentText.Length
    textNodeCount = $textNodes.Count
    descendantCount = $allDescendants.Count
    descendantTypes = $typeCounts
    containsWorkHistory = $documentText.Contains("工作经历")
    containsResponsibilities = $documentText.Contains("职责")
    containsAchievements = $documentText.Contains("业绩")
    preview = $preview
}

$intermediate = Get-OutputJson $result
$result["responseCharacters"] = $intermediate.Length
$result["estimatedTokens"] = Get-TokenEstimate $intermediate
Write-Output (Get-OutputJson $result)
