param(
    [Parameter(Mandatory = $true)][long]$WindowHandle,
    [string]$DocumentName = "BOSS直聘",
    [string]$DocumentUrlLike = "",
    [ValidateSet("Any", "Button", "Hyperlink", "Text", "Document", "ListItem", "Group", "Edit", "ComboBox", "Image", "Pane", "Custom")]
    [string]$ControlType = "Any",
    [string]$Name = "",
    [string]$NameLike = "",
    [string]$ClassName = "",
    [int]$Limit = 100,
    [switch]$VisibleOnly,
    [switch]$Compact,
    [ValidateRange(16, 512)][int]$NameChars = 96
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Name) -and
    [string]::IsNullOrWhiteSpace($NameLike) -and
    [string]::IsNullOrWhiteSpace($ClassName) -and
    $ControlType -eq "Any") {
    throw "至少提供 -Name、-NameLike、-ClassName 或 -ControlType 之一，避免全树扫描。"
}

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$WindowHandle)
if ($null -eq $root) {
    throw "无法取得窗口 UI Automation 根节点。"
}

$scope = $root
$scopeValue = ""
if (-not [string]::IsNullOrWhiteSpace($DocumentUrlLike)) {
    $documentTypeCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Document
    )
    $documents = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $documentTypeCondition
    )
    $urlMatches = New-Object System.Collections.Generic.List[object]
    foreach ($candidateDocument in $documents) {
        try {
            if (-not [string]::IsNullOrWhiteSpace($DocumentName) -and $candidateDocument.Current.Name -ne $DocumentName) {
                continue
            }
            $candidateValue = ""
            $candidateValuePattern = $null
            if ($candidateDocument.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$candidateValuePattern)) {
                $candidateValue = $candidateValuePattern.Current.Value
            }
            if ($candidateValue -like $DocumentUrlLike) {
                $urlMatches.Add([pscustomobject]@{ Element = $candidateDocument; Value = $candidateValue })
            }
        }
        catch {
            continue
        }
    }
    if ($urlMatches.Count -ne 1) {
        throw "Expected one document matching URL pattern '$DocumentUrlLike'; found $($urlMatches.Count)."
    }
    $scope = $urlMatches[0].Element
    $scopeValue = $urlMatches[0].Value
} elseif (-not [string]::IsNullOrWhiteSpace($DocumentName)) {
    $documentNameCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        $DocumentName
    )
    $documentTypeCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Document
    )
    $scope = $root.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        (New-Object System.Windows.Automation.AndCondition($documentNameCondition, $documentTypeCondition))
    )
    if ($null -eq $scope) {
        throw "未找到页面文档：$DocumentName"
    }
    $scopeValuePattern = $null
    if ($scope.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$scopeValuePattern)) {
        $scopeValue = $scopeValuePattern.Current.Value
    }
}

$conditions = New-Object System.Collections.Generic.List[object]
if ($ControlType -ne "Any") {
    $controlTypeValue = switch ($ControlType) {
        "Button" { [System.Windows.Automation.ControlType]::Button }
        "Hyperlink" { [System.Windows.Automation.ControlType]::Hyperlink }
        "Text" { [System.Windows.Automation.ControlType]::Text }
        "Document" { [System.Windows.Automation.ControlType]::Document }
        "ListItem" { [System.Windows.Automation.ControlType]::ListItem }
        "Group" { [System.Windows.Automation.ControlType]::Group }
        "Edit" { [System.Windows.Automation.ControlType]::Edit }
        "ComboBox" { [System.Windows.Automation.ControlType]::ComboBox }
        "Image" { [System.Windows.Automation.ControlType]::Image }
        "Pane" { [System.Windows.Automation.ControlType]::Pane }
        "Custom" { [System.Windows.Automation.ControlType]::Custom }
    }
    $conditions.Add((New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        $controlTypeValue
    )))
}
if (-not [string]::IsNullOrWhiteSpace($Name)) {
    $conditions.Add((New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        $Name
    )))
}
if (-not [string]::IsNullOrWhiteSpace($ClassName)) {
    $conditions.Add((New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ClassNameProperty,
        $ClassName
    )))
}

$condition = if ($conditions.Count -eq 1) {
    $conditions[0]
} else {
    New-Object System.Windows.Automation.AndCondition($conditions.ToArray())
}

$matches = $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
$items = New-Object System.Collections.Generic.List[object]

for ($index = 0; $index -lt $matches.Count -and $items.Count -lt $Limit; $index++) {
    $element = $matches.Item($index)
    try {
        if (-not [string]::IsNullOrWhiteSpace($NameLike) -and $element.Current.Name -notlike $NameLike) {
            continue
        }
        if ($VisibleOnly -and $element.Current.IsOffscreen) {
            continue
        }

        $rect = $element.Current.BoundingRectangle
        $name = $element.Current.Name
        if ($Compact) {
            $items.Add([pscustomobject]@{
                index = $index
                name = if ($name.Length -gt $NameChars) { $name.Substring(0, $NameChars) } else { $name }
                nameTruncated = $name.Length -gt $NameChars
                controlType = $element.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
                left = [math]::Round($rect.Left)
                top = [math]::Round($rect.Top)
                width = [math]::Round($rect.Width)
                height = [math]::Round($rect.Height)
                isOffscreen = $element.Current.IsOffscreen
                isEnabled = $element.Current.IsEnabled
            })
        } else {
            $value = ""
            $valuePattern = $null
            if ($element.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$valuePattern)) {
                $value = $valuePattern.Current.Value
            }
            $items.Add([pscustomobject]@{
                index = $index
                name = $name
                controlType = $element.Current.ControlType.ProgrammaticName.Replace("ControlType.", "")
                className = $element.Current.ClassName
                automationId = $element.Current.AutomationId
                value = $value
                left = [math]::Round($rect.Left)
                top = [math]::Round($rect.Top)
                width = [math]::Round($rect.Width)
                height = [math]::Round($rect.Height)
                isOffscreen = $element.Current.IsOffscreen
                isEnabled = $element.Current.IsEnabled
            })
        }
    }
    catch {
        continue
    }
}

[pscustomobject]@{
    state = "ok"
    windowHandle = $WindowHandle
    document = $DocumentName
    documentUrl = $scopeValue
    count = $items.Count
    items = $items
} | ConvertTo-Json -Depth 5
