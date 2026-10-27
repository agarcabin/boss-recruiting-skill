param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [string]$PythonPath = "",
    [double]$ScrollRatio = 0.75,
    [int]$MaxPages = 20,
    [string]$Run,
    [string]$Db,
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
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$pipeline = Join-Path $PSScriptRoot "resume_image_pipeline.py"


function Invoke-CaptureGuard([scriptblock]$Action) {
    if (-not $Run) { & $Action; return }
    $bytes=[Text.Encoding]::UTF8.GetBytes([IO.Path]::GetFullPath($Db).ToLowerInvariant())
    $sha=[Security.Cryptography.SHA256]::Create()
    try {$hash=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant().Substring(0,24)}finally{$sha.Dispose()}
    $mutex=[Threading.Mutex]::new($false,('Local\CodexRecruiting_'+$hash))
    $held=$false
    try {
        $held=$mutex.WaitOne(5000)
        if(-not $held){throw 'capture_action_lock_timeout'}
        $check=& $PythonPath (Join-Path $PSScriptRoot 'run_safety.py') --db $Db check --run $Run --generation $Generation
        if($LASTEXITCODE -ne 0){throw 'capture_run_stopped'}
        & $Action
    } finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
}

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
    for ($index = 0; $index -lt $documents.Count; $index++) {
        $document = $documents.Item($index)
        $valuePattern = $null
        if (
            $document.TryGetCurrentPattern(
                [System.Windows.Automation.ValuePattern]::Pattern,
                [ref]$valuePattern
            ) -and
            $valuePattern.Current.Value -like "*c-resume*"
        ) {
            return $document
        }
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
    $current = $resume
    for ($depth = 0; $depth -lt 8 -and $null -ne $current; $depth++) {
        $scrollPattern = $null
        if (
            $current.Current.ClassName -eq "resume-detail-wrap" -and
            $current.TryGetCurrentPattern(
                [System.Windows.Automation.ScrollPattern]::Pattern,
                [ref]$scrollPattern
            ) -and
            $scrollPattern.Current.VerticallyScrollable
        ) {
            return [ordered]@{
                present = $true
                resume = $resume
                wrapper = $current
                pattern = $scrollPattern
            }
        }
        $current = $walker.GetParent($current)
    }
    return [ordered]@{
        present = $false
        reason = "resume_detail_wrap_scroll_target_missing"
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
    $stitchJson = & $PythonPath (Join-Path $PSScriptRoot 'managed_helper.py') --db $Db --run $Run --generation $Generation -- $PythonPath $pipeline stitch --pages @pagePaths --offsets $offsetText --output $longPath
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
