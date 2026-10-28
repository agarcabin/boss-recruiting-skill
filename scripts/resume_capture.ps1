param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$PythonPath = "",
    [string]$SafetyPythonPath = "",
    [double]$ScrollRatio = 0.75,
    [int]$MaxPages = 20,
    [string]$Run,
    [string]$LedgerDb,
    [int]$Generation = 0,
    [switch]$KeepPages
)

$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ResumeCaptureDpi {
    [DllImport("user32.dll")]
    public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
}
"@

[void][ResumeCaptureDpi]::SetProcessDpiAwarenessContext([IntPtr](-4))

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    $bundledPython = Join-Path $PSScriptRoot "..\runtime\win-x64\python\python.exe"
    $PythonPath = if (Test-Path -LiteralPath $bundledPython) {
        [System.IO.Path]::GetFullPath($bundledPython)
    }
    else {
        "python"
    }
}
if ([string]::IsNullOrWhiteSpace($SafetyPythonPath)) {
    $SafetyPythonPath = $PythonPath
}
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$pipeline = Join-Path $PSScriptRoot "resume_image_pipeline.py"


function Invoke-CaptureGuard([scriptblock]$Action) {
    if (-not $Run) { & $Action; return }
    $bytes=[Text.Encoding]::UTF8.GetBytes([IO.Path]::GetFullPath($LedgerDb).ToLowerInvariant())
    $sha=[Security.Cryptography.SHA256]::Create()
    try {$hash=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant().Substring(0,24)}finally{$sha.Dispose()}
    $mutex=[Threading.Mutex]::new($false,('Local\CodexRecruiting_'+$hash))
    $held=$false
    try {
        $held=$mutex.WaitOne(5000)
        if(-not $held){throw 'capture_action_lock_timeout'}
        $check=& $SafetyPythonPath (Join-Path $PSScriptRoot 'run_safety.py') --db $LedgerDb check --run $Run --generation $Generation
        if($LASTEXITCODE -ne 0){throw 'capture_run_stopped'}
        & $Action
    } finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
}

$script:CaptureResumeDocument = $null
function Find-ResumeDocument {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
    if ($null -eq $root) {
        return $null
    }
    $documentCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Document
    )
    $documents = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $documentCondition
    )
    $visibleResumes = New-Object System.Collections.Generic.List[object]
    for ($index = 0; $index -lt $documents.Count; $index++) {
        $document = $documents.Item($index)
        $valuePattern = $null
        if (
            $document.TryGetCurrentPattern(
                [System.Windows.Automation.ValuePattern]::Pattern,
                [ref]$valuePattern
            ) -and
            $valuePattern.Current.Value -like "https://www.zhipin.com/web/frame/c-resume/*" -and
            -not $document.Current.IsOffscreen
        ) {
            $visibleResumes.Add($document)
        }
    }
    if ($visibleResumes.Count -gt 1) { throw "resume_document_ambiguous" }
    if ($visibleResumes.Count -eq 1) {
        if ($null -ne $script:CaptureResumeDocument -and
            (($script:CaptureResumeDocument.GetRuntimeId() -join ',') -ne ($visibleResumes[0].GetRuntimeId() -join ','))) {
            throw "resume_document_changed_during_capture"
        }
        $script:CaptureResumeDocument = $visibleResumes[0]
        return $script:CaptureResumeDocument
    }
    # Chromium can omit a live nested iframe from FindAll. Revalidate the SAME
    # cached element and its bounded raw ancestry; never retry scrolling/reload.
    if ($null -ne $script:CaptureResumeDocument) {
        try {
            $cached=$script:CaptureResumeDocument; $value=$null
            if ($cached.Current.IsOffscreen -or
                -not $cached.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$value) -or
                $value.Current.Value -notlike 'https://www.zhipin.com/web/frame/c-resume/*') { return $null }
            $ancestor=$cached; $rootKey=($root.GetRuntimeId() -join ',')
            for($depth=0; $ancestor -and $depth -lt 35; $depth++) {
                if(($ancestor.GetRuntimeId() -join ',') -eq $rootKey) { return $cached }
                $ancestor=[System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent($ancestor)
            }
        } catch [System.Windows.Automation.ElementNotAvailableException] { return $null }
    }
    return $null
}

function Get-ResumeScrollContext {
    $resume = Find-ResumeDocument
    if ($null -eq $resume) {
        return [ordered]@{
            present = $false
            reason = "c_resume_document_missing"
        }
    }
    $walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
    $candidates = New-Object System.Collections.Generic.List[object]
    $seen = New-Object 'System.Collections.Generic.HashSet[string]'

    function Add-ResumeCandidate($Element, [string]$Locator) {
        if ($null -eq $Element) { return }
        try {
            $runtimeKey = (@($Element.GetRuntimeId()) -join ",")
            if ([string]::IsNullOrWhiteSpace($runtimeKey) -or -not $seen.Add($runtimeKey)) { return }
            $scrollPattern = $null
            if (
                $Element.TryGetCurrentPattern(
                    [System.Windows.Automation.ScrollPattern]::Pattern,
                    [ref]$scrollPattern
                ) -and
                $scrollPattern.Current.VerticallyScrollable
            ) {
                $priority = if ($Element.Current.ClassName -eq "resume-detail-wrap") { 0 }
                    elseif ($Element.Current.AutomationId -eq "resume") { 1 }
                    elseif ($Element -eq $resume) { 2 }
                    else { 3 }
                $candidates.Add([pscustomobject]@{
                    element = $Element
                    pattern = $scrollPattern
                    locator = $Locator
                    priority = $priority
                    runtimeKey = $runtimeKey
                })
            }
        } catch { }
    }

    # The resume surface may be exposed as a nested c-resume document containing
    # div#resume (AutomationId=resume), while older views expose its scroll owner
    # as an ancestor named resume-detail-wrap. Probe both directions without
    # focusing the page or scanning the recommendation document.
    $current = $resume
    for ($depth = 0; $depth -lt 8 -and $null -ne $current; $depth++) {
        if (
            $current.Current.ClassName -eq "resume-detail-wrap" -or
            $current.Current.AutomationId -eq "resume" -or
            $current -eq $resume
        ) { Add-ResumeCandidate $current "ancestor:$depth" }
        $current = $walker.GetParent($current)
    }

    foreach ($property in @(
        [pscustomobject]@{ name = "ClassName"; value = "resume-detail-wrap" },
        [pscustomobject]@{ name = "AutomationId"; value = "resume" }
    )) {
        $propertyInfo = if ($property.name -eq "ClassName") {
            [System.Windows.Automation.AutomationElement]::ClassNameProperty
        } else {
            [System.Windows.Automation.AutomationElement]::AutomationIdProperty
        }
        $condition = New-Object System.Windows.Automation.PropertyCondition($propertyInfo, $property.value)
        $matches = $resume.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
        for ($index = 0; $index -lt $matches.Count; $index++) {
            Add-ResumeCandidate $matches.Item($index) "descendant:$($property.name)=$($property.value)"
            $current = $walker.GetParent($matches.Item($index))
            for ($depth = 0; $depth -lt 8 -and $null -ne $current -and $current -ne $resume; $depth++) {
                if ($current.Current.ClassName -eq "resume-detail-wrap") {
                    Add-ResumeCandidate $current "resume-owner-of:$($property.name)"
                }
                $current = $walker.GetParent($current)
            }
        }
    }

    if ($candidates.Count -gt 0) {
        $bestPriority = ($candidates | Measure-Object -Property priority -Minimum).Minimum
        $best = @($candidates | Where-Object { $_.priority -eq $bestPriority })
        if ($best.Count -eq 1) {
            return [ordered]@{
                present = $true
                resume = $resume
                wrapper = $best[0].element
                pattern = $best[0].pattern
                locator = $best[0].locator
            }
        }
        return [ordered]@{
            present = $false
            reason = "resume_scroll_target_ambiguous"
            candidates = $best.Count
        }
    }
    return [ordered]@{
        present = $false
        reason = "resume_scroll_target_missing_after_layer_fallbacks"
    }
}

function Set-ResumeScrollPercent([double]$Percent) {
    $context = Get-ResumeScrollContext
    if (-not $context.present) {
        throw $context.reason
    }
    Invoke-CaptureGuard {
        $context.pattern.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll,$Percent)
    }
    Start-Sleep -Milliseconds 650
    $after = Get-ResumeScrollContext
    if (-not $after.present) {
        throw $after.reason
    }
    return $after
}

function Get-CaptureGeometry($Context) {
    $documentRect = $Context.resume.Current.BoundingRectangle
    $wrapperRect = $Context.wrapper.Current.BoundingRectangle
    $left = [int][math]::Round($wrapperRect.Left)
    $top = [int][math]::Round($wrapperRect.Top)
    $width = [int][math]::Min(
        [math]::Round($documentRect.Width),
        [math]::Round($wrapperRect.Width)
    )
    $visibleBottom = [int][math]::Min(
        [int]$screen.Bottom,
        [int][math]::Round($wrapperRect.Bottom)
    )
    $height = [int][math]::Min(
        [int][math]::Round($wrapperRect.Height),
        $visibleBottom - $top
    )
    return [ordered]@{
        left = $left
        top = $top
        width = $width
        height = $height
    }
}

function Save-Screenshot([string]$Path, $Geometry) {
    $bitmap = New-Object System.Drawing.Bitmap($Geometry.width, $Geometry.height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen(
            $Geometry.left,
            $Geometry.top,
            0,
            0,
            $bitmap.Size,
            [System.Drawing.CopyPixelOperation]::SourceCopy
        )
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$startedAt = Get-Date
$top = Set-ResumeScrollPercent 0
if ([double]$top.pattern.Current.VerticalScrollPercent -gt 0.2) {
    throw "resume_not_at_top"
}
$viewSizePercent = [double]$top.pattern.Current.VerticalViewSize
if ($viewSizePercent -le 0 -or $viewSizePercent -ge 100) {
    throw "unexpected_resume_view_size"
}

$geometry = Get-CaptureGeometry $top
$contentHeight = [double]$geometry.height / ($viewSizePercent / 100.0)
$scrollRange = [math]::Max(1.0, $contentHeight - $geometry.height)
$targetShift = $geometry.height * $ScrollRatio
$stepPercent = ($targetShift / $scrollRange) * 100.0
$pagePaths = New-Object System.Collections.Generic.List[string]
$offsets = New-Object System.Collections.Generic.List[int]
$currentPercent = 0.0
$bottomConfirmed = $false

for ($page = 1; $page -le $MaxPages; $page++) {
    $context = Get-ResumeScrollContext
    if (-not $context.present) {
        throw $context.reason
    }
    $currentPercent = [double]$context.pattern.Current.VerticalScrollPercent
    $offset = [int][math]::Round($scrollRange * ($currentPercent / 100.0))
    $path = Join-Path $OutputDir ("resume-page-{0:D2}.png" -f $page)
    Save-Screenshot $path $geometry
    $pagePaths.Add($path)
    $offsets.Add($offset)
    if ($currentPercent -ge 99.9) {
        $bottomConfirmed = $true
        break
    }
    $next = [double][math]::Min(100.0, $currentPercent + $stepPercent)
    if ($next -le $currentPercent + 0.01) {
        break
    }
    $nextContext = Set-ResumeScrollPercent $next
    if (
        [double]$nextContext.pattern.Current.VerticalScrollPercent -le $currentPercent + 0.01 -and
        [double]$nextContext.pattern.Current.VerticalScrollPercent -lt 99.9
    ) {
        break
    }
}

if (-not $bottomConfirmed) {
    throw "resume_bottom_not_confirmed"
}

$longPath = Join-Path $OutputDir "resume-long.png"
$offsetText = ($offsets | ForEach-Object { [string]$_ }) -join ","
if ($Run) {
 $stitchJson = & $PythonPath (Join-Path $PSScriptRoot 'managed_helper.py') --db $LedgerDb --run $Run --generation $Generation -- $PythonPath $pipeline stitch --pages @pagePaths --offsets $offsetText --output $longPath
} else {
    $stitchJson = & $PythonPath $pipeline stitch --pages @pagePaths --offsets $offsetText --output $longPath
}
if ($LASTEXITCODE -ne 0) {
    throw "resume_stitch_failed"
}
$stitch = $stitchJson | ConvertFrom-Json
$pageFilesRemoved = $false
if (-not $KeepPages) {
    foreach ($pagePath in $pagePaths) {
        if (Test-Path -LiteralPath $pagePath) {
            Remove-Item -LiteralPath $pagePath -Force
        }
    }
    $pageFilesRemoved = $true
}
$completedAt = Get-Date
$result = [ordered]@{
    state = "captured"
    startedAt = $startedAt.ToString("o")
    completedAt = $completedAt.ToString("o")
    pageCount = $pagePaths.Count
    pages = @($pagePaths)
    offsets = @($offsets)
    longImage = $stitch.image
    width = $stitch.width
    height = $stitch.height
    viewSizePercent = [math]::Round($viewSizePercent, 4)
    scrollStepPercent = [math]::Round($stepPercent, 4)
    bottomConfirmed = $bottomConfirmed
    pageFilesRemoved = $pageFilesRemoved
}
$resultJson = $result | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText(
    (Join-Path $OutputDir "resume-capture.json"),
    $resultJson + "`n",
    (New-Object System.Text.UTF8Encoding($false))
)
$resultJson
