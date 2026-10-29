param(
    [Parameter(Mandatory = $true)][int]$X,
    [Parameter(Mandatory = $true)][int]$Y,
    [int]$StartX,
    [int]$StartY,
    [ValidateRange(100, 15000)][int]$DurationMs = 1400,
    [ValidateRange(0.0, 30.0)][double]$Jitter = 2.5,
    [ValidateRange(0, 80)][int]$OvershootPx = 6,
    [ValidateRange(0, 6)][int]$WanderCount = 2,
    [ValidateRange(20, 500)][int]$WanderRadius = 140,
    [ValidateRange(0.0, 1.0)][double]$BurstChance = 0.35,
    [ValidateRange(0.0, 1.0)][double]$PauseChance = 0.18,
    [ValidateRange(0, 250)][int]$MaxPauseMs = 90,
    [ValidateRange(0, 3)][int]$MaxIdleClicks = 0,
    [ValidateRange(0.0, 1.0)][double]$IdleClickChance = 0.25,
    [ValidateRange(0, 5)][int]$MaxIdleHovers = 0,
    [ValidateRange(0.0, 1.0)][double]$IdleHoverChance = 0.4,
    [ValidateRange(0.0, 1.0)][double]$FalseStartChance = 0.35,
    [ValidateRange(1000, 5000)][int]$PostClickMoveMs = 1000,
    [ValidateRange(40, 400)][int]$PostClickMoveRadiusPx = 160,
    [string[]]$ForbiddenNames = @("举报", "不合适", "删除"),
    [string[]]$ForbiddenClassNames = @("btn-report", "btn-quxiao"),
    [string]$SafeZonesPath,
    [string]$ContentBounds,
    [IntPtr]$WindowHandle = [IntPtr]::Zero,
    [ValidateSet("Left", "Right")][string]$Button = "Left",
    [int]$Seed = 0,
    [switch]$NoClick,
    [switch]$DryRun,
    [string]$GuardDeadline,
    [string]$GuardTarget,
    [switch]$IncludePath
)

Set-StrictMode -Version Latest
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class NativeMouseTrajectory
{
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT
    {
        public int X;
        public int Y;
    }

    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT point);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    public static extern int GetSystemMetrics(int index);

    [DllImport("user32.dll")]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsZoomed(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool attach);

    [DllImport("user32.dll")]
    public static extern IntPtr SetFocus(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int command);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);
}
"@

$uiaAvailable = $true
try {
    Add-Type -AssemblyName WindowsBase
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
}
catch {
    $uiaAvailable = $false
}

[void][NativeMouseTrajectory]::SetProcessDPIAware()

if (-not $DryRun -and ($WindowHandle -eq [IntPtr]::Zero -or [string]::IsNullOrWhiteSpace($ContentBounds))) {
    throw "实际移动或点击必须提供 WindowHandle 和 ContentBounds。"
}

$point = New-Object NativeMouseTrajectory+POINT
if (-not [NativeMouseTrajectory]::GetCursorPos([ref]$point)) {
    throw "获取鼠标当前位置失败。"
}

$useExplicitStart = $PSBoundParameters.ContainsKey("StartX") -and $PSBoundParameters.ContainsKey("StartY")
$startX = if ($useExplicitStart) { $StartX } else { $point.X }
$startY = if ($useExplicitStart) { $StartY } else { $point.Y }

if (-not $DryRun -and $WindowHandle -ne [IntPtr]::Zero) {
    if (-not [NativeMouseTrajectory]::IsWindow($WindowHandle)) {
        throw "WindowHandle 不是有效的顶层窗口。"
    }

    if ([NativeMouseTrajectory]::GetForegroundWindow() -ne $WindowHandle) {
        if (-not [NativeMouseTrajectory]::IsZoomed($WindowHandle)) {
            [void][NativeMouseTrajectory]::ShowWindow($WindowHandle, 3)
            throw "目标窗口原本未最大化，已切换为最大化；请重新获取页面坐标和内容边界后再执行。未发送鼠标输入。"
        }

        $foregroundWindow = [NativeMouseTrajectory]::GetForegroundWindow()
        $foregroundProcessId = [uint32]0
        $targetProcessId = [uint32]0
        $foregroundThread = [NativeMouseTrajectory]::GetWindowThreadProcessId(
            $foregroundWindow,
            [ref]$foregroundProcessId
        )
        $targetThread = [NativeMouseTrajectory]::GetWindowThreadProcessId(
            $WindowHandle,
            [ref]$targetProcessId
        )
        $attached = $false
        if ($foregroundThread -ne 0 -and
            $targetThread -ne 0 -and
            $foregroundThread -ne $targetThread) {
            $attached = [NativeMouseTrajectory]::AttachThreadInput(
                $foregroundThread,
                $targetThread,
                $true
            )
        }

        try {
            [void][NativeMouseTrajectory]::BringWindowToTop($WindowHandle)
            [void][NativeMouseTrajectory]::SetForegroundWindow($WindowHandle)
            [void][NativeMouseTrajectory]::SetFocus($WindowHandle)
        }
        finally {
            if ($attached) {
                [void][NativeMouseTrajectory]::AttachThreadInput(
                    $foregroundThread,
                    $targetThread,
                    $false
                )
            }
        }
        [System.Threading.Thread]::Sleep(250)
    }

    if ([NativeMouseTrajectory]::GetForegroundWindow() -ne $WindowHandle) {
        throw "无法将目标窗口切换到前台，未发送任何鼠标输入。"
    }
}

if ($Seed -eq 0) {
    $Seed = [Environment]::TickCount -bxor [DateTime]::UtcNow.Millisecond
}
$random = [System.Random]::new($Seed)

function Next-Double([double]$minimum, [double]$maximum) {
    return $minimum + ($random.NextDouble() * ($maximum - $minimum))
}

$contentBoundsValid = $false
$contentLeft = 0
$contentTop = 0
$contentRight = 0
$contentBottom = 0
if ($ContentBounds) {
    $boundsParts = $ContentBounds -split "\s*,\s*"
    if ($boundsParts.Count -ne 4) {
        throw "ContentBounds 格式必须为 left,top,right,bottom。"
    }
    $contentLeft = [int]$boundsParts[0]
    $contentTop = [int]$boundsParts[1]
    $contentRight = [int]$boundsParts[2]
    $contentBottom = [int]$boundsParts[3]
    if ($contentRight -le $contentLeft -or $contentBottom -le $contentTop) {
        throw "ContentBounds 必须描述一个有效矩形。"
    }
    $contentBoundsValid = $true
}

if (($MaxIdleClicks -gt 0 -or $MaxIdleHovers -gt 0) -and -not $contentBoundsValid) {
    throw "启用空闲悬停或安全区点击时必须提供 ContentBounds。"
}

function Test-PointInContentBounds([int]$candidateX, [int]$candidateY) {
    if (-not $contentBoundsValid) {
        return $true
    }
    return $candidateX -ge $contentLeft -and
        $candidateX -le $contentRight -and
        $candidateY -ge $contentTop -and
        $candidateY -le $contentBottom
}

function Test-ZoneInContentBounds($zone) {
    if (-not $contentBoundsValid) {
        return $true
    }
    return $zone.x -ge $contentLeft -and
        $zone.y -ge $contentTop -and
        ($zone.x + $zone.width - 1) -le $contentRight -and
        ($zone.y + $zone.height - 1) -le $contentBottom
}

if (-not (Test-PointInContentBounds $X $Y)) {
    throw "目标坐标不在 ContentBounds 范围内，未发送任何鼠标输入。"
}

$safeZones = New-Object System.Collections.Generic.List[object]
$safeZonesRejected = 0
if ($SafeZonesPath) {
    $safeConfig = Get-Content -Raw -LiteralPath $SafeZonesPath | ConvertFrom-Json
    foreach ($zone in @($safeConfig.safeZones)) {
        if ($null -eq $zone) {
            continue
        }
        $zoneX = [int]$zone.x
        $zoneY = [int]$zone.y
        $zoneWidth = [int]$zone.width
        $zoneHeight = [int]$zone.height
        if ($zoneWidth -gt 0 -and $zoneHeight -gt 0) {
            $safeZone = [pscustomobject]@{
                label = if ($zone.label) { [string]$zone.label } else { "zone-$($safeZones.Count + 1)" }
                x = $zoneX
                y = $zoneY
                width = $zoneWidth
                height = $zoneHeight
            }
            if (Test-ZoneInContentBounds $safeZone) {
                $safeZones.Add($safeZone)
            }
            else {
                $safeZonesRejected += 1
            }
        }
    }
}

function Test-InteractivePoint([int]$candidateX, [int]$candidateY) {
    if (-not $uiaAvailable) {
        return $true
    }

    try {
        $element = [System.Windows.Automation.AutomationElement]::FromPoint(
            [System.Windows.Point]::new($candidateX, $candidateY)
        )
        if ($null -eq $element) {
            return $true
        }

        $controlType = $element.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
        $interactiveControls = @(
            "Button", "Hyperlink", "Edit", "ComboBox", "CheckBox", "RadioButton",
            "ListItem", "MenuItem", "TabItem", "Slider", "Spinner", "TreeItem",
            "DataItem", "HeaderItem"
        )
        if ($interactiveControls -contains $controlType) {
            return $true
        }

        $patterns = @(
            [System.Windows.Automation.InvokePattern]::Pattern,
            [System.Windows.Automation.SelectionItemPattern]::Pattern,
            [System.Windows.Automation.ValuePattern]::Pattern,
            [System.Windows.Automation.TogglePattern]::Pattern,
            [System.Windows.Automation.ExpandCollapsePattern]::Pattern,
            [System.Windows.Automation.RangeValuePattern]::Pattern
        )
        foreach ($pattern in $patterns) {
            $patternObject = $null
            if ($element.TryGetCurrentPattern($pattern, [ref]$patternObject)) {
                return $true
            }
        }
    }
    catch {
        return $true
    }

    return $false
}

function Find-ForbiddenTarget {
    if (-not $uiaAvailable -or $WindowHandle -eq [IntPtr]::Zero) {
        return $null
    }

    try {
        $point = [System.Windows.Point]::new($X, $Y)
        $element = [System.Windows.Automation.AutomationElement]::FromPoint($point)
        for ($depth = 0; $depth -lt 10 -and $null -ne $element; $depth++) {
            $name = $element.Current.Name
            $className = $element.Current.ClassName
            if ($ForbiddenNames -contains $name -or $ForbiddenClassNames -contains $className) {
                return [pscustomobject]@{
                    name = $name
                    className = $className
                    controlType = $element.Current.ControlType.ProgrammaticName
                    source = "hit-test"
                }
            }
            $element = [System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($element)
        }
    }
    catch {
        return $null
    }

    try {
        $root = [System.Windows.Automation.AutomationElement]::FromHandle($WindowHandle)
        foreach ($forbiddenName in @($ForbiddenNames)) {
            if ([string]::IsNullOrWhiteSpace($forbiddenName)) {
                continue
            }
            $condition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty,
                $forbiddenName
            )
            $matches = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
            for ($index = 0; $index -lt $matches.Count; $index++) {
                $candidate = $matches.Item($index)
                $rect = $candidate.Current.BoundingRectangle
                if (-not $candidate.Current.IsOffscreen -and
                    $X -ge $rect.Left -and $X -le $rect.Right -and
                    $Y -ge $rect.Top -and $Y -le $rect.Bottom) {
                    return [pscustomobject]@{
                        name = $candidate.Current.Name
                        className = $candidate.Current.ClassName
                        controlType = $candidate.Current.ControlType.ProgrammaticName
                        source = "name-scan"
                    }
                }
            }
        }

        foreach ($forbiddenClass in @($ForbiddenClassNames)) {
            if ([string]::IsNullOrWhiteSpace($forbiddenClass)) {
                continue
            }
            $condition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ClassNameProperty,
                $forbiddenClass
            )
            $matches = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
            for ($index = 0; $index -lt $matches.Count; $index++) {
                $candidate = $matches.Item($index)
                $rect = $candidate.Current.BoundingRectangle
                if (-not $candidate.Current.IsOffscreen -and
                    $X -ge $rect.Left -and $X -le $rect.Right -and
                    $Y -ge $rect.Top -and $Y -le $rect.Bottom) {
                    return [pscustomobject]@{
                        name = $candidate.Current.Name
                        className = $candidate.Current.ClassName
                        controlType = $candidate.Current.ControlType.ProgrammaticName
                        source = "class-scan"
                    }
                }
            }
        }
    }
    catch {
        return $null
    }

    return $null
}

$forbiddenTarget = Find-ForbiddenTarget
if (-not $DryRun -and $null -ne $forbiddenTarget) {
    $label = if ($forbiddenTarget.name) { $forbiddenTarget.name } else { $forbiddenTarget.className }
    throw ("目标坐标命中禁止控件“" + $label + "”，未发送鼠标输入。")
}

function Get-RandomSafePoint() {
    if ($safeZones.Count -eq 0) {
        return $null
    }

    for ($attempt = 0; $attempt -lt 8; $attempt++) {
        $zone = $safeZones[$random.Next(0, $safeZones.Count)]
        $paddingX = $zone.width * 0.28
        $paddingY = $zone.height * 0.28
        $candidateX = [int][Math]::Round(
            $zone.x + $paddingX + ($random.NextDouble() * ($zone.width - (2.0 * $paddingX)))
        )
        $candidateY = [int][Math]::Round(
            $zone.y + $paddingY + ($random.NextDouble() * ($zone.height - (2.0 * $paddingY)))
        )
        if (-not (Test-InteractivePoint $candidateX $candidateY)) {
            return [pscustomobject]@{
                x = $candidateX
                y = $candidateY
                label = $zone.label
            }
        }
    }

    return $null
}

$dx = $X - $startX
$dy = $Y - $startY
$directDistance = [Math]::Sqrt(($dx * $dx) + ($dy * $dy))
if ($directDistance -lt 1.0) {
    $directDistance = 1.0
}

$virtualX = [NativeMouseTrajectory]::GetSystemMetrics(76)
$virtualY = [NativeMouseTrajectory]::GetSystemMetrics(77)
$virtualWidth = [NativeMouseTrajectory]::GetSystemMetrics(78)
$virtualHeight = [NativeMouseTrajectory]::GetSystemMetrics(79)
if ($virtualWidth -le 0 -or $virtualHeight -le 0) {
    $virtualX = 0
    $virtualY = 0
    $virtualWidth = 1920
    $virtualHeight = 1080
}

$waypoints = New-Object System.Collections.Generic.List[object]
$idleActions = New-Object System.Collections.Generic.List[object]

for ($index = 0; $index -lt $MaxIdleHovers; $index++) {
    if ($random.NextDouble() -ge $IdleHoverChance) {
        continue
    }
    $safePoint = Get-RandomSafePoint
    if ($null -ne $safePoint) {
        $waypoints.Add([pscustomobject]@{
            x = $safePoint.x
            y = $safePoint.y
            kind = "safeHover"
            label = $safePoint.label
        })
    }
}

for ($index = 0; $index -lt $MaxIdleClicks; $index++) {
    if ($random.NextDouble() -ge $IdleClickChance) {
        continue
    }
    $safePoint = Get-RandomSafePoint
    if ($null -ne $safePoint) {
        $waypoints.Add([pscustomobject]@{
            x = $safePoint.x
            y = $safePoint.y
            kind = "safeClick"
            label = $safePoint.label
        })
    }
}

if ($WanderCount -gt 0 -and $directDistance -gt 80.0) {
    for ($index = 0; $index -lt $WanderCount; $index++) {
        $progress = Next-Double 0.10 0.82
        $baseX = $startX + ($dx * $progress)
        $baseY = $startY + ($dy * $progress)
        $radius = $WanderRadius * (Next-Double 0.35 1.0)
        $angle = Next-Double 0.0 ([Math]::PI * 2.0)
        $wanderX = [int][Math]::Round($baseX + ([Math]::Cos($angle) * $radius))
        $wanderY = [int][Math]::Round($baseY + ([Math]::Sin($angle) * $radius))
        $wanderX = [Math]::Max($virtualX + 2, [Math]::Min($virtualX + $virtualWidth - 3, $wanderX))
        $wanderY = [Math]::Max($virtualY + 2, [Math]::Min($virtualY + $virtualHeight - 3, $wanderY))
        $waypoints.Add([pscustomobject]@{
            x = $wanderX
            y = $wanderY
            kind = "wander"
            label = $null
        })
    }
}

if ($random.NextDouble() -lt $FalseStartChance -and $directDistance -gt 160.0) {
    $angle = Next-Double 0.0 ([Math]::PI * 2.0)
    $radius = Next-Double 35.0 95.0
    $falseStartX = [int][Math]::Round($X + ([Math]::Cos($angle) * $radius))
    $falseStartY = [int][Math]::Round($Y + ([Math]::Sin($angle) * $radius))
    $falseStartX = [Math]::Max($virtualX + 2, [Math]::Min($virtualX + $virtualWidth - 3, $falseStartX))
    $falseStartY = [Math]::Max($virtualY + 2, [Math]::Min($virtualY + $virtualHeight - 3, $falseStartY))
    $waypoints.Add([pscustomobject]@{
        x = $falseStartX
        y = $falseStartY
        kind = "falseStart"
        label = $null
    })
}

$waypoints.Add([pscustomobject]@{
    x = $X
    y = $Y
    kind = "target"
    label = $null
})

$points = New-Object System.Collections.Generic.List[object]
$segments = New-Object System.Collections.Generic.List[object]
$actionPoints = New-Object System.Collections.Generic.List[object]
$previousX = $startX
$previousY = $startY
$totalSegmentDistance = 0.0

foreach ($waypoint in $waypoints) {
    $segmentDx = $waypoint.x - $previousX
    $segmentDy = $waypoint.y - $previousY
    $segmentDistance = [Math]::Sqrt(($segmentDx * $segmentDx) + ($segmentDy * $segmentDy))
    $segmentDistance = [Math]::Max(1.0, $segmentDistance)
    $segments.Add([pscustomobject]@{
        startX = $previousX
        startY = $previousY
        endX = $waypoint.x
        endY = $waypoint.y
        distance = $segmentDistance
        kind = $waypoint.kind
        label = $waypoint.label
    })
    $totalSegmentDistance += $segmentDistance
    $previousX = $waypoint.x
    $previousY = $waypoint.y
}

$pointBudget = [Math]::Max(52, [Math]::Min(220, [int]($DurationMs / 7)))
foreach ($segment in $segments) {
    $segmentDx = $segment.endX - $segment.startX
    $segmentDy = $segment.endY - $segment.startY
    $unitX = $segmentDx / $segment.distance
    $unitY = $segmentDy / $segment.distance
    $normalX = -$unitY
    $normalY = $unitX
    $curveAmount = [Math]::Max(6.0, [Math]::Min(130.0, $segment.distance * (Next-Double 0.05 0.16)))
    if ($random.Next(0, 2) -eq 0) {
        $curveAmount *= -1.0
    }

    $control1X = $segment.startX + ($segmentDx * (Next-Double 0.18 0.42)) + ($normalX * $curveAmount)
    $control1Y = $segment.startY + ($segmentDy * (Next-Double 0.18 0.42)) + ($normalY * $curveAmount)
    $control2X = $segment.startX + ($segmentDx * (Next-Double 0.58 0.84)) + ($normalX * $curveAmount * (Next-Double 0.25 0.9))
    $control2Y = $segment.startY + ($segmentDy * (Next-Double 0.58 0.84)) + ($normalY * $curveAmount * (Next-Double 0.25 0.9))

    $segmentPointCount = [Math]::Max(10, [int][Math]::Round($pointBudget * ($segment.distance / $totalSegmentDistance)))
    for ($index = 0; $index -le $segmentPointCount; $index++) {
        if ($points.Count -gt 0 -and $index -eq 0) {
            continue
        }

        $linearT = $index / $segmentPointCount
        $t = $linearT * $linearT * (3.0 - (2.0 * $linearT))
        $u = 1.0 - $t
        $bezierX = ($u * $u * $u * $segment.startX) +
            (3.0 * $u * $u * $t * $control1X) +
            (3.0 * $u * $t * $t * $control2X) +
            ($t * $t * $t * $segment.endX)
        $bezierY = ($u * $u * $u * $segment.startY) +
            (3.0 * $u * $u * $t * $control1Y) +
            (3.0 * $u * $t * $t * $control2Y) +
            ($t * $t * $t * $segment.endY)

        $envelope = [Math]::Sin([Math]::PI * $linearT)
        $noise = Next-Double (-$Jitter) $Jitter
        $points.Add([pscustomobject]@{
            x = [int][Math]::Round($bezierX + ($normalX * $noise * $envelope) + (Next-Double -0.4 0.4))
            y = [int][Math]::Round($bezierY + ($normalY * $noise * $envelope) + (Next-Double -0.4 0.4))
        })
    }

    if ($segment.kind -ne "target") {
        $actionPoints.Add([pscustomobject]@{
            index = $points.Count - 1
            kind = $segment.kind
            x = $segment.endX
            y = $segment.endY
            label = $segment.label
        })
    }
}

$finalSegment = $segments[$segments.Count - 1]
$finalDx = $X - $finalSegment.startX
$finalDy = $Y - $finalSegment.startY
$finalDistance = [Math]::Max(1.0, [Math]::Sqrt(($finalDx * $finalDx) + ($finalDy * $finalDy)))
$finalUnitX = $finalDx / $finalDistance
$finalUnitY = $finalDy / $finalDistance

if ($OvershootPx -gt 0 -and $finalDistance -gt 120.0) {
    $overshootDistance = Next-Double ($OvershootPx * 0.45) $OvershootPx
    $overshootX = [int][Math]::Round($X + ($finalUnitX * $overshootDistance) + (Next-Double -1.5 1.5))
    $overshootY = [int][Math]::Round($Y + ($finalUnitY * $overshootDistance) + (Next-Double -1.5 1.5))
    $points.Add([pscustomobject]@{ x = $overshootX; y = $overshootY })

    $correctionCount = 7
    for ($index = 1; $index -le $correctionCount; $index++) {
        $t = $index / $correctionCount
        $points.Add([pscustomobject]@{
            x = [int][Math]::Round(($overshootX * (1.0 - $t)) + ($X * $t) + (Next-Double -0.8 0.8))
            y = [int][Math]::Round(($overshootY * (1.0 - $t)) + ($Y * $t) + (Next-Double -0.8 0.8))
        })
    }
}

$points.Add([pscustomobject]@{ x = $X; y = $Y })

$result = [ordered]@{
    start = [ordered]@{ x = $startX; y = $startY }
    target = [ordered]@{ x = $X; y = $Y }
    windowHandle = $WindowHandle.ToInt64()
    contentBounds = if ($contentBoundsValid) {
        [ordered]@{
            left = $contentLeft
            top = $contentTop
            right = $contentRight
            bottom = $contentBottom
        }
    } else {
        $null
    }
    directDistancePx = [Math]::Round($directDistance, 1)
    plannedDistancePx = [Math]::Round($totalSegmentDistance, 1)
    durationMs = $DurationMs
    jitterPx = $Jitter
    overshootPx = $OvershootPx
    wanderCount = $WanderCount
    wanderRadiusPx = $WanderRadius
    burstChance = $BurstChance
    pauseChance = $PauseChance
    maxPauseMs = $MaxPauseMs
    safeZonesLoaded = $safeZones.Count
    safeZonesRejected = $safeZonesRejected
    maxIdleClicks = $MaxIdleClicks
    idleClickChance = $IdleClickChance
    maxIdleHovers = $MaxIdleHovers
    idleHoverChance = $IdleHoverChance
    falseStartChance = $FalseStartChance
    falseStartAdded = @($waypoints | Where-Object { $_.kind -eq "falseStart" }).Count -gt 0
    plannedActionCount = $actionPoints.Count
    pointCount = $points.Count
    seed = $Seed
    forbiddenTarget = $forbiddenTarget
    forbiddenControlBlocked = ($null -ne $forbiddenTarget)
    clicked = (-not $NoClick) -and (-not $DryRun)
    dryRun = [bool]$DryRun
    clickStartedAt = $null
    clickEndedAt = $null
    postClickMove = $null
}

if ($IncludePath -or $DryRun) {
    $result.trajectory = $points
}

$executedIdleActions = New-Object System.Collections.Generic.List[object]

function Invoke-RealClick() {
    if ($GuardTarget) {
        $guard = & (Join-Path $PSScriptRoot "guarded-uia-action.ps1") -Target $GuardTarget -Deadline $GuardDeadline -Action Probe | ConvertFrom-Json
        if ($X -lt $guard.bounds.x -or $X -ge ($guard.bounds.x+$guard.bounds.width) -or $Y -lt $guard.bounds.y -or $Y -ge ($guard.bounds.y+$guard.bounds.height)) { throw "mouse_target_bounds_mismatch" }
    }
    if ([NativeMouseTrajectory]::GetForegroundWindow() -ne $WindowHandle) {
        throw "点击前目标窗口已失去焦点，未点击。"
    }
    $cursorAtClick = New-Object NativeMouseTrajectory+POINT
    if (-not [NativeMouseTrajectory]::GetCursorPos([ref]$cursorAtClick) -or -not (Test-PointInContentBounds $cursorAtClick.X $cursorAtClick.Y)) {
        throw "点击前鼠标已离开内容区域，未点击。"
    }
    $downFlag = if ($Button -eq "Right") { 0x0008 } else { 0x0002 }
    $upFlag = if ($Button -eq "Right") { 0x0010 } else { 0x0004 }
    [NativeMouseTrajectory]::mouse_event($downFlag, 0, 0, 0, [UIntPtr]::Zero)
    [System.Threading.Thread]::Sleep($random.Next(35, 86))
    [NativeMouseTrajectory]::mouse_event($upFlag, 0, 0, 0, [UIntPtr]::Zero)
}

function Invoke-PostClickMove([int]$durationMs) {
    $margin = 10
    $minX = $contentLeft + $margin
    $maxX = $contentRight - $margin
    $minY = $contentTop + $margin
    $maxY = $contentBottom - $margin
    if ($maxX -le $minX -or $maxY -le $minY) {
        throw "内容边界过小，无法执行点击后随机移动。"
    }

    $available = [Math]::Min($maxX - $minX, $maxY - $minY)
    $minimumDistance = [Math]::Min(70.0, [Math]::Max(24.0, $available / 3.0))
    $targetX = $X
    $targetY = $Y
    $bestDistance = -1.0
    for ($attempt = 0; $attempt -lt 24; $attempt++) {
        $angle = Next-Double 0.0 ([Math]::PI * 2.0)
        $distance = Next-Double $minimumDistance $PostClickMoveRadiusPx
        $candidateX = [int][Math]::Round($X + ([Math]::Cos($angle) * $distance))
        $candidateY = [int][Math]::Round($Y + ([Math]::Sin($angle) * $distance))
        $candidateX = [Math]::Max($minX, [Math]::Min($maxX, $candidateX))
        $candidateY = [Math]::Max($minY, [Math]::Min($maxY, $candidateY))
        $distance = [Math]::Sqrt(
            [Math]::Pow($candidateX - $X, 2) + [Math]::Pow($candidateY - $Y, 2)
        )
        if ($distance -gt $bestDistance) {
            $bestDistance = $distance
            $targetX = $candidateX
            $targetY = $candidateY
        }
    }
    if ($bestDistance -lt 24.0) {
        throw "未找到足够的点击后移动距离。"
    }

    $pointCount = [Math]::Max(18, [Math]::Min(40, [int]($durationMs / 40)))
    $delay = [Math]::Max(1, [int][Math]::Floor($durationMs / $pointCount))
    for ($index = 1; $index -le $pointCount; $index++) {
        if ([NativeMouseTrajectory]::GetForegroundWindow() -ne $WindowHandle) {
            throw "点击后移动期间目标窗口失去焦点，已停止。"
        }
        $linear = $index / [double]$pointCount
        $progress = $linear * $linear * (3.0 - (2.0 * $linear))
        $curve = [Math]::Sin([Math]::PI * $linear) * [Math]::Min(42.0, $PostClickMoveRadiusPx * 0.28)
        $normalX = -($targetY - $Y)
        $normalY = $targetX - $X
        $normalLength = [Math]::Max(1.0, [Math]::Sqrt(($normalX * $normalX) + ($normalY * $normalY)))
        $wobble = Next-Double -1.0 1.0
        $moveX = [int][Math]::Round(
            $X + (($targetX - $X) * $progress) +
            (($normalX / $normalLength) * $curve * $wobble)
        )
        $moveY = [int][Math]::Round(
            $Y + (($targetY - $Y) * $progress) +
            (($normalY / $normalLength) * $curve * $wobble)
        )
        $moveX = [Math]::Max($minX, [Math]::Min($maxX, $moveX))
        $moveY = [Math]::Max($minY, [Math]::Min($maxY, $moveY))
        if (-not [NativeMouseTrajectory]::SetCursorPos($moveX, $moveY)) {
            throw "点击后随机移动失败。"
        }
        [System.Threading.Thread]::Sleep($delay)
    }

    if (-not [NativeMouseTrajectory]::SetCursorPos($targetX, $targetY)) {
        throw "点击后随机移动落点设置失败。"
    }
    return [ordered]@{
        durationMs = $durationMs
        start = [ordered]@{ x = $X; y = $Y }
        end = [ordered]@{ x = $targetX; y = $targetY }
        distancePx = [Math]::Round($bestDistance, 1)
    }
}

if (-not $DryRun) {
    $baseDelay = [Math]::Max(2, [int][Math]::Round($DurationMs / [Math]::Max(1, $points.Count)))
    $burstRemaining = 0
    $pointIndex = 0
    $actionByIndex = @{}
    foreach ($action in $actionPoints) {
        $actionByIndex[[int]$action.index] = $action
    }

    foreach ($pathPoint in $points) {
        if ([NativeMouseTrajectory]::GetForegroundWindow() -ne $WindowHandle) {
            throw "移动期间目标窗口失去焦点，已停止。"
        }
        if (-not [NativeMouseTrajectory]::SetCursorPos($pathPoint.x, $pathPoint.y)) {
            throw "SetCursorPos 移动到 $($pathPoint.x),$($pathPoint.y) 失败。"
        }

        if ($burstRemaining -gt 0) {
            $delay = [Math]::Max(1, [int]($baseDelay * (Next-Double 0.12 0.32)))
            $burstRemaining -= 1
        }
        elseif ($random.NextDouble() -lt $BurstChance) {
            $burstRemaining = $random.Next(2, 8)
            $delay = [Math]::Max(1, [int]($baseDelay * (Next-Double 0.15 0.38)))
        }
        elseif ($random.NextDouble() -lt $PauseChance) {
            $delay = $random.Next(18, [Math]::Max(19, $MaxPauseMs + 1))
        }
        else {
            $delay = [Math]::Max(2, [int]($baseDelay * (Next-Double 0.55 1.65)))
        }

        [System.Threading.Thread]::Sleep($delay)

        if ($actionByIndex.ContainsKey($pointIndex)) {
            $action = $actionByIndex[$pointIndex]
            switch ($action.kind) {
                "safeHover" {
                    [System.Threading.Thread]::Sleep($random.Next(180, 481))
                    $executedIdleActions.Add([pscustomobject]@{
                        kind = "hover"
                        x = $action.x
                        y = $action.y
                        label = $action.label
                        clicked = $false
                    })
                }
                "safeClick" {
                    [System.Threading.Thread]::Sleep($random.Next(110, 361))
                    $idleClicked = $false
                    if (-not $NoClick) {
                        Invoke-RealClick
                        $idleClicked = $true
                    }
                    [System.Threading.Thread]::Sleep($random.Next(180, 651))
                    $executedIdleActions.Add([pscustomobject]@{
                        kind = "click"
                        x = $action.x
                        y = $action.y
                        label = $action.label
                        clicked = $idleClicked
                    })
                }
                "falseStart" {
                    [System.Threading.Thread]::Sleep($random.Next(90, 261))
                }
                "wander" {
                    if ($random.NextDouble() -lt 0.3) {
                        [System.Threading.Thread]::Sleep($random.Next(35, 141))
                    }
                }
            }
        }

        $pointIndex += 1
    }

    if ([NativeMouseTrajectory]::GetForegroundWindow() -ne $WindowHandle) {
        throw "最终移动前目标窗口失去焦点，已停止。"
    }
    if (-not [NativeMouseTrajectory]::SetCursorPos($X, $Y)) {
        throw "最终定位失败，未点击。"
    }
    [System.Threading.Thread]::Sleep($random.Next(90, 181))

    if (-not $NoClick) {
        $finalBeforeClick = New-Object NativeMouseTrajectory+POINT
        if (-not [NativeMouseTrajectory]::GetCursorPos([ref]$finalBeforeClick) -or $finalBeforeClick.X -ne $X -or $finalBeforeClick.Y -ne $Y) {
            throw "最终点击坐标发生变化，未点击。"
        }
        $result.clickStartedAt = [DateTimeOffset]::Now.ToString("o")
        Invoke-RealClick
        $result.clickEndedAt = [DateTimeOffset]::Now.ToString("o")
    }

    if (-not $NoClick -and $PostClickMoveMs -gt 0) {
        $result.postClickMove = Invoke-PostClickMove $PostClickMoveMs
    }

    $finalPoint = New-Object NativeMouseTrajectory+POINT
    [void][NativeMouseTrajectory]::GetCursorPos([ref]$finalPoint)
    $result.finalCursor = [ordered]@{ x = $finalPoint.X; y = $finalPoint.Y }
}

$result.idleActions = $executedIdleActions
$result | ConvertTo-Json -Depth 6
