param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [int]$MaxRawNodes = 120,
    [int]$MaxDepth = 4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ResumeDiagnosticMouse {
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr value);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
}
"@

[void][ResumeDiagnosticMouse]::SetProcessDpiAwarenessContext([IntPtr](-4))
$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
$documentCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Document
)
$rawWalker = [System.Windows.Automation.TreeWalker]::RawViewWalker

function Get-RuntimeIdText($Element) {
    try {
        return (@($Element.GetRuntimeId()) -join ",")
    } catch {
        return ""
    }
}

function Get-ElementSnapshot($Element) {
    if ($null -eq $Element) {
        return $null
    }
    $rect = $Element.Current.BoundingRectangle
    $patterns = @(
        $Element.GetSupportedPatterns() |
            ForEach-Object { $_.ProgrammaticName }
    )
    return [ordered]@{
        name = $Element.Current.Name
        controlType = $Element.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
        className = $Element.Current.ClassName
        automationId = $Element.Current.AutomationId
        frameworkId = $Element.Current.FrameworkId
        processId = $Element.Current.ProcessId
        nativeWindowHandle = $Element.Current.NativeWindowHandle
        runtimeId = Get-RuntimeIdText $Element
        boundingRectangle = [ordered]@{
            left = [math]::Round($rect.Left)
            top = [math]::Round($rect.Top)
            width = [math]::Round($rect.Width)
            height = [math]::Round($rect.Height)
        }
        isEnabled = $Element.Current.IsEnabled
        isOffscreen = $Element.Current.IsOffscreen
        patterns = $patterns
    }
}

function Get-ParentChain($Element) {
    $chain = New-Object System.Collections.Generic.List[object]
    $current = $Element
    for ($depth = 0; $depth -lt 10 -and $null -ne $current; $depth++) {
        $chain.Add([pscustomobject]@{
            depth = $depth
            name = $current.Current.Name
            controlType = $current.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
            className = $current.Current.ClassName
            automationId = $current.Current.AutomationId
            runtimeId = Get-RuntimeIdText $current
            processId = $current.Current.ProcessId
            nativeWindowHandle = $current.Current.NativeWindowHandle
        })
        $current = $rawWalker.GetParent($current)
    }
    return $chain
}

function Get-RawSubtree($Element, [int]$Limit, [int]$DepthLimit) {
    $queue = New-Object System.Collections.Generic.Queue[object]
    $queue.Enqueue([pscustomobject]@{ element = $Element; depth = 0 })
    $nodes = New-Object System.Collections.Generic.List[object]
    while ($queue.Count -gt 0 -and $nodes.Count -lt $Limit) {
        $item = $queue.Dequeue()
        $element = $item.element
        $depth = [int]$item.depth
        $nodes.Add([pscustomobject]@{
            depth = $depth
            name = $element.Current.Name
            controlType = $element.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
            className = $element.Current.ClassName
            automationId = $element.Current.AutomationId
            runtimeId = Get-RuntimeIdText $element
            isOffscreen = $element.Current.IsOffscreen
        })
        if ($depth -ge $DepthLimit) {
            continue
        }
        $child = $rawWalker.GetFirstChild($element)
        while ($null -ne $child -and $nodes.Count + $queue.Count -lt $Limit) {
            $queue.Enqueue([pscustomobject]@{ element = $child; depth = $depth + 1 })
            $child = $rawWalker.GetNextSibling($child)
        }
    }
    return $nodes
}

function Find-ResumeDocument {
    $documents = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $documentCondition
    )
    for ($index = 0; $index -lt $documents.Count; $index++) {
        $document = $documents.Item($index)
        $valuePattern = $null
        if ($document.TryGetCurrentPattern(
            [System.Windows.Automation.ValuePattern]::Pattern,
            [ref]$valuePattern
        ) -and $valuePattern.Current.Value -like "*c-resume*") {
            return $document
        }
    }
    return $null
}

function Click-Point([int]$X, [int]$Y) {
    [void][ResumeDiagnosticMouse]::SetCursorPos($X, $Y)
    Start-Sleep -Milliseconds 100
    [ResumeDiagnosticMouse]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [ResumeDiagnosticMouse]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 200
}

$resume = Find-ResumeDocument
if ($null -eq $resume) {
    [ordered]@{
        state = "refresh_detected"
        reason = "c_resume_document_missing"
    } | ConvertTo-Json -Depth 6 -Compress
    exit 0
}

$screenWidth = [System.Windows.Forms.SystemInformation]::VirtualScreen.Width
$screenHeight = [System.Windows.Forms.SystemInformation]::VirtualScreen.Height
$resumeRect = $resume.Current.BoundingRectangle
$visibleLeft = [math]::Max(0, [math]::Round($resumeRect.Left))
$visibleRight = [math]::Min($screenWidth, [math]::Round($resumeRect.Right))
$visibleTop = [math]::Max(0, [math]::Round($resumeRect.Top))
$visibleBottom = [math]::Min($screenHeight, [math]::Round($resumeRect.Bottom))
$mainX = [int](($visibleLeft + $visibleRight) / 2)
$mainY = [int]($visibleTop + ($visibleBottom - $visibleTop) * 0.45)
$rightX = [int]($visibleRight + ($screenWidth - $visibleRight) * 0.5)
$rightY = $mainY
$backgroundX = [int][math]::Max(20, $visibleLeft - 150)
$backgroundY = $mainY

$resumeRuntimeId = Get-RuntimeIdText $resume
$points = @(
    [pscustomobject]@{ label = "resume_body"; x = $mainX; y = $mainY },
    [pscustomobject]@{ label = "resume_right"; x = $rightX; y = $rightY },
    [pscustomobject]@{ label = "background"; x = $backgroundX; y = $backgroundY }
)
$pointResults = New-Object System.Collections.Generic.List[object]
$hitElements = @{}
foreach ($point in $points) {
    $element = [System.Windows.Automation.AutomationElement]::FromPoint(
        (New-Object System.Windows.Point($point.x, $point.y))
    )
    $hitElements[$point.label] = $element
    $chain = Get-ParentChain $element
    $insideResume = @(
        $chain | Where-Object { $_.runtimeId -eq $resumeRuntimeId }
    ).Count -gt 0
    $pointResults.Add([ordered]@{
        label = $point.label
        x = $point.x
        y = $point.y
        insideResume = $insideResume
        element = Get-ElementSnapshot $element
        parentChain = $chain
    })
}

$rawSubtree = @()
$bodyHit = $hitElements["resume_body"]
if ($null -ne $bodyHit) {
    $rawSubtree = @(Get-RawSubtree $bodyHit $MaxRawNodes $MaxDepth)
}

$focusResults = New-Object System.Collections.Generic.List[object]
$bodyPoint = $points[0]
$rightPoint = $points[1]
Click-Point $bodyPoint.x $bodyPoint.y
$bodyFocus = [System.Windows.Automation.AutomationElement]::FocusedElement
$focusResults.Add([ordered]@{
    label = "after_body_click"
    element = Get-ElementSnapshot $bodyFocus
    parentChain = Get-ParentChain $bodyFocus
})
Click-Point $rightPoint.x $rightPoint.y
$rightFocus = [System.Windows.Automation.AutomationElement]::FocusedElement
$focusResults.Add([ordered]@{
    label = "after_right_click"
    element = Get-ElementSnapshot $rightFocus
    parentChain = Get-ParentChain $rightFocus
})

$resumeAfter = Find-ResumeDocument
$textPatternAvailable = $false
$valuePatternAvailable = $false
$legacyPatternAvailable = $false
if ($null -ne $bodyHit) {
    $bodySnapshot = Get-ElementSnapshot $bodyHit
    $dummy = $null
    $textPatternAvailable = $bodyHit.TryGetCurrentPattern(
        [System.Windows.Automation.TextPattern]::Pattern,
        [ref]$dummy
    )
    $dummy = $null
    $valuePatternAvailable = $bodyHit.TryGetCurrentPattern(
        [System.Windows.Automation.ValuePattern]::Pattern,
        [ref]$dummy
    )
    $legacyPatternAvailable = @($bodySnapshot.patterns) -contains "LegacyIAccessiblePatternIdentifiers.Pattern"
}

[ordered]@{
    state = if ($null -eq $resumeAfter) { "refresh_detected" } else { "ok" }
    resumeElement = Get-ElementSnapshot $resume
    points = $pointResults
    bodyPatternAvailability = [ordered]@{
        text = $textPatternAvailable
        value = $valuePatternAvailable
        legacy = $legacyPatternAvailable
    }
    focusedAfterClicks = $focusResults
    rawSubtree = $rawSubtree
    resumeStillPresent = $null -ne $resumeAfter
} | ConvertTo-Json -Depth 10 -Compress
