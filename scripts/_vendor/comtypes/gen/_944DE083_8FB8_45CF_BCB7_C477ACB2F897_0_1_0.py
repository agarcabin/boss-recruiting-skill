# -*- coding: mbcs -*-

from ctypes import *
import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0
from comtypes import (
    _check_version, BSTR, CoClass, COMMETHOD, dispid, GUID, IUnknown
)
from ctypes import HRESULT
from comtypes.automation import _midlSAFEARRAY, IDispatch, VARIANT
from ctypes.wintypes import tagPOINT, tagRECT
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from comtypes import hints


_lcid = 0  # change this if required
typelib_path = 'C:\\Windows\\System32\\UIAutomationCore.dll'
WSTRING = c_wchar_p

# values for enumeration 'ZoomUnit'
ZoomUnit_NoAmount = 0
ZoomUnit_LargeDecrement = 1
ZoomUnit_SmallDecrement = 2
ZoomUnit_LargeIncrement = 3
ZoomUnit_SmallIncrement = 4
ZoomUnit = c_int  # enum

# values for enumeration 'TreeScope'
TreeScope_None = 0
TreeScope_Element = 1
TreeScope_Children = 2
TreeScope_Descendants = 4
TreeScope_Parent = 8
TreeScope_Ancestors = 16
TreeScope_Subtree = 7
TreeScope = c_int  # enum

# values for enumeration 'OrientationType'
OrientationType_None = 0
OrientationType_Horizontal = 1
OrientationType_Vertical = 2
OrientationType = c_int  # enum

# values for enumeration 'SynchronizedInputType'
SynchronizedInputType_KeyUp = 1
SynchronizedInputType_KeyDown = 2
SynchronizedInputType_LeftMouseUp = 4
SynchronizedInputType_LeftMouseDown = 8
SynchronizedInputType_RightMouseUp = 16
SynchronizedInputType_RightMouseDown = 32
SynchronizedInputType = c_int  # enum

# values for enumeration 'ScrollAmount'
ScrollAmount_LargeDecrement = 0
ScrollAmount_SmallDecrement = 1
ScrollAmount_NoAmount = 2
ScrollAmount_LargeIncrement = 3
ScrollAmount_SmallIncrement = 4
ScrollAmount = c_int  # enum

# values for enumeration 'ConnectionRecoveryBehaviorOptions'
ConnectionRecoveryBehaviorOptions_Disabled = 0
ConnectionRecoveryBehaviorOptions_Enabled = 1
ConnectionRecoveryBehaviorOptions = c_int  # enum

# values for enumeration 'StructureChangeType'
StructureChangeType_ChildAdded = 0
StructureChangeType_ChildRemoved = 1
StructureChangeType_ChildrenInvalidated = 2
StructureChangeType_ChildrenBulkAdded = 3
StructureChangeType_ChildrenBulkRemoved = 4
StructureChangeType_ChildrenReordered = 5
StructureChangeType = c_int  # enum

# values for enumeration 'TextEditChangeType'
TextEditChangeType_None = 0
TextEditChangeType_AutoCorrect = 1
TextEditChangeType_Composition = 2
TextEditChangeType_CompositionFinalized = 3
TextEditChangeType_AutoComplete = 4
TextEditChangeType = c_int  # enum

# values for enumeration 'RowOrColumnMajor'
RowOrColumnMajor_RowMajor = 0
RowOrColumnMajor_ColumnMajor = 1
RowOrColumnMajor_Indeterminate = 2
RowOrColumnMajor = c_int  # enum

# values for enumeration 'LiveSetting'
Off = 0
Polite = 1
Assertive = 2
LiveSetting = c_int  # enum

# values for enumeration 'AutomationElementMode'
AutomationElementMode_None = 0
AutomationElementMode_Full = 1
AutomationElementMode = c_int  # enum

# values for enumeration 'TreeTraversalOptions'
TreeTraversalOptions_Default = 0
TreeTraversalOptions_PostOrder = 1
TreeTraversalOptions_LastToFirstOrder = 2
TreeTraversalOptions = c_int  # enum

# values for enumeration 'PropertyConditionFlags'
PropertyConditionFlags_None = 0
PropertyConditionFlags_IgnoreCase = 1
PropertyConditionFlags_MatchSubstring = 2
PropertyConditionFlags = c_int  # enum

# values for enumeration 'NotificationKind'
NotificationKind_ItemAdded = 0
NotificationKind_ItemRemoved = 1
NotificationKind_ActionCompleted = 2
NotificationKind_ActionAborted = 3
NotificationKind_Other = 4
NotificationKind = c_int  # enum

# values for enumeration 'NotificationProcessing'
NotificationProcessing_ImportantAll = 0
NotificationProcessing_ImportantMostRecent = 1
NotificationProcessing_All = 2
NotificationProcessing_MostRecent = 3
NotificationProcessing_CurrentThenMostRecent = 4
NotificationProcessing_ImportantCurrentThenMostRecent = 5
NotificationProcessing = c_int  # enum

# values for enumeration 'ToggleState'
ToggleState_Off = 0
ToggleState_On = 1
ToggleState_Indeterminate = 2
ToggleState = c_int  # enum

# values for enumeration 'WindowInteractionState'
WindowInteractionState_Running = 0
WindowInteractionState_Closing = 1
WindowInteractionState_ReadyForUserInteraction = 2
WindowInteractionState_BlockedByModalWindow = 3
WindowInteractionState_NotResponding = 4
WindowInteractionState = c_int  # enum

# values for enumeration 'TextPatternRangeEndpoint'
TextPatternRangeEndpoint_Start = 0
TextPatternRangeEndpoint_End = 1
TextPatternRangeEndpoint = c_int  # enum

# values for enumeration 'TextUnit'
TextUnit_Character = 0
TextUnit_Format = 1
TextUnit_Word = 2
TextUnit_Line = 3
TextUnit_Paragraph = 4
TextUnit_Page = 5
TextUnit_Document = 6
TextUnit = c_int  # enum

# values for enumeration 'DockPosition'
DockPosition_Top = 0
DockPosition_Left = 1
DockPosition_Bottom = 2
DockPosition_Right = 3
DockPosition_Fill = 4
DockPosition_None = 5
DockPosition = c_int  # enum

# values for enumeration 'ExpandCollapseState'
ExpandCollapseState_Collapsed = 0
ExpandCollapseState_Expanded = 1
ExpandCollapseState_PartiallyExpanded = 2
ExpandCollapseState_LeafNode = 3
ExpandCollapseState = c_int  # enum

# values for enumeration 'NavigateDirection'
NavigateDirection_Parent = 0
NavigateDirection_NextSibling = 1
NavigateDirection_PreviousSibling = 2
NavigateDirection_FirstChild = 3
NavigateDirection_LastChild = 4
NavigateDirection = c_int  # enum

# values for enumeration 'ProviderOptions'
ProviderOptions_ClientSideProvider = 1
ProviderOptions_ServerSideProvider = 2
ProviderOptions_NonClientAreaProvider = 4
ProviderOptions_OverrideProvider = 8
ProviderOptions_ProviderOwnsSetFocus = 16
ProviderOptions_UseComThreading = 32
ProviderOptions_RefuseNonClientSupport = 64
ProviderOptions_HasNativeIAccessible = 128
ProviderOptions_UseClientCoordinates = 256
ProviderOptions = c_int  # enum

# values for enumeration 'WindowVisualState'
WindowVisualState_Normal = 0
WindowVisualState_Maximized = 1
WindowVisualState_Minimized = 2
WindowVisualState = c_int  # enum

# values for enumeration 'CoalesceEventsOptions'
CoalesceEventsOptions_Disabled = 0
CoalesceEventsOptions_Enabled = 1
CoalesceEventsOptions = c_int  # enum

# values for enumeration 'SupportedTextSelection'
SupportedTextSelection_None = 0
SupportedTextSelection_Single = 1
SupportedTextSelection_Multiple = 2
SupportedTextSelection = c_int  # enum



class IUIAutomationCondition(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{352FFBA8-0973-437C-A61F-F64CAFD81DF9}')
    _idlflags_ = []


class IUIAutomationOrCondition(IUIAutomationCondition):
    _case_insensitive_ = True
    _iid_ = GUID('{8753F032-3DB1-47B5-A1FC-6E34A266C712}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_ChildCount(self) -> hints.Incomplete: ...
        ChildCount = hints.normal_property(_get_ChildCount)
        def GetChildrenAsNativeArray(self) -> tuple['IUIAutomationCondition', hints.Incomplete]: ...
        def GetChildren(self) -> hints.Incomplete: ...


IUIAutomationCondition._methods_ = [
]

IUIAutomationOrCondition._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ChildCount',
        (['out', 'retval'], POINTER(c_int), 'ChildCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetChildrenAsNativeArray',
        (
            ['out'],
            POINTER(POINTER(POINTER(IUIAutomationCondition))),
            'childArray',
        ),
        (['out'], POINTER(c_int), 'childArrayCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetChildren',
        (
            ['out', 'retval'],
            POINTER(_midlSAFEARRAY(POINTER(IUIAutomationCondition))),
            'childArray',
        )
    ),
]


class IUIAutomationElement(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{D22108AA-8AC5-49A5-837B-37BBB3D7591E}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def SetFocus(self) -> hints.Hresult: ...
        def GetRuntimeId(self) -> hints.Incomplete: ...
        def FindFirst(self, scope: hints.Incomplete, condition: hints.Incomplete) -> 'IUIAutomationElement': ...
        def FindAll(self, scope: hints.Incomplete, condition: hints.Incomplete) -> 'IUIAutomationElementArray': ...
        def FindFirstBuildCache(self, scope: hints.Incomplete, condition: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def FindAllBuildCache(self, scope: hints.Incomplete, condition: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElementArray': ...
        def BuildUpdatedCache(self, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetCurrentPropertyValue(self, propertyId: hints.Incomplete) -> hints.Incomplete: ...
        def GetCurrentPropertyValueEx(self, propertyId: hints.Incomplete, ignoreDefaultValue: hints.Incomplete) -> hints.Incomplete: ...
        def GetCachedPropertyValue(self, propertyId: hints.Incomplete) -> hints.Incomplete: ...
        def GetCachedPropertyValueEx(self, propertyId: hints.Incomplete, ignoreDefaultValue: hints.Incomplete) -> hints.Incomplete: ...
        def GetCurrentPatternAs(self, patternId: hints.Incomplete, riid: hints.Incomplete) -> hints.Incomplete: ...
        def GetCachedPatternAs(self, patternId: hints.Incomplete, riid: hints.Incomplete) -> hints.Incomplete: ...
        def GetCurrentPattern(self, patternId: hints.Incomplete) -> 'IUnknown': ...
        def GetCachedPattern(self, patternId: hints.Incomplete) -> 'IUnknown': ...
        def GetCachedParent(self) -> 'IUIAutomationElement': ...
        def GetCachedChildren(self) -> 'IUIAutomationElementArray': ...
        def _get_CurrentProcessId(self) -> hints.Incomplete: ...
        CurrentProcessId = hints.normal_property(_get_CurrentProcessId)
        def _get_CurrentControlType(self) -> hints.Incomplete: ...
        CurrentControlType = hints.normal_property(_get_CurrentControlType)
        def _get_CurrentLocalizedControlType(self) -> hints.Incomplete: ...
        CurrentLocalizedControlType = hints.normal_property(_get_CurrentLocalizedControlType)
        def _get_CurrentName(self) -> hints.Incomplete: ...
        CurrentName = hints.normal_property(_get_CurrentName)
        def _get_CurrentAcceleratorKey(self) -> hints.Incomplete: ...
        CurrentAcceleratorKey = hints.normal_property(_get_CurrentAcceleratorKey)
        def _get_CurrentAccessKey(self) -> hints.Incomplete: ...
        CurrentAccessKey = hints.normal_property(_get_CurrentAccessKey)
        def _get_CurrentHasKeyboardFocus(self) -> hints.Incomplete: ...
        CurrentHasKeyboardFocus = hints.normal_property(_get_CurrentHasKeyboardFocus)
        def _get_CurrentIsKeyboardFocusable(self) -> hints.Incomplete: ...
        CurrentIsKeyboardFocusable = hints.normal_property(_get_CurrentIsKeyboardFocusable)
        def _get_CurrentIsEnabled(self) -> hints.Incomplete: ...
        CurrentIsEnabled = hints.normal_property(_get_CurrentIsEnabled)
        def _get_CurrentAutomationId(self) -> hints.Incomplete: ...
        CurrentAutomationId = hints.normal_property(_get_CurrentAutomationId)
        def _get_CurrentClassName(self) -> hints.Incomplete: ...
        CurrentClassName = hints.normal_property(_get_CurrentClassName)
        def _get_CurrentHelpText(self) -> hints.Incomplete: ...
        CurrentHelpText = hints.normal_property(_get_CurrentHelpText)
        def _get_CurrentCulture(self) -> hints.Incomplete: ...
        CurrentCulture = hints.normal_property(_get_CurrentCulture)
        def _get_CurrentIsControlElement(self) -> hints.Incomplete: ...
        CurrentIsControlElement = hints.normal_property(_get_CurrentIsControlElement)
        def _get_CurrentIsContentElement(self) -> hints.Incomplete: ...
        CurrentIsContentElement = hints.normal_property(_get_CurrentIsContentElement)
        def _get_CurrentIsPassword(self) -> hints.Incomplete: ...
        CurrentIsPassword = hints.normal_property(_get_CurrentIsPassword)
        def _get_CurrentNativeWindowHandle(self) -> hints.Incomplete: ...
        CurrentNativeWindowHandle = hints.normal_property(_get_CurrentNativeWindowHandle)
        def _get_CurrentItemType(self) -> hints.Incomplete: ...
        CurrentItemType = hints.normal_property(_get_CurrentItemType)
        def _get_CurrentIsOffscreen(self) -> hints.Incomplete: ...
        CurrentIsOffscreen = hints.normal_property(_get_CurrentIsOffscreen)
        def _get_CurrentOrientation(self) -> hints.Incomplete: ...
        CurrentOrientation = hints.normal_property(_get_CurrentOrientation)
        def _get_CurrentFrameworkId(self) -> hints.Incomplete: ...
        CurrentFrameworkId = hints.normal_property(_get_CurrentFrameworkId)
        def _get_CurrentIsRequiredForForm(self) -> hints.Incomplete: ...
        CurrentIsRequiredForForm = hints.normal_property(_get_CurrentIsRequiredForForm)
        def _get_CurrentItemStatus(self) -> hints.Incomplete: ...
        CurrentItemStatus = hints.normal_property(_get_CurrentItemStatus)
        def _get_CurrentBoundingRectangle(self) -> hints.Incomplete: ...
        CurrentBoundingRectangle = hints.normal_property(_get_CurrentBoundingRectangle)
        def _get_CurrentLabeledBy(self) -> 'IUIAutomationElement': ...
        CurrentLabeledBy = hints.normal_property(_get_CurrentLabeledBy)
        def _get_CurrentAriaRole(self) -> hints.Incomplete: ...
        CurrentAriaRole = hints.normal_property(_get_CurrentAriaRole)
        def _get_CurrentAriaProperties(self) -> hints.Incomplete: ...
        CurrentAriaProperties = hints.normal_property(_get_CurrentAriaProperties)
        def _get_CurrentIsDataValidForForm(self) -> hints.Incomplete: ...
        CurrentIsDataValidForForm = hints.normal_property(_get_CurrentIsDataValidForForm)
        def _get_CurrentControllerFor(self) -> 'IUIAutomationElementArray': ...
        CurrentControllerFor = hints.normal_property(_get_CurrentControllerFor)
        def _get_CurrentDescribedBy(self) -> 'IUIAutomationElementArray': ...
        CurrentDescribedBy = hints.normal_property(_get_CurrentDescribedBy)
        def _get_CurrentFlowsTo(self) -> 'IUIAutomationElementArray': ...
        CurrentFlowsTo = hints.normal_property(_get_CurrentFlowsTo)
        def _get_CurrentProviderDescription(self) -> hints.Incomplete: ...
        CurrentProviderDescription = hints.normal_property(_get_CurrentProviderDescription)
        def _get_CachedProcessId(self) -> hints.Incomplete: ...
        CachedProcessId = hints.normal_property(_get_CachedProcessId)
        def _get_CachedControlType(self) -> hints.Incomplete: ...
        CachedControlType = hints.normal_property(_get_CachedControlType)
        def _get_CachedLocalizedControlType(self) -> hints.Incomplete: ...
        CachedLocalizedControlType = hints.normal_property(_get_CachedLocalizedControlType)
        def _get_CachedName(self) -> hints.Incomplete: ...
        CachedName = hints.normal_property(_get_CachedName)
        def _get_CachedAcceleratorKey(self) -> hints.Incomplete: ...
        CachedAcceleratorKey = hints.normal_property(_get_CachedAcceleratorKey)
        def _get_CachedAccessKey(self) -> hints.Incomplete: ...
        CachedAccessKey = hints.normal_property(_get_CachedAccessKey)
        def _get_CachedHasKeyboardFocus(self) -> hints.Incomplete: ...
        CachedHasKeyboardFocus = hints.normal_property(_get_CachedHasKeyboardFocus)
        def _get_CachedIsKeyboardFocusable(self) -> hints.Incomplete: ...
        CachedIsKeyboardFocusable = hints.normal_property(_get_CachedIsKeyboardFocusable)
        def _get_CachedIsEnabled(self) -> hints.Incomplete: ...
        CachedIsEnabled = hints.normal_property(_get_CachedIsEnabled)
        def _get_CachedAutomationId(self) -> hints.Incomplete: ...
        CachedAutomationId = hints.normal_property(_get_CachedAutomationId)
        def _get_CachedClassName(self) -> hints.Incomplete: ...
        CachedClassName = hints.normal_property(_get_CachedClassName)
        def _get_CachedHelpText(self) -> hints.Incomplete: ...
        CachedHelpText = hints.normal_property(_get_CachedHelpText)
        def _get_CachedCulture(self) -> hints.Incomplete: ...
        CachedCulture = hints.normal_property(_get_CachedCulture)
        def _get_CachedIsControlElement(self) -> hints.Incomplete: ...
        CachedIsControlElement = hints.normal_property(_get_CachedIsControlElement)
        def _get_CachedIsContentElement(self) -> hints.Incomplete: ...
        CachedIsContentElement = hints.normal_property(_get_CachedIsContentElement)
        def _get_CachedIsPassword(self) -> hints.Incomplete: ...
        CachedIsPassword = hints.normal_property(_get_CachedIsPassword)
        def _get_CachedNativeWindowHandle(self) -> hints.Incomplete: ...
        CachedNativeWindowHandle = hints.normal_property(_get_CachedNativeWindowHandle)
        def _get_CachedItemType(self) -> hints.Incomplete: ...
        CachedItemType = hints.normal_property(_get_CachedItemType)
        def _get_CachedIsOffscreen(self) -> hints.Incomplete: ...
        CachedIsOffscreen = hints.normal_property(_get_CachedIsOffscreen)
        def _get_CachedOrientation(self) -> hints.Incomplete: ...
        CachedOrientation = hints.normal_property(_get_CachedOrientation)
        def _get_CachedFrameworkId(self) -> hints.Incomplete: ...
        CachedFrameworkId = hints.normal_property(_get_CachedFrameworkId)
        def _get_CachedIsRequiredForForm(self) -> hints.Incomplete: ...
        CachedIsRequiredForForm = hints.normal_property(_get_CachedIsRequiredForForm)
        def _get_CachedItemStatus(self) -> hints.Incomplete: ...
        CachedItemStatus = hints.normal_property(_get_CachedItemStatus)
        def _get_CachedBoundingRectangle(self) -> hints.Incomplete: ...
        CachedBoundingRectangle = hints.normal_property(_get_CachedBoundingRectangle)
        def _get_CachedLabeledBy(self) -> 'IUIAutomationElement': ...
        CachedLabeledBy = hints.normal_property(_get_CachedLabeledBy)
        def _get_CachedAriaRole(self) -> hints.Incomplete: ...
        CachedAriaRole = hints.normal_property(_get_CachedAriaRole)
        def _get_CachedAriaProperties(self) -> hints.Incomplete: ...
        CachedAriaProperties = hints.normal_property(_get_CachedAriaProperties)
        def _get_CachedIsDataValidForForm(self) -> hints.Incomplete: ...
        CachedIsDataValidForForm = hints.normal_property(_get_CachedIsDataValidForForm)
        def _get_CachedControllerFor(self) -> 'IUIAutomationElementArray': ...
        CachedControllerFor = hints.normal_property(_get_CachedControllerFor)
        def _get_CachedDescribedBy(self) -> 'IUIAutomationElementArray': ...
        CachedDescribedBy = hints.normal_property(_get_CachedDescribedBy)
        def _get_CachedFlowsTo(self) -> 'IUIAutomationElementArray': ...
        CachedFlowsTo = hints.normal_property(_get_CachedFlowsTo)
        def _get_CachedProviderDescription(self) -> hints.Incomplete: ...
        CachedProviderDescription = hints.normal_property(_get_CachedProviderDescription)
        def GetClickablePoint(self) -> tuple[hints.Incomplete, hints.Incomplete]: ...


class IUIAutomationElementArray(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{14314595-B4BC-4055-95F2-58F2E42C9855}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_Length(self) -> hints.Incomplete: ...
        Length = hints.normal_property(_get_Length)
        def GetElement(self, index: hints.Incomplete) -> 'IUIAutomationElement': ...


class IUIAutomationCacheRequest(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{B32A92B5-BC25-4078-9C08-D7EE95C48E03}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def AddProperty(self, propertyId: hints.Incomplete) -> hints.Hresult: ...
        def AddPattern(self, patternId: hints.Incomplete) -> hints.Hresult: ...
        def Clone(self) -> 'IUIAutomationCacheRequest': ...
        def _get_TreeScope(self) -> hints.Incomplete: ...
        def _set_TreeScope(self, scope: hints.Incomplete) -> hints.Hresult: ...
        TreeScope = hints.normal_property(_get_TreeScope, _set_TreeScope)
        def _get_TreeFilter(self) -> 'IUIAutomationCondition': ...
        def _set_TreeFilter(self, filter: hints.Incomplete) -> hints.Hresult: ...
        TreeFilter = hints.normal_property(_get_TreeFilter, _set_TreeFilter)
        def _get_AutomationElementMode(self) -> hints.Incomplete: ...
        def _set_AutomationElementMode(self, mode: hints.Incomplete) -> hints.Hresult: ...
        AutomationElementMode = hints.normal_property(_get_AutomationElementMode, _set_AutomationElementMode)


IUIAutomationElement._methods_ = [
    COMMETHOD([], HRESULT, 'SetFocus'),
    COMMETHOD(
        [],
        HRESULT,
        'GetRuntimeId',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'runtimeId')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindFirst',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'found')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindAll',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'found',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindFirstBuildCache',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'found')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindAllBuildCache',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'found',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'BuildUpdatedCache',
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElement)),
            'updatedElement',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentPropertyValue',
        (['in'], c_int, 'propertyId'),
        (['out', 'retval'], POINTER(VARIANT), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentPropertyValueEx',
        (['in'], c_int, 'propertyId'),
        (['in'], c_int, 'ignoreDefaultValue'),
        (['out', 'retval'], POINTER(VARIANT), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedPropertyValue',
        (['in'], c_int, 'propertyId'),
        (['out', 'retval'], POINTER(VARIANT), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedPropertyValueEx',
        (['in'], c_int, 'propertyId'),
        (['in'], c_int, 'ignoreDefaultValue'),
        (['out', 'retval'], POINTER(VARIANT), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentPatternAs',
        (['in'], c_int, 'patternId'),
        (
            ['in'],
            POINTER(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.GUID),
            'riid',
        ),
        (['out', 'retval'], POINTER(c_void_p), 'patternObject')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedPatternAs',
        (['in'], c_int, 'patternId'),
        (
            ['in'],
            POINTER(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.GUID),
            'riid',
        ),
        (['out', 'retval'], POINTER(c_void_p), 'patternObject')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentPattern',
        (['in'], c_int, 'patternId'),
        (['out', 'retval'], POINTER(POINTER(IUnknown)), 'patternObject')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedPattern',
        (['in'], c_int, 'patternId'),
        (['out', 'retval'], POINTER(POINTER(IUnknown)), 'patternObject')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedParent',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'parent')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedChildren',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'children',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentProcessId',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentControlType',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLocalizedControlType',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAcceleratorKey',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAccessKey',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHasKeyboardFocus',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsKeyboardFocusable',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsEnabled',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAutomationId',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentClassName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHelpText',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCulture',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsControlElement',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsContentElement',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsPassword',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentNativeWindowHandle',
        (['out', 'retval'], POINTER(c_void_p), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentItemType',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsOffscreen',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentOrientation',
        (['out', 'retval'], POINTER(OrientationType), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFrameworkId',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsRequiredForForm',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentItemStatus',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentBoundingRectangle',
        (['out', 'retval'], POINTER(tagRECT), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLabeledBy',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAriaRole',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAriaProperties',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsDataValidForForm',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentControllerFor',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDescribedBy',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFlowsTo',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentProviderDescription',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedProcessId',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedControlType',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLocalizedControlType',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAcceleratorKey',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAccessKey',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHasKeyboardFocus',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsKeyboardFocusable',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsEnabled',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAutomationId',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedClassName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHelpText',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCulture',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsControlElement',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsContentElement',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsPassword',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedNativeWindowHandle',
        (['out', 'retval'], POINTER(c_void_p), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedItemType',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsOffscreen',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedOrientation',
        (['out', 'retval'], POINTER(OrientationType), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFrameworkId',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsRequiredForForm',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedItemStatus',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedBoundingRectangle',
        (['out', 'retval'], POINTER(tagRECT), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLabeledBy',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAriaRole',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAriaProperties',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsDataValidForForm',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedControllerFor',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDescribedBy',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFlowsTo',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedProviderDescription',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetClickablePoint',
        (['out'], POINTER(tagPOINT), 'clickable'),
        (['out', 'retval'], POINTER(c_int), 'gotClickable')
    ),
]


class IUIAutomationSynchronizedInputPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{2233BE0B-AFB7-448B-9FDA-3B378AA5EAE1}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def StartListening(self, inputType: hints.Incomplete) -> hints.Hresult: ...
        def Cancel(self) -> hints.Hresult: ...


IUIAutomationSynchronizedInputPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'StartListening',
        (['in'], SynchronizedInputType, 'inputType')
    ),
    COMMETHOD([], HRESULT, 'Cancel'),
]


class IUIAutomationFocusChangedEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{C270F6B5-5C69-4290-9745-7A7F97169468}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleFocusChangedEvent(self, sender: hints.Incomplete) -> hints.Hresult: ...


IUIAutomationFocusChangedEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleFocusChangedEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender')
    ),
]


class IUIAutomationTreeWalker(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{4042C624-389C-4AFC-A630-9DF854A541FC}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetParentElement(self, element: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetFirstChildElement(self, element: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetLastChildElement(self, element: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetNextSiblingElement(self, element: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetPreviousSiblingElement(self, element: hints.Incomplete) -> 'IUIAutomationElement': ...
        def NormalizeElement(self, element: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetParentElementBuildCache(self, element: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetFirstChildElementBuildCache(self, element: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetLastChildElementBuildCache(self, element: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetNextSiblingElementBuildCache(self, element: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetPreviousSiblingElementBuildCache(self, element: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def NormalizeElementBuildCache(self, element: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def _get_condition(self) -> 'IUIAutomationCondition': ...
        condition = hints.normal_property(_get_condition)


IUIAutomationTreeWalker._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetParentElement',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'parent')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetFirstChildElement',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'first')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetLastChildElement',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'last')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetNextSiblingElement',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'next')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetPreviousSiblingElement',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'previous')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'NormalizeElement',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElement)),
            'normalized',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetParentElementBuildCache',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'parent')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetFirstChildElementBuildCache',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'first')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetLastChildElementBuildCache',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'last')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetNextSiblingElementBuildCache',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'next')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetPreviousSiblingElementBuildCache',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'previous')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'NormalizeElementBuildCache',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElement)),
            'normalized',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'condition',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'condition',
        )
    ),
]


class IUIAutomationTextEditTextChangedEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{92FAA680-E704-4156-931A-E32D5BB38F3F}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleTextEditTextChangedEvent(self, sender: hints.Incomplete, TextEditChangeType: hints.Incomplete, eventStrings: hints.Incomplete) -> hints.Hresult: ...


IUIAutomationTextEditTextChangedEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleTextEditTextChangedEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        (['in'], TextEditChangeType, 'TextEditChangeType'),
        (['in'], _midlSAFEARRAY(BSTR), 'eventStrings')
    ),
]


class IUIAutomationNotCondition(IUIAutomationCondition):
    _case_insensitive_ = True
    _iid_ = GUID('{F528B657-847B-498C-8896-D52B565407A1}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetChild(self) -> 'IUIAutomationCondition': ...


IUIAutomationNotCondition._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetChild',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'condition',
        )
    ),
]


class IUIAutomationTablePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{620E691C-EA96-4710-A850-754B24CE2417}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetCurrentRowHeaders(self) -> 'IUIAutomationElementArray': ...
        def GetCurrentColumnHeaders(self) -> 'IUIAutomationElementArray': ...
        def _get_CurrentRowOrColumnMajor(self) -> hints.Incomplete: ...
        CurrentRowOrColumnMajor = hints.normal_property(_get_CurrentRowOrColumnMajor)
        def GetCachedRowHeaders(self) -> 'IUIAutomationElementArray': ...
        def GetCachedColumnHeaders(self) -> 'IUIAutomationElementArray': ...
        def _get_CachedRowOrColumnMajor(self) -> hints.Incomplete: ...
        CachedRowOrColumnMajor = hints.normal_property(_get_CachedRowOrColumnMajor)


IUIAutomationTablePattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentRowHeaders',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentColumnHeaders',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentRowOrColumnMajor',
        (['out', 'retval'], POINTER(RowOrColumnMajor), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedRowHeaders',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedColumnHeaders',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedRowOrColumnMajor',
        (['out', 'retval'], POINTER(RowOrColumnMajor), 'retVal')
    ),
]


class IUIAutomationElement2(IUIAutomationElement):
    _case_insensitive_ = True
    _iid_ = GUID('{6749C683-F70D-4487-A698-5F79D55290D6}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentOptimizeForVisualContent(self) -> hints.Incomplete: ...
        CurrentOptimizeForVisualContent = hints.normal_property(_get_CurrentOptimizeForVisualContent)
        def _get_CachedOptimizeForVisualContent(self) -> hints.Incomplete: ...
        CachedOptimizeForVisualContent = hints.normal_property(_get_CachedOptimizeForVisualContent)
        def _get_CurrentLiveSetting(self) -> hints.Incomplete: ...
        CurrentLiveSetting = hints.normal_property(_get_CurrentLiveSetting)
        def _get_CachedLiveSetting(self) -> hints.Incomplete: ...
        CachedLiveSetting = hints.normal_property(_get_CachedLiveSetting)
        def _get_CurrentFlowsFrom(self) -> 'IUIAutomationElementArray': ...
        CurrentFlowsFrom = hints.normal_property(_get_CurrentFlowsFrom)
        def _get_CachedFlowsFrom(self) -> 'IUIAutomationElementArray': ...
        CachedFlowsFrom = hints.normal_property(_get_CachedFlowsFrom)


class IUIAutomationElement3(IUIAutomationElement2):
    _case_insensitive_ = True
    _iid_ = GUID('{8471DF34-AEE0-4A01-A7DE-7DB9AF12C296}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def ShowContextMenu(self) -> hints.Hresult: ...
        def _get_CurrentIsPeripheral(self) -> hints.Incomplete: ...
        CurrentIsPeripheral = hints.normal_property(_get_CurrentIsPeripheral)
        def _get_CachedIsPeripheral(self) -> hints.Incomplete: ...
        CachedIsPeripheral = hints.normal_property(_get_CachedIsPeripheral)


class IUIAutomationElement4(IUIAutomationElement3):
    _case_insensitive_ = True
    _iid_ = GUID('{3B6E233C-52FB-4063-A4C9-77C075C2A06B}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentPositionInSet(self) -> hints.Incomplete: ...
        CurrentPositionInSet = hints.normal_property(_get_CurrentPositionInSet)
        def _get_CurrentSizeOfSet(self) -> hints.Incomplete: ...
        CurrentSizeOfSet = hints.normal_property(_get_CurrentSizeOfSet)
        def _get_CurrentLevel(self) -> hints.Incomplete: ...
        CurrentLevel = hints.normal_property(_get_CurrentLevel)
        def _get_CurrentAnnotationTypes(self) -> hints.Incomplete: ...
        CurrentAnnotationTypes = hints.normal_property(_get_CurrentAnnotationTypes)
        def _get_CurrentAnnotationObjects(self) -> 'IUIAutomationElementArray': ...
        CurrentAnnotationObjects = hints.normal_property(_get_CurrentAnnotationObjects)
        def _get_CachedPositionInSet(self) -> hints.Incomplete: ...
        CachedPositionInSet = hints.normal_property(_get_CachedPositionInSet)
        def _get_CachedSizeOfSet(self) -> hints.Incomplete: ...
        CachedSizeOfSet = hints.normal_property(_get_CachedSizeOfSet)
        def _get_CachedLevel(self) -> hints.Incomplete: ...
        CachedLevel = hints.normal_property(_get_CachedLevel)
        def _get_CachedAnnotationTypes(self) -> hints.Incomplete: ...
        CachedAnnotationTypes = hints.normal_property(_get_CachedAnnotationTypes)
        def _get_CachedAnnotationObjects(self) -> 'IUIAutomationElementArray': ...
        CachedAnnotationObjects = hints.normal_property(_get_CachedAnnotationObjects)


class IUIAutomationElement5(IUIAutomationElement4):
    _case_insensitive_ = True
    _iid_ = GUID('{98141C1D-0D0E-4175-BBE2-6BFF455842A7}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentLandmarkType(self) -> hints.Incomplete: ...
        CurrentLandmarkType = hints.normal_property(_get_CurrentLandmarkType)
        def _get_CurrentLocalizedLandmarkType(self) -> hints.Incomplete: ...
        CurrentLocalizedLandmarkType = hints.normal_property(_get_CurrentLocalizedLandmarkType)
        def _get_CachedLandmarkType(self) -> hints.Incomplete: ...
        CachedLandmarkType = hints.normal_property(_get_CachedLandmarkType)
        def _get_CachedLocalizedLandmarkType(self) -> hints.Incomplete: ...
        CachedLocalizedLandmarkType = hints.normal_property(_get_CachedLocalizedLandmarkType)


class IUIAutomationElement6(IUIAutomationElement5):
    _case_insensitive_ = True
    _iid_ = GUID('{4780D450-8BCA-4977-AFA5-A4A517F555E3}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentFullDescription(self) -> hints.Incomplete: ...
        CurrentFullDescription = hints.normal_property(_get_CurrentFullDescription)
        def _get_CachedFullDescription(self) -> hints.Incomplete: ...
        CachedFullDescription = hints.normal_property(_get_CachedFullDescription)


IUIAutomationElement2._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentOptimizeForVisualContent',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedOptimizeForVisualContent',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLiveSetting',
        (['out', 'retval'], POINTER(LiveSetting), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLiveSetting',
        (['out', 'retval'], POINTER(LiveSetting), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFlowsFrom',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFlowsFrom',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
]

IUIAutomationElement3._methods_ = [
    COMMETHOD([], HRESULT, 'ShowContextMenu'),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsPeripheral',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsPeripheral',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]

IUIAutomationElement4._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentPositionInSet',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentSizeOfSet',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLevel',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAnnotationTypes',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAnnotationObjects',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedPositionInSet',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedSizeOfSet',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLevel',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAnnotationTypes',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAnnotationObjects',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
]

IUIAutomationElement5._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLandmarkType',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLocalizedLandmarkType',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLandmarkType',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLocalizedLandmarkType',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
]

IUIAutomationElement6._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFullDescription',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFullDescription',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
]


class IUIAutomationDragPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{1DC7B570-1F54-4BAD-BCDA-D36A722FB7BD}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentIsGrabbed(self) -> hints.Incomplete: ...
        CurrentIsGrabbed = hints.normal_property(_get_CurrentIsGrabbed)
        def _get_CachedIsGrabbed(self) -> hints.Incomplete: ...
        CachedIsGrabbed = hints.normal_property(_get_CachedIsGrabbed)
        def _get_CurrentDropEffect(self) -> hints.Incomplete: ...
        CurrentDropEffect = hints.normal_property(_get_CurrentDropEffect)
        def _get_CachedDropEffect(self) -> hints.Incomplete: ...
        CachedDropEffect = hints.normal_property(_get_CachedDropEffect)
        def _get_CurrentDropEffects(self) -> hints.Incomplete: ...
        CurrentDropEffects = hints.normal_property(_get_CurrentDropEffects)
        def _get_CachedDropEffects(self) -> hints.Incomplete: ...
        CachedDropEffects = hints.normal_property(_get_CachedDropEffects)
        def GetCurrentGrabbedItems(self) -> 'IUIAutomationElementArray': ...
        def GetCachedGrabbedItems(self) -> 'IUIAutomationElementArray': ...


IUIAutomationDragPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsGrabbed',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsGrabbed',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDropEffect',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDropEffect',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDropEffects',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(BSTR)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDropEffects',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(BSTR)), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentGrabbedItems',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedGrabbedItems',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
]


class IUIAutomationChangesEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{58EDCA55-2C3E-4980-B1B9-56C17F27A2A0}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleChangesEvent(self, sender: hints.Incomplete, uiaChanges: hints.Incomplete, changesCount: hints.Incomplete) -> hints.Hresult: ...


class UiaChangeInfo(Structure):
    pass


IUIAutomationChangesEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleChangesEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        (['in'], POINTER(UiaChangeInfo), 'uiaChanges'),
        (['in'], c_int, 'changesCount')
    ),
]


class IUIAutomationElement7(IUIAutomationElement6):
    _case_insensitive_ = True
    _iid_ = GUID('{204E8572-CFC3-4C11-B0C8-7DA7420750B7}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def FindFirstWithOptions(self, scope: hints.Incomplete, condition: hints.Incomplete, traversalOptions: hints.Incomplete, root: hints.Incomplete) -> 'IUIAutomationElement': ...
        def FindAllWithOptions(self, scope: hints.Incomplete, condition: hints.Incomplete, traversalOptions: hints.Incomplete, root: hints.Incomplete) -> 'IUIAutomationElementArray': ...
        def FindFirstWithOptionsBuildCache(self, scope: hints.Incomplete, condition: hints.Incomplete, cacheRequest: hints.Incomplete, traversalOptions: hints.Incomplete, root: hints.Incomplete) -> 'IUIAutomationElement': ...
        def FindAllWithOptionsBuildCache(self, scope: hints.Incomplete, condition: hints.Incomplete, cacheRequest: hints.Incomplete, traversalOptions: hints.Incomplete, root: hints.Incomplete) -> 'IUIAutomationElementArray': ...
        def GetCurrentMetadataValue(self, targetId: hints.Incomplete, metadataId: hints.Incomplete) -> hints.Incomplete: ...


IUIAutomationElement7._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'FindFirstWithOptions',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['in'], TreeTraversalOptions, 'traversalOptions'),
        (['in'], POINTER(IUIAutomationElement), 'root'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'found')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindAllWithOptions',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['in'], TreeTraversalOptions, 'traversalOptions'),
        (['in'], POINTER(IUIAutomationElement), 'root'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'found',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindFirstWithOptionsBuildCache',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], TreeTraversalOptions, 'traversalOptions'),
        (['in'], POINTER(IUIAutomationElement), 'root'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'found')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindAllWithOptionsBuildCache',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], TreeTraversalOptions, 'traversalOptions'),
        (['in'], POINTER(IUIAutomationElement), 'root'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'found',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentMetadataValue',
        (['in'], c_int, 'targetId'),
        (['in'], c_int, 'metadataId'),
        (['out', 'retval'], POINTER(VARIANT), 'returnVal')
    ),
]


class IUIAutomation(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def CompareElements(self, el1: hints.Incomplete, el2: hints.Incomplete) -> hints.Incomplete: ...
        def CompareRuntimeIds(self, runtimeId1: hints.Incomplete, runtimeId2: hints.Incomplete) -> hints.Incomplete: ...
        def GetRootElement(self) -> 'IUIAutomationElement': ...
        def ElementFromHandle(self, hwnd: hints.Incomplete) -> 'IUIAutomationElement': ...
        def ElementFromPoint(self, pt: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetFocusedElement(self) -> 'IUIAutomationElement': ...
        def GetRootElementBuildCache(self, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def ElementFromHandleBuildCache(self, hwnd: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def ElementFromPointBuildCache(self, pt: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetFocusedElementBuildCache(self, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def CreateTreeWalker(self, pCondition: hints.Incomplete) -> 'IUIAutomationTreeWalker': ...
        def _get_ControlViewWalker(self) -> 'IUIAutomationTreeWalker': ...
        ControlViewWalker = hints.normal_property(_get_ControlViewWalker)
        def _get_ContentViewWalker(self) -> 'IUIAutomationTreeWalker': ...
        ContentViewWalker = hints.normal_property(_get_ContentViewWalker)
        def _get_RawViewWalker(self) -> 'IUIAutomationTreeWalker': ...
        RawViewWalker = hints.normal_property(_get_RawViewWalker)
        def _get_RawViewCondition(self) -> 'IUIAutomationCondition': ...
        RawViewCondition = hints.normal_property(_get_RawViewCondition)
        def _get_ControlViewCondition(self) -> 'IUIAutomationCondition': ...
        ControlViewCondition = hints.normal_property(_get_ControlViewCondition)
        def _get_ContentViewCondition(self) -> 'IUIAutomationCondition': ...
        ContentViewCondition = hints.normal_property(_get_ContentViewCondition)
        def CreateCacheRequest(self) -> 'IUIAutomationCacheRequest': ...
        def CreateTrueCondition(self) -> 'IUIAutomationCondition': ...
        def CreateFalseCondition(self) -> 'IUIAutomationCondition': ...
        def CreatePropertyCondition(self, propertyId: hints.Incomplete, value: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreatePropertyConditionEx(self, propertyId: hints.Incomplete, value: hints.Incomplete, flags: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateAndCondition(self, condition1: hints.Incomplete, condition2: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateAndConditionFromArray(self, conditions: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateAndConditionFromNativeArray(self, conditions: hints.Incomplete, conditionCount: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateOrCondition(self, condition1: hints.Incomplete, condition2: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateOrConditionFromArray(self, conditions: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateOrConditionFromNativeArray(self, conditions: hints.Incomplete, conditionCount: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def CreateNotCondition(self, condition: hints.Incomplete) -> 'IUIAutomationCondition': ...
        def AddAutomationEventHandler(self, eventId: hints.Incomplete, element: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveAutomationEventHandler(self, eventId: hints.Incomplete, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddPropertyChangedEventHandlerNativeArray(self, element: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete, propertyArray: hints.Incomplete, propertyCount: hints.Incomplete) -> hints.Hresult: ...
        def AddPropertyChangedEventHandler(self, element: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete, propertyArray: hints.Incomplete) -> hints.Hresult: ...
        def RemovePropertyChangedEventHandler(self, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddStructureChangedEventHandler(self, element: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveStructureChangedEventHandler(self, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddFocusChangedEventHandler(self, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveFocusChangedEventHandler(self, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveAllEventHandlers(self) -> hints.Hresult: ...
        def IntNativeArrayToSafeArray(self, array: hints.Incomplete, arrayCount: hints.Incomplete) -> hints.Incomplete: ...
        def IntSafeArrayToNativeArray(self, intArray: hints.Incomplete) -> tuple[hints.Incomplete, hints.Incomplete]: ...
        def RectToVariant(self, rc: hints.Incomplete) -> hints.Incomplete: ...
        def VariantToRect(self, var: hints.Incomplete) -> hints.Incomplete: ...
        def SafeArrayToRectNativeArray(self, rects: hints.Incomplete) -> tuple[hints.Incomplete, hints.Incomplete]: ...
        def CreateProxyFactoryEntry(self, factory: hints.Incomplete) -> 'IUIAutomationProxyFactoryEntry': ...
        def _get_ProxyFactoryMapping(self) -> 'IUIAutomationProxyFactoryMapping': ...
        ProxyFactoryMapping = hints.normal_property(_get_ProxyFactoryMapping)
        def GetPropertyProgrammaticName(self, property: hints.Incomplete) -> hints.Incomplete: ...
        def GetPatternProgrammaticName(self, pattern: hints.Incomplete) -> hints.Incomplete: ...
        def PollForPotentialSupportedPatterns(self, pElement: hints.Incomplete) -> tuple[hints.Incomplete, hints.Incomplete]: ...
        def PollForPotentialSupportedProperties(self, pElement: hints.Incomplete) -> tuple[hints.Incomplete, hints.Incomplete]: ...
        def CheckNotSupported(self, value: hints.Incomplete) -> hints.Incomplete: ...
        def _get_ReservedNotSupportedValue(self) -> 'IUnknown': ...
        ReservedNotSupportedValue = hints.normal_property(_get_ReservedNotSupportedValue)
        def _get_ReservedMixedAttributeValue(self) -> 'IUnknown': ...
        ReservedMixedAttributeValue = hints.normal_property(_get_ReservedMixedAttributeValue)
        def ElementFromIAccessible(self, accessible: hints.Incomplete, childId: hints.Incomplete) -> 'IUIAutomationElement': ...
        def ElementFromIAccessibleBuildCache(self, accessible: hints.Incomplete, childId: hints.Incomplete, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...


class IUIAutomationEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{146C3C17-F12E-4E22-8C27-F894B9B79C69}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleAutomationEvent(self, sender: hints.Incomplete, eventId: hints.Incomplete) -> hints.Hresult: ...


class IUIAutomationPropertyChangedEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{40CD37D4-C756-4B0C-8C6F-BDDFEEB13B50}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandlePropertyChangedEvent(self, sender: hints.Incomplete, propertyId: hints.Incomplete, newValue: hints.Incomplete) -> hints.Hresult: ...


class IUIAutomationStructureChangedEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{E81D1B4E-11C5-42F8-9754-E7036C79F054}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleStructureChangedEvent(self, sender: hints.Incomplete, changeType: hints.Incomplete, runtimeId: hints.Incomplete) -> hints.Hresult: ...


class IUIAutomationProxyFactory(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{85B94ECD-849D-42B6-B94D-D6DB23FDF5A4}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def CreateProvider(self, hwnd: hints.Incomplete, idObject: hints.Incomplete, idChild: hints.Incomplete) -> 'IRawElementProviderSimple': ...
        def _get_ProxyFactoryId(self) -> hints.Incomplete: ...
        ProxyFactoryId = hints.normal_property(_get_ProxyFactoryId)


class IUIAutomationProxyFactoryEntry(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{D50E472E-B64B-490C-BCA1-D30696F9F289}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_ProxyFactory(self) -> 'IUIAutomationProxyFactory': ...
        ProxyFactory = hints.normal_property(_get_ProxyFactory)
        def _get_ClassName(self) -> hints.Incomplete: ...
        def _set_ClassName(self, ClassName: hints.Incomplete) -> hints.Hresult: ...
        ClassName = hints.normal_property(_get_ClassName, _set_ClassName)
        def _get_ImageName(self) -> hints.Incomplete: ...
        def _set_ImageName(self, ImageName: hints.Incomplete) -> hints.Hresult: ...
        ImageName = hints.normal_property(_get_ImageName, _set_ImageName)
        def _get_AllowSubstringMatch(self) -> hints.Incomplete: ...
        def _set_AllowSubstringMatch(self, AllowSubstringMatch: hints.Incomplete) -> hints.Hresult: ...
        AllowSubstringMatch = hints.normal_property(_get_AllowSubstringMatch, _set_AllowSubstringMatch)
        def _get_CanCheckBaseClass(self) -> hints.Incomplete: ...
        def _set_CanCheckBaseClass(self, CanCheckBaseClass: hints.Incomplete) -> hints.Hresult: ...
        CanCheckBaseClass = hints.normal_property(_get_CanCheckBaseClass, _set_CanCheckBaseClass)
        def _get_NeedsAdviseEvents(self) -> hints.Incomplete: ...
        def _set_NeedsAdviseEvents(self, adviseEvents: hints.Incomplete) -> hints.Hresult: ...
        NeedsAdviseEvents = hints.normal_property(_get_NeedsAdviseEvents, _set_NeedsAdviseEvents)
        def SetWinEventsForAutomationEvent(self, eventId: hints.Incomplete, propertyId: hints.Incomplete, winEvents: hints.Incomplete) -> hints.Hresult: ...
        def GetWinEventsForAutomationEvent(self, eventId: hints.Incomplete, propertyId: hints.Incomplete) -> hints.Incomplete: ...


class IUIAutomationProxyFactoryMapping(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{09E31E18-872D-4873-93D1-1E541EC133FD}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_count(self) -> hints.Incomplete: ...
        count = hints.normal_property(_get_count)
        def GetTable(self) -> hints.Incomplete: ...
        def GetEntry(self, index: hints.Incomplete) -> 'IUIAutomationProxyFactoryEntry': ...
        def SetTable(self, factoryList: hints.Incomplete) -> hints.Hresult: ...
        def InsertEntries(self, before: hints.Incomplete, factoryList: hints.Incomplete) -> hints.Hresult: ...
        def InsertEntry(self, before: hints.Incomplete, factory: hints.Incomplete) -> hints.Hresult: ...
        def RemoveEntry(self, index: hints.Incomplete) -> hints.Hresult: ...
        def ClearTable(self) -> hints.Hresult: ...
        def RestoreDefaultTable(self) -> hints.Hresult: ...


class IAccessible(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IDispatch):
    _case_insensitive_ = True
    _iid_ = GUID('{618736E0-3C3D-11CF-810C-00AA00389B71}')
    _idlflags_ = ['hidden', 'dual', 'oleautomation']

    if TYPE_CHECKING:  # commembers
        def _get_accParent(self) -> 'IDispatch': ...
        accParent = hints.normal_property(_get_accParent)
        def _get_accChildCount(self) -> hints.Incomplete: ...
        accChildCount = hints.normal_property(_get_accChildCount)
        def _get_accChild(self, varChild: hints.Incomplete) -> 'IDispatch': ...
        accChild = hints.named_property('accChild', _get_accChild)
        def _get_accName(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        def _set_accName(self, varChild: hints.Incomplete = ..., /, *args: hints.Unpack[tuple[hints.Incomplete]]) -> hints.Hresult: ...
        accName = hints.named_property('accName', _get_accName, _set_accName)
        def _get_accValue(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        def _set_accValue(self, varChild: hints.Incomplete = ..., /, *args: hints.Unpack[tuple[hints.Incomplete]]) -> hints.Hresult: ...
        accValue = hints.named_property('accValue', _get_accValue, _set_accValue)
        def _get_accDescription(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        accDescription = hints.named_property('accDescription', _get_accDescription)
        def _get_accRole(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        accRole = hints.named_property('accRole', _get_accRole)
        def _get_accState(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        accState = hints.named_property('accState', _get_accState)
        def _get_accHelp(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        accHelp = hints.named_property('accHelp', _get_accHelp)
        def _get_accHelpTopic(self, varChild: hints.Incomplete = ...) -> tuple[hints.Incomplete, hints.Incomplete]: ...
        accHelpTopic = hints.named_property('accHelpTopic', _get_accHelpTopic)
        def _get_accKeyboardShortcut(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        accKeyboardShortcut = hints.named_property('accKeyboardShortcut', _get_accKeyboardShortcut)
        def _get_accFocus(self) -> hints.Incomplete: ...
        accFocus = hints.normal_property(_get_accFocus)
        def _get_accSelection(self) -> hints.Incomplete: ...
        accSelection = hints.normal_property(_get_accSelection)
        def _get_accDefaultAction(self, varChild: hints.Incomplete = ...) -> hints.Incomplete: ...
        accDefaultAction = hints.named_property('accDefaultAction', _get_accDefaultAction)
        def accSelect(self, flagsSelect: hints.Incomplete, varChild: hints.Incomplete = ...) -> hints.Hresult: ...
        def accLocation(self, varChild: hints.Incomplete = ...) -> tuple[hints.Incomplete, hints.Incomplete, hints.Incomplete, hints.Incomplete]: ...
        def accNavigate(self, navDir: hints.Incomplete, varStart: hints.Incomplete = ...) -> hints.Incomplete: ...
        def accHitTest(self, xLeft: hints.Incomplete, yTop: hints.Incomplete) -> hints.Incomplete: ...
        def accDoDefaultAction(self, varChild: hints.Incomplete = ...) -> hints.Hresult: ...


IUIAutomation._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'CompareElements',
        (['in'], POINTER(IUIAutomationElement), 'el1'),
        (['in'], POINTER(IUIAutomationElement), 'el2'),
        (['out', 'retval'], POINTER(c_int), 'areSame')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CompareRuntimeIds',
        (['in'], _midlSAFEARRAY(c_int), 'runtimeId1'),
        (['in'], _midlSAFEARRAY(c_int), 'runtimeId2'),
        (['out', 'retval'], POINTER(c_int), 'areSame')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetRootElement',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'root')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ElementFromHandle',
        (['in'], c_void_p, 'hwnd'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ElementFromPoint',
        (['in'], tagPOINT, 'pt'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetFocusedElement',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetRootElementBuildCache',
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'root')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ElementFromHandleBuildCache',
        (['in'], c_void_p, 'hwnd'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ElementFromPointBuildCache',
        (['in'], tagPOINT, 'pt'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetFocusedElementBuildCache',
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateTreeWalker',
        (['in'], POINTER(IUIAutomationCondition), 'pCondition'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTreeWalker)), 'walker')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ControlViewWalker',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTreeWalker)), 'walker')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ContentViewWalker',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTreeWalker)), 'walker')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'RawViewWalker',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTreeWalker)), 'walker')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'RawViewCondition',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'condition',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ControlViewCondition',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'condition',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ContentViewCondition',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'condition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateCacheRequest',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCacheRequest)),
            'cacheRequest',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateTrueCondition',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateFalseCondition',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreatePropertyCondition',
        (['in'], c_int, 'propertyId'),
        (['in'], VARIANT, 'value'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreatePropertyConditionEx',
        (['in'], c_int, 'propertyId'),
        (['in'], VARIANT, 'value'),
        (['in'], PropertyConditionFlags, 'flags'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateAndCondition',
        (['in'], POINTER(IUIAutomationCondition), 'condition1'),
        (['in'], POINTER(IUIAutomationCondition), 'condition2'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateAndConditionFromArray',
        (['in'], _midlSAFEARRAY(POINTER(IUIAutomationCondition)), 'conditions'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateAndConditionFromNativeArray',
        (['in'], POINTER(POINTER(IUIAutomationCondition)), 'conditions'),
        (['in'], c_int, 'conditionCount'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateOrCondition',
        (['in'], POINTER(IUIAutomationCondition), 'condition1'),
        (['in'], POINTER(IUIAutomationCondition), 'condition2'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateOrConditionFromArray',
        (['in'], _midlSAFEARRAY(POINTER(IUIAutomationCondition)), 'conditions'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateOrConditionFromNativeArray',
        (['in'], POINTER(POINTER(IUIAutomationCondition)), 'conditions'),
        (['in'], c_int, 'conditionCount'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateNotCondition',
        (['in'], POINTER(IUIAutomationCondition), 'condition'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCondition)),
            'newCondition',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddAutomationEventHandler',
        (['in'], c_int, 'eventId'),
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveAutomationEventHandler',
        (['in'], c_int, 'eventId'),
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddPropertyChangedEventHandlerNativeArray',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationPropertyChangedEventHandler), 'handler'),
        (['in'], POINTER(c_int), 'propertyArray'),
        (['in'], c_int, 'propertyCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddPropertyChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationPropertyChangedEventHandler), 'handler'),
        (['in'], _midlSAFEARRAY(c_int), 'propertyArray')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemovePropertyChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationPropertyChangedEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddStructureChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationStructureChangedEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveStructureChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationStructureChangedEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddFocusChangedEventHandler',
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationFocusChangedEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveFocusChangedEventHandler',
        (['in'], POINTER(IUIAutomationFocusChangedEventHandler), 'handler')
    ),
    COMMETHOD([], HRESULT, 'RemoveAllEventHandlers'),
    COMMETHOD(
        [],
        HRESULT,
        'IntNativeArrayToSafeArray',
        (['in'], POINTER(c_int), 'array'),
        (['in'], c_int, 'arrayCount'),
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'safeArray')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'IntSafeArrayToNativeArray',
        (['in'], _midlSAFEARRAY(c_int), 'intArray'),
        (['out'], POINTER(POINTER(c_int)), 'array'),
        (['out', 'retval'], POINTER(c_int), 'arrayCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RectToVariant',
        (['in'], tagRECT, 'rc'),
        (['out', 'retval'], POINTER(VARIANT), 'var')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'VariantToRect',
        (['in'], VARIANT, 'var'),
        (['out', 'retval'], POINTER(tagRECT), 'rc')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SafeArrayToRectNativeArray',
        (['in'], _midlSAFEARRAY(c_double), 'rects'),
        (['out'], POINTER(POINTER(tagRECT)), 'rectArray'),
        (['out', 'retval'], POINTER(c_int), 'rectArrayCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CreateProxyFactoryEntry',
        (['in'], POINTER(IUIAutomationProxyFactory), 'factory'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationProxyFactoryEntry)),
            'factoryEntry',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ProxyFactoryMapping',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationProxyFactoryMapping)),
            'factoryMapping',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetPropertyProgrammaticName',
        (['in'], c_int, 'property'),
        (['out', 'retval'], POINTER(BSTR), 'name')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetPatternProgrammaticName',
        (['in'], c_int, 'pattern'),
        (['out', 'retval'], POINTER(BSTR), 'name')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'PollForPotentialSupportedPatterns',
        (['in'], POINTER(IUIAutomationElement), 'pElement'),
        (['out'], POINTER(_midlSAFEARRAY(c_int)), 'patternIds'),
        (['out'], POINTER(_midlSAFEARRAY(BSTR)), 'patternNames')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'PollForPotentialSupportedProperties',
        (['in'], POINTER(IUIAutomationElement), 'pElement'),
        (['out'], POINTER(_midlSAFEARRAY(c_int)), 'propertyIds'),
        (['out'], POINTER(_midlSAFEARRAY(BSTR)), 'propertyNames')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CheckNotSupported',
        (['in'], VARIANT, 'value'),
        (['out', 'retval'], POINTER(c_int), 'isNotSupported')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ReservedNotSupportedValue',
        (['out', 'retval'], POINTER(POINTER(IUnknown)), 'notSupportedValue')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ReservedMixedAttributeValue',
        (['out', 'retval'], POINTER(POINTER(IUnknown)), 'mixedAttributeValue')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ElementFromIAccessible',
        (['in'], POINTER(IAccessible), 'accessible'),
        (['in'], c_int, 'childId'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ElementFromIAccessibleBuildCache',
        (['in'], POINTER(IAccessible), 'accessible'),
        (['in'], c_int, 'childId'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
]


class IUIAutomationMultipleViewPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{8D253C91-1DC5-4BB5-B18F-ADE16FA495E8}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetViewName(self, view: hints.Incomplete) -> hints.Incomplete: ...
        def SetCurrentView(self, view: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentCurrentView(self) -> hints.Incomplete: ...
        CurrentCurrentView = hints.normal_property(_get_CurrentCurrentView)
        def GetCurrentSupportedViews(self) -> hints.Incomplete: ...
        def _get_CachedCurrentView(self) -> hints.Incomplete: ...
        CachedCurrentView = hints.normal_property(_get_CachedCurrentView)
        def GetCachedSupportedViews(self) -> hints.Incomplete: ...


IUIAutomationMultipleViewPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetViewName',
        (['in'], c_int, 'view'),
        (['out', 'retval'], POINTER(BSTR), 'name')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetCurrentView',
        (['in'], c_int, 'view')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCurrentView',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentSupportedViews',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCurrentView',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedSupportedViews',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'retVal')
    ),
]


class IUIAutomationTableItemPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{0B964EB3-EF2E-4464-9C79-61D61737A27E}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetCurrentRowHeaderItems(self) -> 'IUIAutomationElementArray': ...
        def GetCurrentColumnHeaderItems(self) -> 'IUIAutomationElementArray': ...
        def GetCachedRowHeaderItems(self) -> 'IUIAutomationElementArray': ...
        def GetCachedColumnHeaderItems(self) -> 'IUIAutomationElementArray': ...


IUIAutomationTableItemPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentRowHeaderItems',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentColumnHeaderItems',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedRowHeaderItems',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedColumnHeaderItems',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
]

UiaChangeInfo._fields_ = [
    ('uiaId', c_int),
    ('payload', VARIANT),
    ('extraInfo', VARIANT),
]

assert sizeof(UiaChangeInfo) == 56, sizeof(UiaChangeInfo)
assert alignment(UiaChangeInfo) == 8, alignment(UiaChangeInfo)


class IUIAutomationNotificationEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{C7CB2637-E6C2-4D0C-85DE-4948C02175C7}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleNotificationEvent(self, sender: hints.Incomplete, NotificationKind: hints.Incomplete, NotificationProcessing: hints.Incomplete, displayString: hints.Incomplete, activityId: hints.Incomplete) -> hints.Hresult: ...


IUIAutomationNotificationEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleNotificationEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        ([], NotificationKind, 'NotificationKind'),
        ([], NotificationProcessing, 'NotificationProcessing'),
        (['in'], BSTR, 'displayString'),
        (['in'], BSTR, 'activityId')
    ),
]


class IUIAutomationScrollItemPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{B488300F-D015-4F19-9C29-BB595E3645EF}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def ScrollIntoView(self) -> hints.Hresult: ...


IUIAutomationScrollItemPattern._methods_ = [
    COMMETHOD([], HRESULT, 'ScrollIntoView'),
]

IUIAutomationProxyFactoryEntry._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ProxyFactory',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationProxyFactory)),
            'factory',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ClassName',
        (['out', 'retval'], POINTER(BSTR), 'ClassName')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ImageName',
        (['out', 'retval'], POINTER(BSTR), 'ImageName')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'AllowSubstringMatch',
        (['out', 'retval'], POINTER(c_int), 'AllowSubstringMatch')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CanCheckBaseClass',
        (['out', 'retval'], POINTER(c_int), 'CanCheckBaseClass')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'NeedsAdviseEvents',
        (['out', 'retval'], POINTER(c_int), 'adviseEvents')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'ClassName',
        (['in'], WSTRING, 'ClassName')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'ImageName',
        (['in'], WSTRING, 'ImageName')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'AllowSubstringMatch',
        (['in'], c_int, 'AllowSubstringMatch')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'CanCheckBaseClass',
        (['in'], c_int, 'CanCheckBaseClass')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'NeedsAdviseEvents',
        (['in'], c_int, 'adviseEvents')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetWinEventsForAutomationEvent',
        (['in'], c_int, 'eventId'),
        (['in'], c_int, 'propertyId'),
        (['in'], _midlSAFEARRAY(c_uint), 'winEvents')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetWinEventsForAutomationEvent',
        (['in'], c_int, 'eventId'),
        (['in'], c_int, 'propertyId'),
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_uint)), 'winEvents')
    ),
]


class IUIAutomationSelectionPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{5ED5202E-B2AC-47A6-B638-4B0BF140D78E}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetCurrentSelection(self) -> 'IUIAutomationElementArray': ...
        def _get_CurrentCanSelectMultiple(self) -> hints.Incomplete: ...
        CurrentCanSelectMultiple = hints.normal_property(_get_CurrentCanSelectMultiple)
        def _get_CurrentIsSelectionRequired(self) -> hints.Incomplete: ...
        CurrentIsSelectionRequired = hints.normal_property(_get_CurrentIsSelectionRequired)
        def GetCachedSelection(self) -> 'IUIAutomationElementArray': ...
        def _get_CachedCanSelectMultiple(self) -> hints.Incomplete: ...
        CachedCanSelectMultiple = hints.normal_property(_get_CachedCanSelectMultiple)
        def _get_CachedIsSelectionRequired(self) -> hints.Incomplete: ...
        CachedIsSelectionRequired = hints.normal_property(_get_CachedIsSelectionRequired)


IUIAutomationSelectionPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentSelection',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanSelectMultiple',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsSelectionRequired',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedSelection',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanSelectMultiple',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsSelectionRequired',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]


class IUIAutomationInvokePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{FB377FBE-8EA6-46D5-9C73-6499642D3059}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Invoke(self) -> hints.Hresult: ...


IUIAutomationInvokePattern._methods_ = [
    COMMETHOD([], HRESULT, 'Invoke'),
]


class IUIAutomationObjectModelPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{71C284B3-C14D-4D14-981E-19751B0D756D}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetUnderlyingObjectModel(self) -> 'IUnknown': ...


IUIAutomationObjectModelPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetUnderlyingObjectModel',
        (['out', 'retval'], POINTER(POINTER(IUnknown)), 'retVal')
    ),
]


class IUIAutomationDropTargetPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{69A095F7-EEE4-430E-A46B-FB73B1AE39A5}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentDropTargetEffect(self) -> hints.Incomplete: ...
        CurrentDropTargetEffect = hints.normal_property(_get_CurrentDropTargetEffect)
        def _get_CachedDropTargetEffect(self) -> hints.Incomplete: ...
        CachedDropTargetEffect = hints.normal_property(_get_CachedDropTargetEffect)
        def _get_CurrentDropTargetEffects(self) -> hints.Incomplete: ...
        CurrentDropTargetEffects = hints.normal_property(_get_CurrentDropTargetEffects)
        def _get_CachedDropTargetEffects(self) -> hints.Incomplete: ...
        CachedDropTargetEffects = hints.normal_property(_get_CachedDropTargetEffects)


IUIAutomationDropTargetPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDropTargetEffect',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDropTargetEffect',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDropTargetEffects',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(BSTR)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDropTargetEffects',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(BSTR)), 'retVal')
    ),
]


class IUIAutomationTogglePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{94CF8058-9B8D-4AB9-8BFD-4CD0A33C8C70}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Toggle(self) -> hints.Hresult: ...
        def _get_CurrentToggleState(self) -> hints.Incomplete: ...
        CurrentToggleState = hints.normal_property(_get_CurrentToggleState)
        def _get_CachedToggleState(self) -> hints.Incomplete: ...
        CachedToggleState = hints.normal_property(_get_CachedToggleState)


IUIAutomationTogglePattern._methods_ = [
    COMMETHOD([], HRESULT, 'Toggle'),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentToggleState',
        (['out', 'retval'], POINTER(ToggleState), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedToggleState',
        (['out', 'retval'], POINTER(ToggleState), 'retVal')
    ),
]


class IUIAutomationRangeValuePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{59213F4F-7346-49E5-B120-80555987A148}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def SetValue(self, val: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentValue(self) -> hints.Incomplete: ...
        CurrentValue = hints.normal_property(_get_CurrentValue)
        def _get_CurrentIsReadOnly(self) -> hints.Incomplete: ...
        CurrentIsReadOnly = hints.normal_property(_get_CurrentIsReadOnly)
        def _get_CurrentMaximum(self) -> hints.Incomplete: ...
        CurrentMaximum = hints.normal_property(_get_CurrentMaximum)
        def _get_CurrentMinimum(self) -> hints.Incomplete: ...
        CurrentMinimum = hints.normal_property(_get_CurrentMinimum)
        def _get_CurrentLargeChange(self) -> hints.Incomplete: ...
        CurrentLargeChange = hints.normal_property(_get_CurrentLargeChange)
        def _get_CurrentSmallChange(self) -> hints.Incomplete: ...
        CurrentSmallChange = hints.normal_property(_get_CurrentSmallChange)
        def _get_CachedValue(self) -> hints.Incomplete: ...
        CachedValue = hints.normal_property(_get_CachedValue)
        def _get_CachedIsReadOnly(self) -> hints.Incomplete: ...
        CachedIsReadOnly = hints.normal_property(_get_CachedIsReadOnly)
        def _get_CachedMaximum(self) -> hints.Incomplete: ...
        CachedMaximum = hints.normal_property(_get_CachedMaximum)
        def _get_CachedMinimum(self) -> hints.Incomplete: ...
        CachedMinimum = hints.normal_property(_get_CachedMinimum)
        def _get_CachedLargeChange(self) -> hints.Incomplete: ...
        CachedLargeChange = hints.normal_property(_get_CachedLargeChange)
        def _get_CachedSmallChange(self) -> hints.Incomplete: ...
        CachedSmallChange = hints.normal_property(_get_CachedSmallChange)


IUIAutomationRangeValuePattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'SetValue',
        (['in'], c_double, 'val')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentValue',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsReadOnly',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentMaximum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentMinimum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLargeChange',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentSmallChange',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedValue',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsReadOnly',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedMaximum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedMinimum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLargeChange',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedSmallChange',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
]

UIA_SelectionPatternId = 10001  # Constant c_int


class IUIAutomationTextRange(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{A543CC6A-F4AE-494B-8239-C814481187A8}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Clone(self) -> 'IUIAutomationTextRange': ...
        def Compare(self, range: hints.Incomplete) -> hints.Incomplete: ...
        def CompareEndpoints(self, srcEndPoint: hints.Incomplete, range: hints.Incomplete, targetEndPoint: hints.Incomplete) -> hints.Incomplete: ...
        def ExpandToEnclosingUnit(self, TextUnit: hints.Incomplete) -> hints.Hresult: ...
        def FindAttribute(self, attr: hints.Incomplete, val: hints.Incomplete, backward: hints.Incomplete) -> 'IUIAutomationTextRange': ...
        def FindText(self, text: hints.Incomplete, backward: hints.Incomplete, ignoreCase: hints.Incomplete) -> 'IUIAutomationTextRange': ...
        def GetAttributeValue(self, attr: hints.Incomplete) -> hints.Incomplete: ...
        def GetBoundingRectangles(self) -> hints.Incomplete: ...
        def GetEnclosingElement(self) -> 'IUIAutomationElement': ...
        def GetText(self, maxLength: hints.Incomplete) -> hints.Incomplete: ...
        def Move(self, unit: hints.Incomplete, count: hints.Incomplete) -> hints.Incomplete: ...
        def MoveEndpointByUnit(self, endpoint: hints.Incomplete, unit: hints.Incomplete, count: hints.Incomplete) -> hints.Incomplete: ...
        def MoveEndpointByRange(self, srcEndPoint: hints.Incomplete, range: hints.Incomplete, targetEndPoint: hints.Incomplete) -> hints.Hresult: ...
        def Select(self) -> hints.Hresult: ...
        def AddToSelection(self) -> hints.Hresult: ...
        def RemoveFromSelection(self) -> hints.Hresult: ...
        def ScrollIntoView(self, alignToTop: hints.Incomplete) -> hints.Hresult: ...
        def GetChildren(self) -> 'IUIAutomationElementArray': ...


IUIAutomationTextRange._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'Clone',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationTextRange)),
            'clonedRange',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Compare',
        (['in'], POINTER(IUIAutomationTextRange), 'range'),
        (['out', 'retval'], POINTER(c_int), 'areSame')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'CompareEndpoints',
        (['in'], TextPatternRangeEndpoint, 'srcEndPoint'),
        (['in'], POINTER(IUIAutomationTextRange), 'range'),
        (['in'], TextPatternRangeEndpoint, 'targetEndPoint'),
        (['out', 'retval'], POINTER(c_int), 'compValue')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ExpandToEnclosingUnit',
        (['in'], TextUnit, 'TextUnit')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindAttribute',
        (['in'], c_int, 'attr'),
        (['in'], VARIANT, 'val'),
        (['in'], c_int, 'backward'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'found')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'FindText',
        (['in'], BSTR, 'text'),
        (['in'], c_int, 'backward'),
        (['in'], c_int, 'ignoreCase'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'found')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetAttributeValue',
        (['in'], c_int, 'attr'),
        (['out', 'retval'], POINTER(VARIANT), 'value')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetBoundingRectangles',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_double)), 'boundingRects')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetEnclosingElement',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElement)),
            'enclosingElement',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetText',
        (['in'], c_int, 'maxLength'),
        (['out', 'retval'], POINTER(BSTR), 'text')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Move',
        (['in'], TextUnit, 'unit'),
        (['in'], c_int, 'count'),
        (['out', 'retval'], POINTER(c_int), 'moved')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'MoveEndpointByUnit',
        (['in'], TextPatternRangeEndpoint, 'endpoint'),
        (['in'], TextUnit, 'unit'),
        (['in'], c_int, 'count'),
        (['out', 'retval'], POINTER(c_int), 'moved')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'MoveEndpointByRange',
        (['in'], TextPatternRangeEndpoint, 'srcEndPoint'),
        (['in'], POINTER(IUIAutomationTextRange), 'range'),
        (['in'], TextPatternRangeEndpoint, 'targetEndPoint')
    ),
    COMMETHOD([], HRESULT, 'Select'),
    COMMETHOD([], HRESULT, 'AddToSelection'),
    COMMETHOD([], HRESULT, 'RemoveFromSelection'),
    COMMETHOD(
        [],
        HRESULT,
        'ScrollIntoView',
        (['in'], c_int, 'alignToTop')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetChildren',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'children',
        )
    ),
]


class IUIAutomationDockPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{FDE5EF97-1464-48F6-90BF-43D0948E86EC}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def SetDockPosition(self, dockPos: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentDockPosition(self) -> hints.Incomplete: ...
        CurrentDockPosition = hints.normal_property(_get_CurrentDockPosition)
        def _get_CachedDockPosition(self) -> hints.Incomplete: ...
        CachedDockPosition = hints.normal_property(_get_CachedDockPosition)


IUIAutomationDockPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'SetDockPosition',
        (['in'], DockPosition, 'dockPos')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDockPosition',
        (['out', 'retval'], POINTER(DockPosition), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDockPosition',
        (['out', 'retval'], POINTER(DockPosition), 'retVal')
    ),
]


class IUIAutomationSelectionPattern2(IUIAutomationSelectionPattern):
    _case_insensitive_ = True
    _iid_ = GUID('{0532BFAE-C011-4E32-A343-6D642D798555}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentFirstSelectedItem(self) -> 'IUIAutomationElement': ...
        CurrentFirstSelectedItem = hints.normal_property(_get_CurrentFirstSelectedItem)
        def _get_CurrentLastSelectedItem(self) -> 'IUIAutomationElement': ...
        CurrentLastSelectedItem = hints.normal_property(_get_CurrentLastSelectedItem)
        def _get_CurrentCurrentSelectedItem(self) -> 'IUIAutomationElement': ...
        CurrentCurrentSelectedItem = hints.normal_property(_get_CurrentCurrentSelectedItem)
        def _get_CurrentItemCount(self) -> hints.Incomplete: ...
        CurrentItemCount = hints.normal_property(_get_CurrentItemCount)
        def _get_CachedFirstSelectedItem(self) -> 'IUIAutomationElement': ...
        CachedFirstSelectedItem = hints.normal_property(_get_CachedFirstSelectedItem)
        def _get_CachedLastSelectedItem(self) -> 'IUIAutomationElement': ...
        CachedLastSelectedItem = hints.normal_property(_get_CachedLastSelectedItem)
        def _get_CachedCurrentSelectedItem(self) -> 'IUIAutomationElement': ...
        CachedCurrentSelectedItem = hints.normal_property(_get_CachedCurrentSelectedItem)
        def _get_CachedItemCount(self) -> hints.Incomplete: ...
        CachedItemCount = hints.normal_property(_get_CachedItemCount)


IUIAutomationSelectionPattern2._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFirstSelectedItem',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentLastSelectedItem',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCurrentSelectedItem',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentItemCount',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFirstSelectedItem',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedLastSelectedItem',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCurrentSelectedItem',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedItemCount',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]

UIA_BackgroundColorAttributeId = 40001  # Constant c_int


class IUIAutomationValuePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{A94CD8B1-0844-4CD6-9D2D-640537AB39E9}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def SetValue(self, val: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentValue(self) -> hints.Incomplete: ...
        CurrentValue = hints.normal_property(_get_CurrentValue)
        def _get_CurrentIsReadOnly(self) -> hints.Incomplete: ...
        CurrentIsReadOnly = hints.normal_property(_get_CurrentIsReadOnly)
        def _get_CachedValue(self) -> hints.Incomplete: ...
        CachedValue = hints.normal_property(_get_CachedValue)
        def _get_CachedIsReadOnly(self) -> hints.Incomplete: ...
        CachedIsReadOnly = hints.normal_property(_get_CachedIsReadOnly)


IUIAutomationValuePattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'SetValue',
        (['in'], BSTR, 'val')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentValue',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsReadOnly',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedValue',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsReadOnly',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]


class IUIAutomationTransformPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{A9B55844-A55D-4EF0-926D-569C16FF89BB}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Move(self, x: hints.Incomplete, y: hints.Incomplete) -> hints.Hresult: ...
        def Resize(self, width: hints.Incomplete, height: hints.Incomplete) -> hints.Hresult: ...
        def Rotate(self, degrees: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentCanMove(self) -> hints.Incomplete: ...
        CurrentCanMove = hints.normal_property(_get_CurrentCanMove)
        def _get_CurrentCanResize(self) -> hints.Incomplete: ...
        CurrentCanResize = hints.normal_property(_get_CurrentCanResize)
        def _get_CurrentCanRotate(self) -> hints.Incomplete: ...
        CurrentCanRotate = hints.normal_property(_get_CurrentCanRotate)
        def _get_CachedCanMove(self) -> hints.Incomplete: ...
        CachedCanMove = hints.normal_property(_get_CachedCanMove)
        def _get_CachedCanResize(self) -> hints.Incomplete: ...
        CachedCanResize = hints.normal_property(_get_CachedCanResize)
        def _get_CachedCanRotate(self) -> hints.Incomplete: ...
        CachedCanRotate = hints.normal_property(_get_CachedCanRotate)


IUIAutomationTransformPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'Move',
        (['in'], c_double, 'x'),
        (['in'], c_double, 'y')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Resize',
        (['in'], c_double, 'width'),
        (['in'], c_double, 'height')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Rotate',
        (['in'], c_double, 'degrees')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanMove',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanResize',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanRotate',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanMove',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanResize',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanRotate',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]


class IUIAutomationElement8(IUIAutomationElement7):
    _case_insensitive_ = True
    _iid_ = GUID('{8C60217D-5411-4CDE-BCC0-1CEDA223830C}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentHeadingLevel(self) -> hints.Incomplete: ...
        CurrentHeadingLevel = hints.normal_property(_get_CurrentHeadingLevel)
        def _get_CachedHeadingLevel(self) -> hints.Incomplete: ...
        CachedHeadingLevel = hints.normal_property(_get_CachedHeadingLevel)


IUIAutomationElement8._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHeadingLevel',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHeadingLevel',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]


class IUIAutomationPropertyCondition(IUIAutomationCondition):
    _case_insensitive_ = True
    _iid_ = GUID('{99EBF2CB-5578-4267-9AD4-AFD6EA77E94B}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_propertyId(self) -> hints.Incomplete: ...
        propertyId = hints.normal_property(_get_propertyId)
        def _get_PropertyValue(self) -> hints.Incomplete: ...
        PropertyValue = hints.normal_property(_get_PropertyValue)
        def _get_PropertyConditionFlags(self) -> hints.Incomplete: ...
        PropertyConditionFlags = hints.normal_property(_get_PropertyConditionFlags)


IUIAutomationPropertyCondition._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'propertyId',
        (['out', 'retval'], POINTER(c_int), 'propertyId')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'PropertyValue',
        (['out', 'retval'], POINTER(VARIANT), 'PropertyValue')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'PropertyConditionFlags',
        (['out', 'retval'], POINTER(PropertyConditionFlags), 'flags')
    ),
]

IUIAutomationPropertyChangedEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandlePropertyChangedEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        (['in'], c_int, 'propertyId'),
        (['in'], VARIANT, 'newValue')
    ),
]


class IUIAutomationExpandCollapsePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{619BE086-1F4E-4EE4-BAFA-210128738730}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Expand(self) -> hints.Hresult: ...
        def Collapse(self) -> hints.Hresult: ...
        def _get_CurrentExpandCollapseState(self) -> hints.Incomplete: ...
        CurrentExpandCollapseState = hints.normal_property(_get_CurrentExpandCollapseState)
        def _get_CachedExpandCollapseState(self) -> hints.Incomplete: ...
        CachedExpandCollapseState = hints.normal_property(_get_CachedExpandCollapseState)


IUIAutomationExpandCollapsePattern._methods_ = [
    COMMETHOD([], HRESULT, 'Expand'),
    COMMETHOD([], HRESULT, 'Collapse'),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentExpandCollapseState',
        (['out', 'retval'], POINTER(ExpandCollapseState), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedExpandCollapseState',
        (['out', 'retval'], POINTER(ExpandCollapseState), 'retVal')
    ),
]


class Library(object):
    name = 'UIAutomationClient'
    _reg_typelib_ = ('{944DE083-8FB8-45CF-BCB7-C477ACB2F897}', 1, 0)


class IUIAutomationElement9(IUIAutomationElement8):
    _case_insensitive_ = True
    _iid_ = GUID('{39325FAC-039D-440E-A3A3-5EB81A5CECC3}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentIsDialog(self) -> hints.Incomplete: ...
        CurrentIsDialog = hints.normal_property(_get_CurrentIsDialog)
        def _get_CachedIsDialog(self) -> hints.Incomplete: ...
        CachedIsDialog = hints.normal_property(_get_CachedIsDialog)


IUIAutomationElement9._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsDialog',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsDialog',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]

UIA_TransformPattern2Id = 10028  # Constant c_int

IUIAutomationEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleAutomationEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        (['in'], c_int, 'eventId')
    ),
]

UIA_SpreadsheetPatternId = 10026  # Constant c_int


class IUIAutomationBoolCondition(IUIAutomationCondition):
    _case_insensitive_ = True
    _iid_ = GUID('{1B4E1F2E-75EB-4D0B-8952-5A69988E2307}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_BooleanValue(self) -> hints.Incomplete: ...
        BooleanValue = hints.normal_property(_get_BooleanValue)


IUIAutomationBoolCondition._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'BooleanValue',
        (['out', 'retval'], POINTER(c_int), 'boolVal')
    ),
]

UIA_InvokePatternId = 10000  # Constant c_int
UIA_DragPatternId = 10030  # Constant c_int
UIA_SpreadsheetItemPatternId = 10027  # Constant c_int
UIA_ValuePatternId = 10002  # Constant c_int
UIA_RangeValuePatternId = 10003  # Constant c_int
UIA_ScrollPatternId = 10004  # Constant c_int
UIA_ExpandCollapsePatternId = 10005  # Constant c_int


class IUIAutomationSelectionItemPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{A8EFA66A-0FDA-421A-9194-38021F3578EA}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Select(self) -> hints.Hresult: ...
        def AddToSelection(self) -> hints.Hresult: ...
        def RemoveFromSelection(self) -> hints.Hresult: ...
        def _get_CurrentIsSelected(self) -> hints.Incomplete: ...
        CurrentIsSelected = hints.normal_property(_get_CurrentIsSelected)
        def _get_CurrentSelectionContainer(self) -> 'IUIAutomationElement': ...
        CurrentSelectionContainer = hints.normal_property(_get_CurrentSelectionContainer)
        def _get_CachedIsSelected(self) -> hints.Incomplete: ...
        CachedIsSelected = hints.normal_property(_get_CachedIsSelected)
        def _get_CachedSelectionContainer(self) -> 'IUIAutomationElement': ...
        CachedSelectionContainer = hints.normal_property(_get_CachedSelectionContainer)


IUIAutomationSelectionItemPattern._methods_ = [
    COMMETHOD([], HRESULT, 'Select'),
    COMMETHOD([], HRESULT, 'AddToSelection'),
    COMMETHOD([], HRESULT, 'RemoveFromSelection'),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsSelected',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentSelectionContainer',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsSelected',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedSelectionContainer',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
]

UIA_GridPatternId = 10006  # Constant c_int
UIA_GridItemPatternId = 10007  # Constant c_int
UIA_MultipleViewPatternId = 10008  # Constant c_int


class IRawElementProviderSimple(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{D6DD68D1-86FD-4332-8666-9ABEDEA2D24C}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def _get_ProviderOptions(self) -> hints.Incomplete: ...
        ProviderOptions = hints.normal_property(_get_ProviderOptions)
        def GetPatternProvider(self, patternId: hints.Incomplete) -> 'IUnknown': ...
        def GetPropertyValue(self, propertyId: hints.Incomplete) -> hints.Incomplete: ...
        def _get_HostRawElementProvider(self) -> 'IRawElementProviderSimple': ...
        HostRawElementProvider = hints.normal_property(_get_HostRawElementProvider)


IUIAutomationProxyFactory._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'CreateProvider',
        (['in'], c_void_p, 'hwnd'),
        (['in'], c_int, 'idObject'),
        (['in'], c_int, 'idChild'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IRawElementProviderSimple)),
            'provider',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ProxyFactoryId',
        (['out', 'retval'], POINTER(BSTR), 'factoryId')
    ),
]

UIA_WindowPatternId = 10009  # Constant c_int
UIA_SelectionItemPatternId = 10010  # Constant c_int
UIA_DockPatternId = 10011  # Constant c_int
UIA_TablePatternId = 10012  # Constant c_int
UIA_TableItemPatternId = 10013  # Constant c_int
UIA_TextPatternId = 10014  # Constant c_int
UIA_TogglePatternId = 10015  # Constant c_int
UIA_TransformPatternId = 10016  # Constant c_int
UIA_ScrollItemPatternId = 10017  # Constant c_int


class IUIAutomationAndCondition(IUIAutomationCondition):
    _case_insensitive_ = True
    _iid_ = GUID('{A7D0AF36-B912-45FE-9855-091DDC174AEC}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_ChildCount(self) -> hints.Incomplete: ...
        ChildCount = hints.normal_property(_get_ChildCount)
        def GetChildrenAsNativeArray(self) -> tuple['IUIAutomationCondition', hints.Incomplete]: ...
        def GetChildren(self) -> hints.Incomplete: ...


IUIAutomationAndCondition._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ChildCount',
        (['out', 'retval'], POINTER(c_int), 'ChildCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetChildrenAsNativeArray',
        (
            ['out'],
            POINTER(POINTER(POINTER(IUIAutomationCondition))),
            'childArray',
        ),
        (['out'], POINTER(c_int), 'childArrayCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetChildren',
        (
            ['out', 'retval'],
            POINTER(_midlSAFEARRAY(POINTER(IUIAutomationCondition))),
            'childArray',
        )
    ),
]

UIA_LegacyIAccessiblePatternId = 10018  # Constant c_int
UIA_ItemContainerPatternId = 10019  # Constant c_int


class IUIAutomationScrollPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{88F4D42A-E881-459D-A77C-73BBBB7E02DC}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Scroll(self, horizontalAmount: hints.Incomplete, verticalAmount: hints.Incomplete) -> hints.Hresult: ...
        def SetScrollPercent(self, horizontalPercent: hints.Incomplete, verticalPercent: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentHorizontalScrollPercent(self) -> hints.Incomplete: ...
        CurrentHorizontalScrollPercent = hints.normal_property(_get_CurrentHorizontalScrollPercent)
        def _get_CurrentVerticalScrollPercent(self) -> hints.Incomplete: ...
        CurrentVerticalScrollPercent = hints.normal_property(_get_CurrentVerticalScrollPercent)
        def _get_CurrentHorizontalViewSize(self) -> hints.Incomplete: ...
        CurrentHorizontalViewSize = hints.normal_property(_get_CurrentHorizontalViewSize)
        def _get_CurrentVerticalViewSize(self) -> hints.Incomplete: ...
        CurrentVerticalViewSize = hints.normal_property(_get_CurrentVerticalViewSize)
        def _get_CurrentHorizontallyScrollable(self) -> hints.Incomplete: ...
        CurrentHorizontallyScrollable = hints.normal_property(_get_CurrentHorizontallyScrollable)
        def _get_CurrentVerticallyScrollable(self) -> hints.Incomplete: ...
        CurrentVerticallyScrollable = hints.normal_property(_get_CurrentVerticallyScrollable)
        def _get_CachedHorizontalScrollPercent(self) -> hints.Incomplete: ...
        CachedHorizontalScrollPercent = hints.normal_property(_get_CachedHorizontalScrollPercent)
        def _get_CachedVerticalScrollPercent(self) -> hints.Incomplete: ...
        CachedVerticalScrollPercent = hints.normal_property(_get_CachedVerticalScrollPercent)
        def _get_CachedHorizontalViewSize(self) -> hints.Incomplete: ...
        CachedHorizontalViewSize = hints.normal_property(_get_CachedHorizontalViewSize)
        def _get_CachedVerticalViewSize(self) -> hints.Incomplete: ...
        CachedVerticalViewSize = hints.normal_property(_get_CachedVerticalViewSize)
        def _get_CachedHorizontallyScrollable(self) -> hints.Incomplete: ...
        CachedHorizontallyScrollable = hints.normal_property(_get_CachedHorizontallyScrollable)
        def _get_CachedVerticallyScrollable(self) -> hints.Incomplete: ...
        CachedVerticallyScrollable = hints.normal_property(_get_CachedVerticallyScrollable)


IUIAutomationScrollPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'Scroll',
        (['in'], ScrollAmount, 'horizontalAmount'),
        (['in'], ScrollAmount, 'verticalAmount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetScrollPercent',
        (['in'], c_double, 'horizontalPercent'),
        (['in'], c_double, 'verticalPercent')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHorizontalScrollPercent',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentVerticalScrollPercent',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHorizontalViewSize',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentVerticalViewSize',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHorizontallyScrollable',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentVerticallyScrollable',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHorizontalScrollPercent',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedVerticalScrollPercent',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHorizontalViewSize',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedVerticalViewSize',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHorizontallyScrollable',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedVerticallyScrollable',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]

UIA_VirtualizedItemPatternId = 10020  # Constant c_int
UIA_SynchronizedInputPatternId = 10021  # Constant c_int
UIA_ObjectModelPatternId = 10022  # Constant c_int
UIA_AnnotationPatternId = 10023  # Constant c_int


class IUIAutomationGridPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{414C3CDC-856B-4F5B-8538-3131C6302550}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetItem(self, row: hints.Incomplete, column: hints.Incomplete) -> 'IUIAutomationElement': ...
        def _get_CurrentRowCount(self) -> hints.Incomplete: ...
        CurrentRowCount = hints.normal_property(_get_CurrentRowCount)
        def _get_CurrentColumnCount(self) -> hints.Incomplete: ...
        CurrentColumnCount = hints.normal_property(_get_CurrentColumnCount)
        def _get_CachedRowCount(self) -> hints.Incomplete: ...
        CachedRowCount = hints.normal_property(_get_CachedRowCount)
        def _get_CachedColumnCount(self) -> hints.Incomplete: ...
        CachedColumnCount = hints.normal_property(_get_CachedColumnCount)


IUIAutomationGridPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetItem',
        (['in'], c_int, 'row'),
        (['in'], c_int, 'column'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentRowCount',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentColumnCount',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedRowCount',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedColumnCount',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]

UIA_TextChildPatternId = 10029  # Constant c_int


class IUIAutomationGridItemPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{78F8EF57-66C3-4E09-BD7C-E79B2004894D}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentContainingGrid(self) -> 'IUIAutomationElement': ...
        CurrentContainingGrid = hints.normal_property(_get_CurrentContainingGrid)
        def _get_CurrentRow(self) -> hints.Incomplete: ...
        CurrentRow = hints.normal_property(_get_CurrentRow)
        def _get_CurrentColumn(self) -> hints.Incomplete: ...
        CurrentColumn = hints.normal_property(_get_CurrentColumn)
        def _get_CurrentRowSpan(self) -> hints.Incomplete: ...
        CurrentRowSpan = hints.normal_property(_get_CurrentRowSpan)
        def _get_CurrentColumnSpan(self) -> hints.Incomplete: ...
        CurrentColumnSpan = hints.normal_property(_get_CurrentColumnSpan)
        def _get_CachedContainingGrid(self) -> 'IUIAutomationElement': ...
        CachedContainingGrid = hints.normal_property(_get_CachedContainingGrid)
        def _get_CachedRow(self) -> hints.Incomplete: ...
        CachedRow = hints.normal_property(_get_CachedRow)
        def _get_CachedColumn(self) -> hints.Incomplete: ...
        CachedColumn = hints.normal_property(_get_CachedColumn)
        def _get_CachedRowSpan(self) -> hints.Incomplete: ...
        CachedRowSpan = hints.normal_property(_get_CachedRowSpan)
        def _get_CachedColumnSpan(self) -> hints.Incomplete: ...
        CachedColumnSpan = hints.normal_property(_get_CachedColumnSpan)


IUIAutomationGridItemPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentContainingGrid',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentRow',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentColumn',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentRowSpan',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentColumnSpan',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedContainingGrid',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedRow',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedColumn',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedRowSpan',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedColumnSpan',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
]

UIA_TextPattern2Id = 10024  # Constant c_int
UIA_StylesPatternId = 10025  # Constant c_int
UIA_IsActiveAttributeId = 40036  # Constant c_int
UIA_CustomLandmarkTypeId = 80000  # Constant c_int


class IUIAutomation2(IUIAutomation):
    _case_insensitive_ = True
    _iid_ = GUID('{34723AFF-0C9D-49D0-9896-7AB52DF8CD8A}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_AutoSetFocus(self) -> hints.Incomplete: ...
        def _set_AutoSetFocus(self, AutoSetFocus: hints.Incomplete) -> hints.Hresult: ...
        AutoSetFocus = hints.normal_property(_get_AutoSetFocus, _set_AutoSetFocus)
        def _get_ConnectionTimeout(self) -> hints.Incomplete: ...
        def _set_ConnectionTimeout(self, timeout: hints.Incomplete) -> hints.Hresult: ...
        ConnectionTimeout = hints.normal_property(_get_ConnectionTimeout, _set_ConnectionTimeout)
        def _get_TransactionTimeout(self) -> hints.Incomplete: ...
        def _set_TransactionTimeout(self, timeout: hints.Incomplete) -> hints.Hresult: ...
        TransactionTimeout = hints.normal_property(_get_TransactionTimeout, _set_TransactionTimeout)


class IUIAutomation3(IUIAutomation2):
    _case_insensitive_ = True
    _iid_ = GUID('{73D768DA-9B51-4B89-936E-C209290973E7}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def AddTextEditTextChangedEventHandler(self, element: hints.Incomplete, scope: hints.Incomplete, TextEditChangeType: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveTextEditTextChangedEventHandler(self, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...


class IUIAutomation4(IUIAutomation3):
    _case_insensitive_ = True
    _iid_ = GUID('{1189C02A-05F8-4319-8E21-E817E3DB2860}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def AddChangesEventHandler(self, element: hints.Incomplete, scope: hints.Incomplete, changeTypes: hints.Incomplete, changesCount: hints.Incomplete, pCacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveChangesEventHandler(self, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...


IUIAutomation2._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'AutoSetFocus',
        (['out', 'retval'], POINTER(c_int), 'AutoSetFocus')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'AutoSetFocus',
        (['in'], c_int, 'AutoSetFocus')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ConnectionTimeout',
        (['out', 'retval'], POINTER(c_ulong), 'timeout')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'ConnectionTimeout',
        (['in'], c_ulong, 'timeout')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'TransactionTimeout',
        (['out', 'retval'], POINTER(c_ulong), 'timeout')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'TransactionTimeout',
        (['in'], c_ulong, 'timeout')
    ),
]

IUIAutomation3._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'AddTextEditTextChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], TextEditChangeType, 'TextEditChangeType'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['in'],
            POINTER(IUIAutomationTextEditTextChangedEventHandler),
            'handler',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveTextEditTextChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (
            ['in'],
            POINTER(IUIAutomationTextEditTextChangedEventHandler),
            'handler',
        )
    ),
]

IUIAutomation4._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'AddChangesEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(c_int), 'changeTypes'),
        (['in'], c_int, 'changesCount'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'pCacheRequest'),
        (['in'], POINTER(IUIAutomationChangesEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveChangesEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationChangesEventHandler), 'handler')
    ),
]

UIA_AnimationStyleAttributeId = 40000  # Constant c_int
UIA_LinkAttributeId = 40035  # Constant c_int
StyleId_Quote = 70014  # Constant c_int
UIA_SelectionActiveEndAttributeId = 40037  # Constant c_int
StyleId_Title = 70010  # Constant c_int
UIA_CaretBidiModeAttributeId = 40039  # Constant c_int
StyleId_Normal = 70012  # Constant c_int
UIA_DropTargetPatternId = 10031  # Constant c_int
UIA_LineSpacingAttributeId = 40040  # Constant c_int
UIA_TextEditPatternId = 10032  # Constant c_int
UIA_BeforeParagraphSpacingAttributeId = 40041  # Constant c_int
UIA_CustomNavigationPatternId = 10033  # Constant c_int
UIA_AfterParagraphSpacingAttributeId = 40042  # Constant c_int
UIA_SelectionPattern2Id = 10034  # Constant c_int
UIA_SayAsInterpretAsAttributeId = 40043  # Constant c_int
UIA_ToolTipOpenedEventId = 20000  # Constant c_int
UIA_ButtonControlTypeId = 50000  # Constant c_int
UIA_ToolTipClosedEventId = 20001  # Constant c_int
UIA_CalendarControlTypeId = 50001  # Constant c_int


class IUIAutomationCustomNavigationPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{01EA217A-1766-47ED-A6CC-ACF492854B1F}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Navigate(self, direction: hints.Incomplete) -> 'IUIAutomationElement': ...


IUIAutomationCustomNavigationPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'Navigate',
        (['in'], NavigateDirection, 'direction'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'pRetVal')
    ),
]

UIA_StructureChangedEventId = 20002  # Constant c_int
UIA_CheckBoxControlTypeId = 50002  # Constant c_int
UIA_MenuOpenedEventId = 20003  # Constant c_int
UIA_ComboBoxControlTypeId = 50003  # Constant c_int
UIA_AutomationPropertyChangedEventId = 20004  # Constant c_int
UIA_EditControlTypeId = 50004  # Constant c_int

IRawElementProviderSimple._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ProviderOptions',
        (['out', 'retval'], POINTER(ProviderOptions), 'pRetVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetPatternProvider',
        (['in'], c_int, 'patternId'),
        (['out', 'retval'], POINTER(POINTER(IUnknown)), 'pRetVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetPropertyValue',
        (['in'], c_int, 'propertyId'),
        (['out', 'retval'], POINTER(VARIANT), 'pRetVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'HostRawElementProvider',
        (
            ['out', 'retval'],
            POINTER(POINTER(IRawElementProviderSimple)),
            'pRetVal',
        )
    ),
]

UIA_AutomationFocusChangedEventId = 20005  # Constant c_int
UIA_HyperlinkControlTypeId = 50005  # Constant c_int
UIA_AsyncContentLoadedEventId = 20006  # Constant c_int
UIA_ImageControlTypeId = 50006  # Constant c_int
UIA_MenuClosedEventId = 20007  # Constant c_int
UIA_ListItemControlTypeId = 50007  # Constant c_int
UIA_LayoutInvalidatedEventId = 20008  # Constant c_int
UIA_ListControlTypeId = 50008  # Constant c_int
UIA_Invoke_InvokedEventId = 20009  # Constant c_int
UIA_MenuControlTypeId = 50009  # Constant c_int
UIA_SelectionItem_ElementAddedToSelectionEventId = 20010  # Constant c_int
UIA_MenuBarControlTypeId = 50010  # Constant c_int
UIA_SelectionItem_ElementRemovedFromSelectionEventId = 20011  # Constant c_int
UIA_MenuItemControlTypeId = 50011  # Constant c_int
UIA_SelectionItem_ElementSelectedEventId = 20012  # Constant c_int
UIA_ProgressBarControlTypeId = 50012  # Constant c_int
UIA_Selection_InvalidatedEventId = 20013  # Constant c_int
UIA_RadioButtonControlTypeId = 50013  # Constant c_int
UIA_Text_TextSelectionChangedEventId = 20014  # Constant c_int
UIA_ScrollBarControlTypeId = 50014  # Constant c_int
UIA_Text_TextChangedEventId = 20015  # Constant c_int
UIA_SliderControlTypeId = 50015  # Constant c_int
UIA_Window_WindowOpenedEventId = 20016  # Constant c_int
UIA_SpinnerControlTypeId = 50016  # Constant c_int
UIA_Window_WindowClosedEventId = 20017  # Constant c_int
UIA_StatusBarControlTypeId = 50017  # Constant c_int
UIA_MenuModeStartEventId = 20018  # Constant c_int
UIA_TabControlTypeId = 50018  # Constant c_int
UIA_MenuModeEndEventId = 20019  # Constant c_int
UIA_TabItemControlTypeId = 50019  # Constant c_int
UIA_InputReachedTargetEventId = 20020  # Constant c_int
UIA_TextControlTypeId = 50020  # Constant c_int
UIA_InputReachedOtherElementEventId = 20021  # Constant c_int
UIA_ToolBarControlTypeId = 50021  # Constant c_int
UIA_InputDiscardedEventId = 20022  # Constant c_int
UIA_ToolTipControlTypeId = 50022  # Constant c_int
UIA_SystemAlertEventId = 20023  # Constant c_int
UIA_TreeControlTypeId = 50023  # Constant c_int
UIA_LiveRegionChangedEventId = 20024  # Constant c_int
UIA_TreeItemControlTypeId = 50024  # Constant c_int
UIA_HostedFragmentRootsInvalidatedEventId = 20025  # Constant c_int
UIA_CustomControlTypeId = 50025  # Constant c_int
UIA_Drag_DragStartEventId = 20026  # Constant c_int
UIA_GroupControlTypeId = 50026  # Constant c_int
UIA_Drag_DragCancelEventId = 20027  # Constant c_int
UIA_ThumbControlTypeId = 50027  # Constant c_int
UIA_Drag_DragCompleteEventId = 20028  # Constant c_int
UIA_DataGridControlTypeId = 50028  # Constant c_int


class IUIAutomation5(IUIAutomation4):
    _case_insensitive_ = True
    _iid_ = GUID('{25F700C8-D816-4057-A9DC-3CBDEE77E256}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def AddNotificationEventHandler(self, element: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveNotificationEventHandler(self, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...


IUIAutomation5._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'AddNotificationEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationNotificationEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveNotificationEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationNotificationEventHandler), 'handler')
    ),
]

UIA_DropTarget_DragEnterEventId = 20029  # Constant c_int
UIA_DataItemControlTypeId = 50029  # Constant c_int
UIA_DropTarget_DragLeaveEventId = 20030  # Constant c_int
UIA_DocumentControlTypeId = 50030  # Constant c_int


class IUIAutomationActiveTextPositionChangedEventHandler(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{F97933B0-8DAE-4496-8997-5BA015FE0D82}')
    _idlflags_ = ['oleautomation']

    if TYPE_CHECKING:  # commembers
        def HandleActiveTextPositionChangedEvent(self, sender: hints.Incomplete, range: hints.Incomplete) -> hints.Hresult: ...


IUIAutomationActiveTextPositionChangedEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleActiveTextPositionChangedEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        (['in'], POINTER(IUIAutomationTextRange), 'range')
    ),
]

UIA_DropTarget_DroppedEventId = 20031  # Constant c_int
UIA_SplitButtonControlTypeId = 50031  # Constant c_int


class IUIAutomationWindowPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{0FAEF453-9208-43EF-BBB2-3B485177864F}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Close(self) -> hints.Hresult: ...
        def WaitForInputIdle(self, milliseconds: hints.Incomplete) -> hints.Incomplete: ...
        def SetWindowVisualState(self, state: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentCanMaximize(self) -> hints.Incomplete: ...
        CurrentCanMaximize = hints.normal_property(_get_CurrentCanMaximize)
        def _get_CurrentCanMinimize(self) -> hints.Incomplete: ...
        CurrentCanMinimize = hints.normal_property(_get_CurrentCanMinimize)
        def _get_CurrentIsModal(self) -> hints.Incomplete: ...
        CurrentIsModal = hints.normal_property(_get_CurrentIsModal)
        def _get_CurrentIsTopmost(self) -> hints.Incomplete: ...
        CurrentIsTopmost = hints.normal_property(_get_CurrentIsTopmost)
        def _get_CurrentWindowVisualState(self) -> hints.Incomplete: ...
        CurrentWindowVisualState = hints.normal_property(_get_CurrentWindowVisualState)
        def _get_CurrentWindowInteractionState(self) -> hints.Incomplete: ...
        CurrentWindowInteractionState = hints.normal_property(_get_CurrentWindowInteractionState)
        def _get_CachedCanMaximize(self) -> hints.Incomplete: ...
        CachedCanMaximize = hints.normal_property(_get_CachedCanMaximize)
        def _get_CachedCanMinimize(self) -> hints.Incomplete: ...
        CachedCanMinimize = hints.normal_property(_get_CachedCanMinimize)
        def _get_CachedIsModal(self) -> hints.Incomplete: ...
        CachedIsModal = hints.normal_property(_get_CachedIsModal)
        def _get_CachedIsTopmost(self) -> hints.Incomplete: ...
        CachedIsTopmost = hints.normal_property(_get_CachedIsTopmost)
        def _get_CachedWindowVisualState(self) -> hints.Incomplete: ...
        CachedWindowVisualState = hints.normal_property(_get_CachedWindowVisualState)
        def _get_CachedWindowInteractionState(self) -> hints.Incomplete: ...
        CachedWindowInteractionState = hints.normal_property(_get_CachedWindowInteractionState)


IUIAutomationWindowPattern._methods_ = [
    COMMETHOD([], HRESULT, 'Close'),
    COMMETHOD(
        [],
        HRESULT,
        'WaitForInputIdle',
        (['in'], c_int, 'milliseconds'),
        (['out', 'retval'], POINTER(c_int), 'success')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetWindowVisualState',
        (['in'], WindowVisualState, 'state')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanMaximize',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanMinimize',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsModal',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentIsTopmost',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentWindowVisualState',
        (['out', 'retval'], POINTER(WindowVisualState), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentWindowInteractionState',
        (['out', 'retval'], POINTER(WindowInteractionState), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanMaximize',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanMinimize',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsModal',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedIsTopmost',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedWindowVisualState',
        (['out', 'retval'], POINTER(WindowVisualState), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedWindowInteractionState',
        (['out', 'retval'], POINTER(WindowInteractionState), 'retVal')
    ),
]

UIA_TextEdit_TextChangedEventId = 20032  # Constant c_int
UIA_WindowControlTypeId = 50032  # Constant c_int
UIA_TextEdit_ConversionTargetChangedEventId = 20033  # Constant c_int
UIA_PaneControlTypeId = 50033  # Constant c_int
UIA_ChangesEventId = 20034  # Constant c_int
UIA_HeaderControlTypeId = 50034  # Constant c_int
UIA_NotificationEventId = 20035  # Constant c_int
UIA_HeaderItemControlTypeId = 50035  # Constant c_int
UIA_ActiveTextPositionChangedEventId = 20036  # Constant c_int
UIA_TableControlTypeId = 50036  # Constant c_int
UIA_RuntimeIdPropertyId = 30000  # Constant c_int
UIA_TitleBarControlTypeId = 50037  # Constant c_int
UIA_BoundingRectanglePropertyId = 30001  # Constant c_int
UIA_SeparatorControlTypeId = 50038  # Constant c_int
UIA_ProcessIdPropertyId = 30002  # Constant c_int
UIA_SemanticZoomControlTypeId = 50039  # Constant c_int
UIA_ControlTypePropertyId = 30003  # Constant c_int
UIA_AppBarControlTypeId = 50040  # Constant c_int
UIA_LocalizedControlTypePropertyId = 30004  # Constant c_int
AnnotationType_Unknown = 60000  # Constant c_int
UIA_NamePropertyId = 30005  # Constant c_int
AnnotationType_SpellingError = 60001  # Constant c_int


class IUIAutomationLegacyIAccessiblePattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{828055AD-355B-4435-86D5-3B51C14A9B1B}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Select(self, flagsSelect: hints.Incomplete) -> hints.Hresult: ...
        def DoDefaultAction(self) -> hints.Hresult: ...
        def SetValue(self, szValue: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentChildId(self) -> hints.Incomplete: ...
        CurrentChildId = hints.normal_property(_get_CurrentChildId)
        def _get_CurrentName(self) -> hints.Incomplete: ...
        CurrentName = hints.normal_property(_get_CurrentName)
        def _get_CurrentValue(self) -> hints.Incomplete: ...
        CurrentValue = hints.normal_property(_get_CurrentValue)
        def _get_CurrentDescription(self) -> hints.Incomplete: ...
        CurrentDescription = hints.normal_property(_get_CurrentDescription)
        def _get_CurrentRole(self) -> hints.Incomplete: ...
        CurrentRole = hints.normal_property(_get_CurrentRole)
        def _get_CurrentState(self) -> hints.Incomplete: ...
        CurrentState = hints.normal_property(_get_CurrentState)
        def _get_CurrentHelp(self) -> hints.Incomplete: ...
        CurrentHelp = hints.normal_property(_get_CurrentHelp)
        def _get_CurrentKeyboardShortcut(self) -> hints.Incomplete: ...
        CurrentKeyboardShortcut = hints.normal_property(_get_CurrentKeyboardShortcut)
        def GetCurrentSelection(self) -> 'IUIAutomationElementArray': ...
        def _get_CurrentDefaultAction(self) -> hints.Incomplete: ...
        CurrentDefaultAction = hints.normal_property(_get_CurrentDefaultAction)
        def _get_CachedChildId(self) -> hints.Incomplete: ...
        CachedChildId = hints.normal_property(_get_CachedChildId)
        def _get_CachedName(self) -> hints.Incomplete: ...
        CachedName = hints.normal_property(_get_CachedName)
        def _get_CachedValue(self) -> hints.Incomplete: ...
        CachedValue = hints.normal_property(_get_CachedValue)
        def _get_CachedDescription(self) -> hints.Incomplete: ...
        CachedDescription = hints.normal_property(_get_CachedDescription)
        def _get_CachedRole(self) -> hints.Incomplete: ...
        CachedRole = hints.normal_property(_get_CachedRole)
        def _get_CachedState(self) -> hints.Incomplete: ...
        CachedState = hints.normal_property(_get_CachedState)
        def _get_CachedHelp(self) -> hints.Incomplete: ...
        CachedHelp = hints.normal_property(_get_CachedHelp)
        def _get_CachedKeyboardShortcut(self) -> hints.Incomplete: ...
        CachedKeyboardShortcut = hints.normal_property(_get_CachedKeyboardShortcut)
        def GetCachedSelection(self) -> 'IUIAutomationElementArray': ...
        def _get_CachedDefaultAction(self) -> hints.Incomplete: ...
        CachedDefaultAction = hints.normal_property(_get_CachedDefaultAction)
        def GetIAccessible(self) -> 'IAccessible': ...


IUIAutomationLegacyIAccessiblePattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'Select',
        ([], c_int, 'flagsSelect')
    ),
    COMMETHOD([], HRESULT, 'DoDefaultAction'),
    COMMETHOD(
        [],
        HRESULT,
        'SetValue',
        ([], WSTRING, 'szValue')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentChildId',
        (['out', 'retval'], POINTER(c_int), 'pRetVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentName',
        (['out', 'retval'], POINTER(BSTR), 'pszName')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentValue',
        (['out', 'retval'], POINTER(BSTR), 'pszValue')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDescription',
        (['out', 'retval'], POINTER(BSTR), 'pszDescription')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentRole',
        (['out', 'retval'], POINTER(c_ulong), 'pdwRole')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentState',
        (['out', 'retval'], POINTER(c_ulong), 'pdwState')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentHelp',
        (['out', 'retval'], POINTER(BSTR), 'pszHelp')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentKeyboardShortcut',
        (['out', 'retval'], POINTER(BSTR), 'pszKeyboardShortcut')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentSelection',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'pvarSelectedChildren',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDefaultAction',
        (['out', 'retval'], POINTER(BSTR), 'pszDefaultAction')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedChildId',
        (['out', 'retval'], POINTER(c_int), 'pRetVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedName',
        (['out', 'retval'], POINTER(BSTR), 'pszName')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedValue',
        (['out', 'retval'], POINTER(BSTR), 'pszValue')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDescription',
        (['out', 'retval'], POINTER(BSTR), 'pszDescription')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedRole',
        (['out', 'retval'], POINTER(c_ulong), 'pdwRole')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedState',
        (['out', 'retval'], POINTER(c_ulong), 'pdwState')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedHelp',
        (['out', 'retval'], POINTER(BSTR), 'pszHelp')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedKeyboardShortcut',
        (['out', 'retval'], POINTER(BSTR), 'pszKeyboardShortcut')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedSelection',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'pvarSelectedChildren',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDefaultAction',
        (['out', 'retval'], POINTER(BSTR), 'pszDefaultAction')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetIAccessible',
        (['out', 'retval'], POINTER(POINTER(IAccessible)), 'ppAccessible')
    ),
]

UIA_AcceleratorKeyPropertyId = 30006  # Constant c_int
AnnotationType_GrammarError = 60002  # Constant c_int
UIA_AccessKeyPropertyId = 30007  # Constant c_int
AnnotationType_Comment = 60003  # Constant c_int
UIA_HasKeyboardFocusPropertyId = 30008  # Constant c_int
AnnotationType_FormulaError = 60004  # Constant c_int
UIA_IsKeyboardFocusablePropertyId = 30009  # Constant c_int
AnnotationType_TrackChanges = 60005  # Constant c_int
UIA_IsEnabledPropertyId = 30010  # Constant c_int
AnnotationType_Header = 60006  # Constant c_int
UIA_AutomationIdPropertyId = 30011  # Constant c_int
AnnotationType_Footer = 60007  # Constant c_int
UIA_ClassNamePropertyId = 30012  # Constant c_int
AnnotationType_Highlighted = 60008  # Constant c_int
UIA_HelpTextPropertyId = 30013  # Constant c_int
AnnotationType_Endnote = 60009  # Constant c_int
UIA_ClickablePointPropertyId = 30014  # Constant c_int
AnnotationType_Footnote = 60010  # Constant c_int
UIA_CulturePropertyId = 30015  # Constant c_int
AnnotationType_InsertionChange = 60011  # Constant c_int
UIA_IsControlElementPropertyId = 30016  # Constant c_int
AnnotationType_DeletionChange = 60012  # Constant c_int
UIA_IsContentElementPropertyId = 30017  # Constant c_int
AnnotationType_MoveChange = 60013  # Constant c_int
UIA_LabeledByPropertyId = 30018  # Constant c_int
AnnotationType_FormatChange = 60014  # Constant c_int
UIA_IsPasswordPropertyId = 30019  # Constant c_int
AnnotationType_UnsyncedChange = 60015  # Constant c_int
UIA_NativeWindowHandlePropertyId = 30020  # Constant c_int
AnnotationType_EditingLockedChange = 60016  # Constant c_int


class IUIAutomation6(IUIAutomation5):
    _case_insensitive_ = True
    _iid_ = GUID('{AAE072DA-29E3-413D-87A7-192DBF81ED10}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def CreateEventHandlerGroup(self) -> 'IUIAutomationEventHandlerGroup': ...
        def AddEventHandlerGroup(self, element: hints.Incomplete, handlerGroup: hints.Incomplete) -> hints.Hresult: ...
        def RemoveEventHandlerGroup(self, element: hints.Incomplete, handlerGroup: hints.Incomplete) -> hints.Hresult: ...
        def _get_ConnectionRecoveryBehavior(self) -> hints.Incomplete: ...
        def _set_ConnectionRecoveryBehavior(self, ConnectionRecoveryBehaviorOptions: hints.Incomplete) -> hints.Hresult: ...
        ConnectionRecoveryBehavior = hints.normal_property(_get_ConnectionRecoveryBehavior, _set_ConnectionRecoveryBehavior)
        def _get_CoalesceEvents(self) -> hints.Incomplete: ...
        def _set_CoalesceEvents(self, CoalesceEventsOptions: hints.Incomplete) -> hints.Hresult: ...
        CoalesceEvents = hints.normal_property(_get_CoalesceEvents, _set_CoalesceEvents)
        def AddActiveTextPositionChangedEventHandler(self, element: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def RemoveActiveTextPositionChangedEventHandler(self, element: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...


class IUIAutomationEventHandlerGroup(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{C9EE12F2-C13B-4408-997C-639914377F4E}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def AddActiveTextPositionChangedEventHandler(self, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddAutomationEventHandler(self, eventId: hints.Incomplete, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddChangesEventHandler(self, scope: hints.Incomplete, changeTypes: hints.Incomplete, changesCount: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddNotificationEventHandler(self, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddPropertyChangedEventHandler(self, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete, propertyArray: hints.Incomplete, propertyCount: hints.Incomplete) -> hints.Hresult: ...
        def AddStructureChangedEventHandler(self, scope: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...
        def AddTextEditTextChangedEventHandler(self, scope: hints.Incomplete, TextEditChangeType: hints.Incomplete, cacheRequest: hints.Incomplete, handler: hints.Incomplete) -> hints.Hresult: ...


IUIAutomation6._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'CreateEventHandlerGroup',
        (
            ['out'],
            POINTER(POINTER(IUIAutomationEventHandlerGroup)),
            'handlerGroup',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddEventHandlerGroup',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationEventHandlerGroup), 'handlerGroup')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveEventHandlerGroup',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], POINTER(IUIAutomationEventHandlerGroup), 'handlerGroup')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'ConnectionRecoveryBehavior',
        (
            ['out', 'retval'],
            POINTER(ConnectionRecoveryBehaviorOptions),
            'ConnectionRecoveryBehaviorOptions',
        )
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'ConnectionRecoveryBehavior',
        (
            ['in'],
            ConnectionRecoveryBehaviorOptions,
            'ConnectionRecoveryBehaviorOptions',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CoalesceEvents',
        (
            ['out', 'retval'],
            POINTER(CoalesceEventsOptions),
            'CoalesceEventsOptions',
        )
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'CoalesceEvents',
        (['in'], CoalesceEventsOptions, 'CoalesceEventsOptions')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddActiveTextPositionChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['in'],
            POINTER(IUIAutomationActiveTextPositionChangedEventHandler),
            'handler',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveActiveTextPositionChangedEventHandler',
        (['in'], POINTER(IUIAutomationElement), 'element'),
        (
            ['in'],
            POINTER(IUIAutomationActiveTextPositionChangedEventHandler),
            'handler',
        )
    ),
]

UIA_ItemTypePropertyId = 30021  # Constant c_int
AnnotationType_ExternalChange = 60017  # Constant c_int
UIA_IsOffscreenPropertyId = 30022  # Constant c_int
AnnotationType_ConflictingChange = 60018  # Constant c_int
UIA_OrientationPropertyId = 30023  # Constant c_int
AnnotationType_Author = 60019  # Constant c_int
UIA_FrameworkIdPropertyId = 30024  # Constant c_int
AnnotationType_AdvancedProofingIssue = 60020  # Constant c_int
UIA_IsRequiredForFormPropertyId = 30025  # Constant c_int
AnnotationType_DataValidationError = 60021  # Constant c_int
UIA_ItemStatusPropertyId = 30026  # Constant c_int
AnnotationType_CircularReferenceError = 60022  # Constant c_int
UIA_IsDockPatternAvailablePropertyId = 30027  # Constant c_int
AnnotationType_Mathematics = 60023  # Constant c_int
UIA_IsExpandCollapsePatternAvailablePropertyId = 30028  # Constant c_int
AnnotationType_Sensitive = 60024  # Constant c_int
UIA_IsGridItemPatternAvailablePropertyId = 30029  # Constant c_int
StyleId_Custom = 70000  # Constant c_int
UIA_IsGridPatternAvailablePropertyId = 30030  # Constant c_int
UIA_IsInvokePatternAvailablePropertyId = 30031  # Constant c_int
UIA_IsMultipleViewPatternAvailablePropertyId = 30032  # Constant c_int
StyleId_Heading1 = 70001  # Constant c_int
UIA_IsRangeValuePatternAvailablePropertyId = 30033  # Constant c_int
StyleId_Heading2 = 70002  # Constant c_int
UIA_IsScrollPatternAvailablePropertyId = 30034  # Constant c_int
StyleId_Heading3 = 70003  # Constant c_int
UIA_IsScrollItemPatternAvailablePropertyId = 30035  # Constant c_int
StyleId_Heading4 = 70004  # Constant c_int
UIA_IsSelectionItemPatternAvailablePropertyId = 30036  # Constant c_int
StyleId_Heading5 = 70005  # Constant c_int
UIA_IsSelectionPatternAvailablePropertyId = 30037  # Constant c_int
StyleId_Heading6 = 70006  # Constant c_int
UIA_IsTablePatternAvailablePropertyId = 30038  # Constant c_int
StyleId_Heading7 = 70007  # Constant c_int
UIA_IsTableItemPatternAvailablePropertyId = 30039  # Constant c_int
StyleId_Heading8 = 70008  # Constant c_int
UIA_IsTextPatternAvailablePropertyId = 30040  # Constant c_int
StyleId_Heading9 = 70009  # Constant c_int
UIA_IsTogglePatternAvailablePropertyId = 30041  # Constant c_int
UIA_IsTransformPatternAvailablePropertyId = 30042  # Constant c_int
HeadingLevel1 = 80051  # Constant c_int


class IUIAutomationTextRange2(IUIAutomationTextRange):
    _case_insensitive_ = True
    _iid_ = GUID('{BB9B40E0-5E04-46BD-9BE0-4B601B9AFAD4}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def ShowContextMenu(self) -> hints.Hresult: ...


IUIAutomationTextRange2._methods_ = [
    COMMETHOD([], HRESULT, 'ShowContextMenu'),
]

UIA_IsValuePatternAvailablePropertyId = 30043  # Constant c_int
StyleId_Subtitle = 70011  # Constant c_int
UIA_IsWindowPatternAvailablePropertyId = 30044  # Constant c_int
UIA_ValueValuePropertyId = 30045  # Constant c_int
UIA_ValueIsReadOnlyPropertyId = 30046  # Constant c_int
StyleId_Emphasis = 70013  # Constant c_int
UIA_RangeValueValuePropertyId = 30047  # Constant c_int
UIA_RangeValueIsReadOnlyPropertyId = 30048  # Constant c_int
UIA_RangeValueMinimumPropertyId = 30049  # Constant c_int
StyleId_BulletedList = 70015  # Constant c_int


class IUIAutomationTextRange3(IUIAutomationTextRange2):
    _case_insensitive_ = True
    _iid_ = GUID('{6A315D69-5512-4C2E-85F0-53FCE6DD4BC2}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetEnclosingElementBuildCache(self, cacheRequest: hints.Incomplete) -> 'IUIAutomationElement': ...
        def GetChildrenBuildCache(self, cacheRequest: hints.Incomplete) -> 'IUIAutomationElementArray': ...
        def GetAttributeValues(self, attributeIds: hints.Incomplete, attributeIdCount: hints.Incomplete) -> hints.Incomplete: ...


IUIAutomationTextRange3._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetEnclosingElementBuildCache',
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElement)),
            'enclosingElement',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetChildrenBuildCache',
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'children',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetAttributeValues',
        (['in'], POINTER(c_int), 'attributeIds'),
        (['in'], c_int, 'attributeIdCount'),
        (['out', 'retval'], POINTER(_midlSAFEARRAY(VARIANT)), 'attributeValues')
    ),
]

UIA_RangeValueMaximumPropertyId = 30050  # Constant c_int
StyleId_NumberedList = 70016  # Constant c_int
UIA_RangeValueLargeChangePropertyId = 30051  # Constant c_int
UIA_FormLandmarkTypeId = 80001  # Constant c_int
UIA_RangeValueSmallChangePropertyId = 30052  # Constant c_int
UIA_MainLandmarkTypeId = 80002  # Constant c_int
UIA_ScrollHorizontalScrollPercentPropertyId = 30053  # Constant c_int
UIA_NavigationLandmarkTypeId = 80003  # Constant c_int
UIA_ScrollHorizontalViewSizePropertyId = 30054  # Constant c_int
UIA_SearchLandmarkTypeId = 80004  # Constant c_int
UIA_ScrollVerticalScrollPercentPropertyId = 30055  # Constant c_int
HeadingLevel_None = 80050  # Constant c_int
UIA_ScrollVerticalViewSizePropertyId = 30056  # Constant c_int
UIA_ScrollHorizontallyScrollablePropertyId = 30057  # Constant c_int
HeadingLevel2 = 80052  # Constant c_int


class ExtendedProperty(Structure):
    pass


ExtendedProperty._fields_ = [
    ('PropertyName', BSTR),
    ('PropertyValue', BSTR),
]

assert sizeof(ExtendedProperty) == 16, sizeof(ExtendedProperty)
assert alignment(ExtendedProperty) == 8, alignment(ExtendedProperty)
UIA_ScrollVerticallyScrollablePropertyId = 30058  # Constant c_int
UIA_SelectionSelectionPropertyId = 30059  # Constant c_int
HeadingLevel3 = 80053  # Constant c_int


class IUIAutomationTextRangeArray(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{CE4AE76A-E717-4C98-81EA-47371D028EB6}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_Length(self) -> hints.Incomplete: ...
        Length = hints.normal_property(_get_Length)
        def GetElement(self, index: hints.Incomplete) -> 'IUIAutomationTextRange': ...


IUIAutomationTextRangeArray._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Length',
        (['out', 'retval'], POINTER(c_int), 'Length')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetElement',
        (['in'], c_int, 'index'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'element')
    ),
]

UIA_SelectionCanSelectMultiplePropertyId = 30060  # Constant c_int
UIA_SelectionIsSelectionRequiredPropertyId = 30061  # Constant c_int
HeadingLevel4 = 80054  # Constant c_int
UIA_GridRowCountPropertyId = 30062  # Constant c_int
UIA_GridColumnCountPropertyId = 30063  # Constant c_int
HeadingLevel5 = 80055  # Constant c_int
UIA_GridItemRowPropertyId = 30064  # Constant c_int
UIA_GridItemColumnPropertyId = 30065  # Constant c_int
HeadingLevel6 = 80056  # Constant c_int
UIA_GridItemRowSpanPropertyId = 30066  # Constant c_int
UIA_GridItemColumnSpanPropertyId = 30067  # Constant c_int
HeadingLevel7 = 80057  # Constant c_int
UIA_GridItemContainingGridPropertyId = 30068  # Constant c_int
UIA_DockDockPositionPropertyId = 30069  # Constant c_int
HeadingLevel8 = 80058  # Constant c_int
UIA_ExpandCollapseExpandCollapseStatePropertyId = 30070  # Constant c_int
UIA_MultipleViewCurrentViewPropertyId = 30071  # Constant c_int
HeadingLevel9 = 80059  # Constant c_int
UIA_MultipleViewSupportedViewsPropertyId = 30072  # Constant c_int
UIA_WindowCanMaximizePropertyId = 30073  # Constant c_int
UIA_WindowCanMinimizePropertyId = 30074  # Constant c_int
UIA_WindowWindowVisualStatePropertyId = 30075  # Constant c_int
UIA_SummaryChangeId = 90000  # Constant c_int
UIA_WindowWindowInteractionStatePropertyId = 30076  # Constant c_int
UIA_SayAsInterpretAsMetadataId = 100000  # Constant c_int


class CUIAutomation(CoClass):
    """The Central Class for UIAutomation"""
    _reg_clsid_ = GUID('{FF48DBA4-60EF-4201-AA87-54103EEF594E}')
    _idlflags_ = []
    _typelib_path_ = typelib_path
    _reg_typelib_ = ('{944DE083-8FB8-45CF-BCB7-C477ACB2F897}', 1, 0)


CUIAutomation._com_interfaces_ = [IUIAutomation]

UIA_WindowIsModalPropertyId = 30077  # Constant c_int
UIA_WindowIsTopmostPropertyId = 30078  # Constant c_int
UIA_SelectionItemIsSelectedPropertyId = 30079  # Constant c_int
UIA_SelectionItemSelectionContainerPropertyId = 30080  # Constant c_int
UIA_TableRowHeadersPropertyId = 30081  # Constant c_int
UIA_TableColumnHeadersPropertyId = 30082  # Constant c_int

IUIAutomationStructureChangedEventHandler._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'HandleStructureChangedEvent',
        (['in'], POINTER(IUIAutomationElement), 'sender'),
        (['in'], StructureChangeType, 'changeType'),
        (['in'], _midlSAFEARRAY(c_int), 'runtimeId')
    ),
]

UIA_TableRowOrColumnMajorPropertyId = 30083  # Constant c_int
UIA_TableItemRowHeaderItemsPropertyId = 30084  # Constant c_int
UIA_TableItemColumnHeaderItemsPropertyId = 30085  # Constant c_int
UIA_ToggleToggleStatePropertyId = 30086  # Constant c_int
UIA_TransformCanMovePropertyId = 30087  # Constant c_int
UIA_TransformCanResizePropertyId = 30088  # Constant c_int
UIA_TransformCanRotatePropertyId = 30089  # Constant c_int
UIA_IsLegacyIAccessiblePatternAvailablePropertyId = 30090  # Constant c_int
UIA_LegacyIAccessibleChildIdPropertyId = 30091  # Constant c_int
UIA_LegacyIAccessibleNamePropertyId = 30092  # Constant c_int
UIA_LegacyIAccessibleValuePropertyId = 30093  # Constant c_int
UIA_LegacyIAccessibleDescriptionPropertyId = 30094  # Constant c_int
UIA_LegacyIAccessibleRolePropertyId = 30095  # Constant c_int
UIA_LegacyIAccessibleStatePropertyId = 30096  # Constant c_int


class CUIAutomation8(CoClass):
    """The Central Class for UIAutomation8"""
    _reg_clsid_ = GUID('{E22AD333-B25F-460C-83D0-0581107395C9}')
    _idlflags_ = []
    _typelib_path_ = typelib_path
    _reg_typelib_ = ('{944DE083-8FB8-45CF-BCB7-C477ACB2F897}', 1, 0)


CUIAutomation8._com_interfaces_ = [IUIAutomation2, IUIAutomation3, IUIAutomation4, IUIAutomation5, IUIAutomation6]

UIA_LegacyIAccessibleHelpPropertyId = 30097  # Constant c_int
UIA_LegacyIAccessibleKeyboardShortcutPropertyId = 30098  # Constant c_int
UIA_LegacyIAccessibleSelectionPropertyId = 30099  # Constant c_int
UIA_LegacyIAccessibleDefaultActionPropertyId = 30100  # Constant c_int
UIA_AriaRolePropertyId = 30101  # Constant c_int
UIA_AriaPropertiesPropertyId = 30102  # Constant c_int
UIA_IsDataValidForFormPropertyId = 30103  # Constant c_int
UIA_ControllerForPropertyId = 30104  # Constant c_int
UIA_DescribedByPropertyId = 30105  # Constant c_int
UIA_FlowsToPropertyId = 30106  # Constant c_int
UIA_ProviderDescriptionPropertyId = 30107  # Constant c_int
UIA_IsItemContainerPatternAvailablePropertyId = 30108  # Constant c_int
UIA_IsVirtualizedItemPatternAvailablePropertyId = 30109  # Constant c_int
UIA_IsSynchronizedInputPatternAvailablePropertyId = 30110  # Constant c_int
UIA_OptimizeForVisualContentPropertyId = 30111  # Constant c_int


class IUIAutomationTextPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{32EBA289-3583-42C9-9C59-3B6D9A1E9B6A}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def RangeFromPoint(self, pt: hints.Incomplete) -> 'IUIAutomationTextRange': ...
        def RangeFromChild(self, child: hints.Incomplete) -> 'IUIAutomationTextRange': ...
        def GetSelection(self) -> 'IUIAutomationTextRangeArray': ...
        def GetVisibleRanges(self) -> 'IUIAutomationTextRangeArray': ...
        def _get_DocumentRange(self) -> 'IUIAutomationTextRange': ...
        DocumentRange = hints.normal_property(_get_DocumentRange)
        def _get_SupportedTextSelection(self) -> hints.Incomplete: ...
        SupportedTextSelection = hints.normal_property(_get_SupportedTextSelection)


IUIAutomationTextPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'RangeFromPoint',
        (['in'], tagPOINT, 'pt'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RangeFromChild',
        (['in'], POINTER(IUIAutomationElement), 'child'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetSelection',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationTextRangeArray)),
            'ranges',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetVisibleRanges',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationTextRangeArray)),
            'ranges',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'DocumentRange',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'SupportedTextSelection',
        (
            ['out', 'retval'],
            POINTER(SupportedTextSelection),
            'SupportedTextSelection',
        )
    ),
]

UIA_IsObjectModelPatternAvailablePropertyId = 30112  # Constant c_int
UIA_AnnotationAnnotationTypeIdPropertyId = 30113  # Constant c_int
UIA_AnnotationAnnotationTypeNamePropertyId = 30114  # Constant c_int
UIA_AnnotationAuthorPropertyId = 30115  # Constant c_int


class IUIAutomationSpreadsheetPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{7517A7C8-FAAE-4DE9-9F08-29B91E8595C1}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetItemByName(self, name: hints.Incomplete) -> 'IUIAutomationElement': ...


IUIAutomationSpreadsheetPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetItemByName',
        (['in'], BSTR, 'name'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
]

UIA_AnnotationDateTimePropertyId = 30116  # Constant c_int
UIA_AnnotationTargetPropertyId = 30117  # Constant c_int

IUIAutomationProxyFactoryMapping._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'count',
        (['out', 'retval'], POINTER(c_uint), 'count')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetTable',
        (
            ['out', 'retval'],
            POINTER(_midlSAFEARRAY(POINTER(IUIAutomationProxyFactoryEntry))),
            'table',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetEntry',
        (['in'], c_uint, 'index'),
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationProxyFactoryEntry)),
            'entry',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'SetTable',
        (
            ['in'],
            _midlSAFEARRAY(POINTER(IUIAutomationProxyFactoryEntry)),
            'factoryList',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'InsertEntries',
        (['in'], c_uint, 'before'),
        (
            ['in'],
            _midlSAFEARRAY(POINTER(IUIAutomationProxyFactoryEntry)),
            'factoryList',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'InsertEntry',
        (['in'], c_uint, 'before'),
        (['in'], POINTER(IUIAutomationProxyFactoryEntry), 'factory')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'RemoveEntry',
        (['in'], c_uint, 'index')
    ),
    COMMETHOD([], HRESULT, 'ClearTable'),
    COMMETHOD([], HRESULT, 'RestoreDefaultTable'),
]

UIA_IsAnnotationPatternAvailablePropertyId = 30118  # Constant c_int
UIA_IsTextPattern2AvailablePropertyId = 30119  # Constant c_int
UIA_StylesStyleIdPropertyId = 30120  # Constant c_int
UIA_StylesStyleNamePropertyId = 30121  # Constant c_int
UIA_StylesFillColorPropertyId = 30122  # Constant c_int


class IUIAutomationSpreadsheetItemPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{7D4FB86C-8D34-40E1-8E83-62C15204E335}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentFormula(self) -> hints.Incomplete: ...
        CurrentFormula = hints.normal_property(_get_CurrentFormula)
        def GetCurrentAnnotationObjects(self) -> 'IUIAutomationElementArray': ...
        def GetCurrentAnnotationTypes(self) -> hints.Incomplete: ...
        def _get_CachedFormula(self) -> hints.Incomplete: ...
        CachedFormula = hints.normal_property(_get_CachedFormula)
        def GetCachedAnnotationObjects(self) -> 'IUIAutomationElementArray': ...
        def GetCachedAnnotationTypes(self) -> hints.Incomplete: ...


IUIAutomationSpreadsheetItemPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFormula',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentAnnotationObjects',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentAnnotationTypes',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFormula',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedAnnotationObjects',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationElementArray)),
            'retVal',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedAnnotationTypes',
        (['out', 'retval'], POINTER(_midlSAFEARRAY(c_int)), 'retVal')
    ),
]

UIA_StylesFillPatternStylePropertyId = 30123  # Constant c_int
UIA_StylesShapePropertyId = 30124  # Constant c_int
UIA_StylesFillPatternColorPropertyId = 30125  # Constant c_int


class IUIAutomationVirtualizedItemPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{6BA3D7A6-04CF-4F11-8793-A8D1CDE9969F}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Realize(self) -> hints.Hresult: ...


IUIAutomationVirtualizedItemPattern._methods_ = [
    COMMETHOD([], HRESULT, 'Realize'),
]

UIA_StylesExtendedPropertiesPropertyId = 30126  # Constant c_int
UIA_IsStylesPatternAvailablePropertyId = 30127  # Constant c_int
UIA_IsSpreadsheetPatternAvailablePropertyId = 30128  # Constant c_int
UIA_SpreadsheetItemFormulaPropertyId = 30129  # Constant c_int
UIA_SpreadsheetItemAnnotationObjectsPropertyId = 30130  # Constant c_int
UIA_SpreadsheetItemAnnotationTypesPropertyId = 30131  # Constant c_int
UIA_IsSpreadsheetItemPatternAvailablePropertyId = 30132  # Constant c_int
UIA_Transform2CanZoomPropertyId = 30133  # Constant c_int
UIA_IsTransformPattern2AvailablePropertyId = 30134  # Constant c_int
UIA_LiveSettingPropertyId = 30135  # Constant c_int
UIA_IsTextChildPatternAvailablePropertyId = 30136  # Constant c_int
UIA_IsDragPatternAvailablePropertyId = 30137  # Constant c_int
UIA_DragIsGrabbedPropertyId = 30138  # Constant c_int
UIA_DragDropEffectPropertyId = 30139  # Constant c_int
UIA_DragDropEffectsPropertyId = 30140  # Constant c_int
UIA_IsDropTargetPatternAvailablePropertyId = 30141  # Constant c_int
UIA_DropTargetDropTargetEffectPropertyId = 30142  # Constant c_int
UIA_DropTargetDropTargetEffectsPropertyId = 30143  # Constant c_int
UIA_DragGrabbedItemsPropertyId = 30144  # Constant c_int
UIA_Transform2ZoomLevelPropertyId = 30145  # Constant c_int
UIA_Transform2ZoomMinimumPropertyId = 30146  # Constant c_int
UIA_Transform2ZoomMaximumPropertyId = 30147  # Constant c_int
UIA_FlowsFromPropertyId = 30148  # Constant c_int
UIA_IsTextEditPatternAvailablePropertyId = 30149  # Constant c_int
UIA_IsPeripheralPropertyId = 30150  # Constant c_int
UIA_IsCustomNavigationPatternAvailablePropertyId = 30151  # Constant c_int
UIA_PositionInSetPropertyId = 30152  # Constant c_int
UIA_SizeOfSetPropertyId = 30153  # Constant c_int
UIA_LevelPropertyId = 30154  # Constant c_int
UIA_AnnotationTypesPropertyId = 30155  # Constant c_int
UIA_AnnotationObjectsPropertyId = 30156  # Constant c_int
UIA_LandmarkTypePropertyId = 30157  # Constant c_int
UIA_LocalizedLandmarkTypePropertyId = 30158  # Constant c_int
UIA_FullDescriptionPropertyId = 30159  # Constant c_int
UIA_FillColorPropertyId = 30160  # Constant c_int
UIA_OutlineColorPropertyId = 30161  # Constant c_int
UIA_FillTypePropertyId = 30162  # Constant c_int
UIA_VisualEffectsPropertyId = 30163  # Constant c_int


class IUIAutomationAnnotationPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{9A175B21-339E-41B1-8E8B-623F6B681098}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentAnnotationTypeId(self) -> hints.Incomplete: ...
        CurrentAnnotationTypeId = hints.normal_property(_get_CurrentAnnotationTypeId)
        def _get_CurrentAnnotationTypeName(self) -> hints.Incomplete: ...
        CurrentAnnotationTypeName = hints.normal_property(_get_CurrentAnnotationTypeName)
        def _get_CurrentAuthor(self) -> hints.Incomplete: ...
        CurrentAuthor = hints.normal_property(_get_CurrentAuthor)
        def _get_CurrentDateTime(self) -> hints.Incomplete: ...
        CurrentDateTime = hints.normal_property(_get_CurrentDateTime)
        def _get_CurrentTarget(self) -> 'IUIAutomationElement': ...
        CurrentTarget = hints.normal_property(_get_CurrentTarget)
        def _get_CachedAnnotationTypeId(self) -> hints.Incomplete: ...
        CachedAnnotationTypeId = hints.normal_property(_get_CachedAnnotationTypeId)
        def _get_CachedAnnotationTypeName(self) -> hints.Incomplete: ...
        CachedAnnotationTypeName = hints.normal_property(_get_CachedAnnotationTypeName)
        def _get_CachedAuthor(self) -> hints.Incomplete: ...
        CachedAuthor = hints.normal_property(_get_CachedAuthor)
        def _get_CachedDateTime(self) -> hints.Incomplete: ...
        CachedDateTime = hints.normal_property(_get_CachedDateTime)
        def _get_CachedTarget(self) -> 'IUIAutomationElement': ...
        CachedTarget = hints.normal_property(_get_CachedTarget)


IUIAutomationAnnotationPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAnnotationTypeId',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAnnotationTypeName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentAuthor',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentDateTime',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentTarget',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAnnotationTypeId',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAnnotationTypeName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedAuthor',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedDateTime',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedTarget',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'retVal')
    ),
]

UIA_OutlineThicknessPropertyId = 30164  # Constant c_int


class IUIAutomationTransformPattern2(IUIAutomationTransformPattern):
    _case_insensitive_ = True
    _iid_ = GUID('{6D74D017-6ECB-4381-B38B-3C17A48FF1C2}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def Zoom(self, zoomValue: hints.Incomplete) -> hints.Hresult: ...
        def ZoomByUnit(self, ZoomUnit: hints.Incomplete) -> hints.Hresult: ...
        def _get_CurrentCanZoom(self) -> hints.Incomplete: ...
        CurrentCanZoom = hints.normal_property(_get_CurrentCanZoom)
        def _get_CachedCanZoom(self) -> hints.Incomplete: ...
        CachedCanZoom = hints.normal_property(_get_CachedCanZoom)
        def _get_CurrentZoomLevel(self) -> hints.Incomplete: ...
        CurrentZoomLevel = hints.normal_property(_get_CurrentZoomLevel)
        def _get_CachedZoomLevel(self) -> hints.Incomplete: ...
        CachedZoomLevel = hints.normal_property(_get_CachedZoomLevel)
        def _get_CurrentZoomMinimum(self) -> hints.Incomplete: ...
        CurrentZoomMinimum = hints.normal_property(_get_CurrentZoomMinimum)
        def _get_CachedZoomMinimum(self) -> hints.Incomplete: ...
        CachedZoomMinimum = hints.normal_property(_get_CachedZoomMinimum)
        def _get_CurrentZoomMaximum(self) -> hints.Incomplete: ...
        CurrentZoomMaximum = hints.normal_property(_get_CurrentZoomMaximum)
        def _get_CachedZoomMaximum(self) -> hints.Incomplete: ...
        CachedZoomMaximum = hints.normal_property(_get_CachedZoomMaximum)


IUIAutomationTransformPattern2._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'Zoom',
        (['in'], c_double, 'zoomValue')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'ZoomByUnit',
        (['in'], ZoomUnit, 'ZoomUnit')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentCanZoom',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedCanZoom',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentZoomLevel',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedZoomLevel',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentZoomMinimum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedZoomMinimum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentZoomMaximum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedZoomMaximum',
        (['out', 'retval'], POINTER(c_double), 'retVal')
    ),
]

UIA_CenterPointPropertyId = 30165  # Constant c_int
UIA_RotationPropertyId = 30166  # Constant c_int

IUIAutomationElementArray._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'Length',
        (['out', 'retval'], POINTER(c_int), 'Length')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetElement',
        (['in'], c_int, 'index'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'element')
    ),
]

UIA_SizePropertyId = 30167  # Constant c_int


class IUIAutomationTextPattern2(IUIAutomationTextPattern):
    _case_insensitive_ = True
    _iid_ = GUID('{506A921A-FCC9-409F-B23B-37EB74106872}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def RangeFromAnnotation(self, annotation: hints.Incomplete) -> 'IUIAutomationTextRange': ...
        def GetCaretRange(self) -> tuple[hints.Incomplete, 'IUIAutomationTextRange']: ...


IUIAutomationTextPattern2._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'RangeFromAnnotation',
        (['in'], POINTER(IUIAutomationElement), 'annotation'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCaretRange',
        (['out'], POINTER(c_int), 'isActive'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
]

UIA_IsSelectionPattern2AvailablePropertyId = 30168  # Constant c_int
UIA_Selection2FirstSelectedItemPropertyId = 30169  # Constant c_int
UIA_Selection2LastSelectedItemPropertyId = 30170  # Constant c_int
UIA_Selection2CurrentSelectedItemPropertyId = 30171  # Constant c_int
UIA_Selection2ItemCountPropertyId = 30172  # Constant c_int
UIA_HeadingLevelPropertyId = 30173  # Constant c_int
UIA_IsDialogPropertyId = 30174  # Constant c_int
UIA_CaretPositionAttributeId = 40038  # Constant c_int
UIA_BulletStyleAttributeId = 40002  # Constant c_int
UIA_CapStyleAttributeId = 40003  # Constant c_int
UIA_CultureAttributeId = 40004  # Constant c_int
UIA_FontNameAttributeId = 40005  # Constant c_int
UIA_FontSizeAttributeId = 40006  # Constant c_int
UIA_FontWeightAttributeId = 40007  # Constant c_int
UIA_ForegroundColorAttributeId = 40008  # Constant c_int
UIA_HorizontalTextAlignmentAttributeId = 40009  # Constant c_int
UIA_IndentationFirstLineAttributeId = 40010  # Constant c_int

IUIAutomationEventHandlerGroup._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'AddActiveTextPositionChangedEventHandler',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['in'],
            POINTER(IUIAutomationActiveTextPositionChangedEventHandler),
            'handler',
        )
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddAutomationEventHandler',
        (['in'], c_int, 'eventId'),
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddChangesEventHandler',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(c_int), 'changeTypes'),
        (['in'], c_int, 'changesCount'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationChangesEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddNotificationEventHandler',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationNotificationEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddPropertyChangedEventHandler',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationPropertyChangedEventHandler), 'handler'),
        (['in'], POINTER(c_int), 'propertyArray'),
        (['in'], c_int, 'propertyCount')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddStructureChangedEventHandler',
        (['in'], TreeScope, 'scope'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (['in'], POINTER(IUIAutomationStructureChangedEventHandler), 'handler')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddTextEditTextChangedEventHandler',
        (['in'], TreeScope, 'scope'),
        (['in'], TextEditChangeType, 'TextEditChangeType'),
        (['in'], POINTER(IUIAutomationCacheRequest), 'cacheRequest'),
        (
            ['in'],
            POINTER(IUIAutomationTextEditTextChangedEventHandler),
            'handler',
        )
    ),
]

UIA_IndentationLeadingAttributeId = 40011  # Constant c_int


class IUIAutomationItemContainerPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{C690FDB2-27A8-423C-812D-429773C9084E}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def FindItemByProperty(self, pStartAfter: hints.Incomplete, propertyId: hints.Incomplete, value: hints.Incomplete) -> 'IUIAutomationElement': ...


IUIAutomationItemContainerPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'FindItemByProperty',
        (['in'], POINTER(IUIAutomationElement), 'pStartAfter'),
        (['in'], c_int, 'propertyId'),
        (['in'], VARIANT, 'value'),
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'pFound')
    ),
]

UIA_IndentationTrailingAttributeId = 40012  # Constant c_int
UIA_IsHiddenAttributeId = 40013  # Constant c_int

IAccessible._methods_ = [
    COMMETHOD(
        [dispid(-5000), 'hidden', 'propget'],
        HRESULT,
        'accParent',
        (['out', 'retval'], POINTER(POINTER(IDispatch)), 'ppdispParent')
    ),
    COMMETHOD(
        [dispid(-5001), 'hidden', 'propget'],
        HRESULT,
        'accChildCount',
        (['out', 'retval'], POINTER(c_int), 'pcountChildren')
    ),
    COMMETHOD(
        [dispid(-5002), 'hidden', 'propget'],
        HRESULT,
        'accChild',
        (['in'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(POINTER(IDispatch)), 'ppdispChild')
    ),
    COMMETHOD(
        [dispid(-5003), 'hidden', 'propget'],
        HRESULT,
        'accName',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(BSTR), 'pszName')
    ),
    COMMETHOD(
        [dispid(-5004), 'hidden', 'propget'],
        HRESULT,
        'accValue',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(BSTR), 'pszValue')
    ),
    COMMETHOD(
        [dispid(-5005), 'hidden', 'propget'],
        HRESULT,
        'accDescription',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(BSTR), 'pszDescription')
    ),
    COMMETHOD(
        [dispid(-5006), 'hidden', 'propget'],
        HRESULT,
        'accRole',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(VARIANT), 'pvarRole')
    ),
    COMMETHOD(
        [dispid(-5007), 'hidden', 'propget'],
        HRESULT,
        'accState',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(VARIANT), 'pvarState')
    ),
    COMMETHOD(
        [dispid(-5008), 'hidden', 'propget'],
        HRESULT,
        'accHelp',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(BSTR), 'pszHelp')
    ),
    COMMETHOD(
        [dispid(-5009), 'hidden', 'propget'],
        HRESULT,
        'accHelpTopic',
        (['out'], POINTER(BSTR), 'pszHelpFile'),
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(c_int), 'pidTopic')
    ),
    COMMETHOD(
        [dispid(-5010), 'hidden', 'propget'],
        HRESULT,
        'accKeyboardShortcut',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(BSTR), 'pszKeyboardShortcut')
    ),
    COMMETHOD(
        [dispid(-5011), 'hidden', 'propget'],
        HRESULT,
        'accFocus',
        (['out', 'retval'], POINTER(VARIANT), 'pvarChild')
    ),
    COMMETHOD(
        [dispid(-5012), 'hidden', 'propget'],
        HRESULT,
        'accSelection',
        (['out', 'retval'], POINTER(VARIANT), 'pvarChildren')
    ),
    COMMETHOD(
        [dispid(-5013), 'hidden', 'propget'],
        HRESULT,
        'accDefaultAction',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['out', 'retval'], POINTER(BSTR), 'pszDefaultAction')
    ),
    COMMETHOD(
        [dispid(-5014), 'hidden'],
        HRESULT,
        'accSelect',
        (['in'], c_int, 'flagsSelect'),
        (['in', 'optional'], VARIANT, 'varChild')
    ),
    COMMETHOD(
        [dispid(-5015), 'hidden'],
        HRESULT,
        'accLocation',
        (['out'], POINTER(c_int), 'pxLeft'),
        (['out'], POINTER(c_int), 'pyTop'),
        (['out'], POINTER(c_int), 'pcxWidth'),
        (['out'], POINTER(c_int), 'pcyHeight'),
        (['in', 'optional'], VARIANT, 'varChild')
    ),
    COMMETHOD(
        [dispid(-5016), 'hidden'],
        HRESULT,
        'accNavigate',
        (['in'], c_int, 'navDir'),
        (['in', 'optional'], VARIANT, 'varStart'),
        (['out', 'retval'], POINTER(VARIANT), 'pvarEndUpAt')
    ),
    COMMETHOD(
        [dispid(-5017), 'hidden'],
        HRESULT,
        'accHitTest',
        (['in'], c_int, 'xLeft'),
        (['in'], c_int, 'yTop'),
        (['out', 'retval'], POINTER(VARIANT), 'pvarChild')
    ),
    COMMETHOD(
        [dispid(-5018), 'hidden'],
        HRESULT,
        'accDoDefaultAction',
        (['in', 'optional'], VARIANT, 'varChild')
    ),
    COMMETHOD(
        [dispid(-5003), 'hidden', 'propput'],
        HRESULT,
        'accName',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['in'], BSTR, 'pszName')
    ),
    COMMETHOD(
        [dispid(-5004), 'hidden', 'propput'],
        HRESULT,
        'accValue',
        (['in', 'optional'], VARIANT, 'varChild'),
        (['in'], BSTR, 'pszValue')
    ),
]

UIA_IsItalicAttributeId = 40014  # Constant c_int
UIA_IsReadOnlyAttributeId = 40015  # Constant c_int
UIA_IsSubscriptAttributeId = 40016  # Constant c_int
UIA_IsSuperscriptAttributeId = 40017  # Constant c_int
UIA_MarginBottomAttributeId = 40018  # Constant c_int
UIA_MarginLeadingAttributeId = 40019  # Constant c_int
UIA_MarginTopAttributeId = 40020  # Constant c_int
UIA_MarginTrailingAttributeId = 40021  # Constant c_int
UIA_OutlineStylesAttributeId = 40022  # Constant c_int
UIA_OverlineColorAttributeId = 40023  # Constant c_int
UIA_OverlineStyleAttributeId = 40024  # Constant c_int
UIA_StrikethroughColorAttributeId = 40025  # Constant c_int
UIA_StrikethroughStyleAttributeId = 40026  # Constant c_int


class IUIAutomationTextEditPattern(IUIAutomationTextPattern):
    _case_insensitive_ = True
    _iid_ = GUID('{17E21576-996C-4870-99D9-BFF323380C06}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def GetActiveComposition(self) -> 'IUIAutomationTextRange': ...
        def GetConversionTarget(self) -> 'IUIAutomationTextRange': ...


IUIAutomationTextEditPattern._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'GetActiveComposition',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetConversionTarget',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
]

UIA_TabsAttributeId = 40027  # Constant c_int

IUIAutomationCacheRequest._methods_ = [
    COMMETHOD(
        [],
        HRESULT,
        'AddProperty',
        (['in'], c_int, 'propertyId')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'AddPattern',
        (['in'], c_int, 'patternId')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'Clone',
        (
            ['out', 'retval'],
            POINTER(POINTER(IUIAutomationCacheRequest)),
            'clonedRequest',
        )
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'TreeScope',
        (['out', 'retval'], POINTER(TreeScope), 'scope')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'TreeScope',
        (['in'], TreeScope, 'scope')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'TreeFilter',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationCondition)), 'filter')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'TreeFilter',
        (['in'], POINTER(IUIAutomationCondition), 'filter')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'AutomationElementMode',
        (['out', 'retval'], POINTER(AutomationElementMode), 'mode')
    ),
    COMMETHOD(
        ['propput'],
        HRESULT,
        'AutomationElementMode',
        (['in'], AutomationElementMode, 'mode')
    ),
]

UIA_TextFlowDirectionsAttributeId = 40028  # Constant c_int
UIA_UnderlineColorAttributeId = 40029  # Constant c_int


class IUIAutomationTextChildPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{6552B038-AE05-40C8-ABFD-AA08352AAB86}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_TextContainer(self) -> 'IUIAutomationElement': ...
        TextContainer = hints.normal_property(_get_TextContainer)
        def _get_TextRange(self) -> 'IUIAutomationTextRange': ...
        TextRange = hints.normal_property(_get_TextRange)


IUIAutomationTextChildPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'TextContainer',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationElement)), 'container')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'TextRange',
        (['out', 'retval'], POINTER(POINTER(IUIAutomationTextRange)), 'range')
    ),
]

UIA_UnderlineStyleAttributeId = 40030  # Constant c_int
UIA_AnnotationTypesAttributeId = 40031  # Constant c_int


class IUIAutomationStylesPattern(comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0.IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{85B5F0A2-BD79-484A-AD2B-388C9838D5FB}')
    _idlflags_ = []

    if TYPE_CHECKING:  # commembers
        def _get_CurrentStyleId(self) -> hints.Incomplete: ...
        CurrentStyleId = hints.normal_property(_get_CurrentStyleId)
        def _get_CurrentStyleName(self) -> hints.Incomplete: ...
        CurrentStyleName = hints.normal_property(_get_CurrentStyleName)
        def _get_CurrentFillColor(self) -> hints.Incomplete: ...
        CurrentFillColor = hints.normal_property(_get_CurrentFillColor)
        def _get_CurrentFillPatternStyle(self) -> hints.Incomplete: ...
        CurrentFillPatternStyle = hints.normal_property(_get_CurrentFillPatternStyle)
        def _get_CurrentShape(self) -> hints.Incomplete: ...
        CurrentShape = hints.normal_property(_get_CurrentShape)
        def _get_CurrentFillPatternColor(self) -> hints.Incomplete: ...
        CurrentFillPatternColor = hints.normal_property(_get_CurrentFillPatternColor)
        def _get_CurrentExtendedProperties(self) -> hints.Incomplete: ...
        CurrentExtendedProperties = hints.normal_property(_get_CurrentExtendedProperties)
        def GetCurrentExtendedPropertiesAsArray(self) -> tuple[hints.Incomplete, hints.Incomplete]: ...
        def _get_CachedStyleId(self) -> hints.Incomplete: ...
        CachedStyleId = hints.normal_property(_get_CachedStyleId)
        def _get_CachedStyleName(self) -> hints.Incomplete: ...
        CachedStyleName = hints.normal_property(_get_CachedStyleName)
        def _get_CachedFillColor(self) -> hints.Incomplete: ...
        CachedFillColor = hints.normal_property(_get_CachedFillColor)
        def _get_CachedFillPatternStyle(self) -> hints.Incomplete: ...
        CachedFillPatternStyle = hints.normal_property(_get_CachedFillPatternStyle)
        def _get_CachedShape(self) -> hints.Incomplete: ...
        CachedShape = hints.normal_property(_get_CachedShape)
        def _get_CachedFillPatternColor(self) -> hints.Incomplete: ...
        CachedFillPatternColor = hints.normal_property(_get_CachedFillPatternColor)
        def _get_CachedExtendedProperties(self) -> hints.Incomplete: ...
        CachedExtendedProperties = hints.normal_property(_get_CachedExtendedProperties)
        def GetCachedExtendedPropertiesAsArray(self) -> tuple[hints.Incomplete, hints.Incomplete]: ...


IUIAutomationStylesPattern._methods_ = [
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentStyleId',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentStyleName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFillColor',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFillPatternStyle',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentShape',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentFillPatternColor',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CurrentExtendedProperties',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCurrentExtendedPropertiesAsArray',
        (['out'], POINTER(POINTER(ExtendedProperty)), 'propertyArray'),
        (['out'], POINTER(c_int), 'propertyCount')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedStyleId',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedStyleName',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFillColor',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFillPatternStyle',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedShape',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedFillPatternColor',
        (['out', 'retval'], POINTER(c_int), 'retVal')
    ),
    COMMETHOD(
        ['propget'],
        HRESULT,
        'CachedExtendedProperties',
        (['out', 'retval'], POINTER(BSTR), 'retVal')
    ),
    COMMETHOD(
        [],
        HRESULT,
        'GetCachedExtendedPropertiesAsArray',
        (['out'], POINTER(POINTER(ExtendedProperty)), 'propertyArray'),
        (['out'], POINTER(c_int), 'propertyCount')
    ),
]

UIA_AnnotationObjectsAttributeId = 40032  # Constant c_int
UIA_StyleNameAttributeId = 40033  # Constant c_int
UIA_StyleIdAttributeId = 40034  # Constant c_int

__all__ = [
    'UIA_InvokePatternId', 'AnnotationType_DataValidationError',
    'UiaChangeInfo', 'UIA_AnnotationObjectsAttributeId',
    'UIA_VisualEffectsPropertyId', 'StructureChangeType',
    'AnnotationType_Endnote', 'NotificationKind_ItemRemoved',
    'SupportedTextSelection', 'IUIAutomationSelectionPattern',
    'RowOrColumnMajor_Indeterminate',
    'UIA_IndentationFirstLineAttributeId', 'TreeScope_Descendants',
    'UIA_SpreadsheetPatternId',
    'UIA_IsItemContainerPatternAvailablePropertyId',
    'UIA_ScrollVerticallyScrollablePropertyId',
    'UIA_MenuModeStartEventId', 'TextUnit_Paragraph',
    'UIA_SearchLandmarkTypeId', 'WindowVisualState_Normal',
    'UIA_IsTextChildPatternAvailablePropertyId', 'ZoomUnit_NoAmount',
    'ProviderOptions_OverrideProvider', 'CUIAutomation',
    'UIA_TreeControlTypeId', 'UIA_ItemContainerPatternId',
    'UIA_SpreadsheetItemAnnotationObjectsPropertyId',
    'UIA_SplitButtonControlTypeId', 'TextUnit',
    'IUIAutomationElement2',
    'ConnectionRecoveryBehaviorOptions_Disabled',
    'UIA_CultureAttributeId', 'typelib_path',
    'UIA_IsPeripheralPropertyId', 'DockPosition_Right', 'Library',
    'UIA_MarginBottomAttributeId', 'UIA_Drag_DragCompleteEventId',
    'UIA_ImageControlTypeId', 'UIA_LiveRegionChangedEventId',
    'UIA_ToolTipOpenedEventId', 'UIA_WindowIsModalPropertyId',
    'UIA_IsSpreadsheetItemPatternAvailablePropertyId',
    'UIA_Invoke_InvokedEventId', 'UIA_ToolBarControlTypeId',
    'UIA_AnnotationTypesAttributeId', 'UIA_RangeValuePatternId',
    'ZoomUnit_SmallIncrement', 'IUIAutomationScrollPattern',
    'IUIAutomationExpandCollapsePattern',
    'IUIAutomationMultipleViewPattern', 'UIA_SliderControlTypeId',
    'UIA_DragDropEffectPropertyId',
    'UIA_SelectionItemSelectionContainerPropertyId',
    'UIA_MenuClosedEventId',
    'UIA_Selection2CurrentSelectedItemPropertyId', 'StyleId_Heading7',
    'UIA_BeforeParagraphSpacingAttributeId',
    'NotificationProcessing_MostRecent', 'UIA_DataItemControlTypeId',
    'UIA_ProviderDescriptionPropertyId', 'UIA_PaneControlTypeId',
    'ExpandCollapseState', 'UIA_OverlineStyleAttributeId',
    'UIA_TablePatternId', 'IUIAutomationObjectModelPattern',
    'UIA_LinkAttributeId', 'IUIAutomationCustomNavigationPattern',
    'IUIAutomationTextEditTextChangedEventHandler',
    'UIA_TextChildPatternId', 'UIA_DockDockPositionPropertyId',
    'UIA_StylesFillPatternColorPropertyId',
    'UIA_InputDiscardedEventId', 'AnnotationType_GrammarError',
    'UIA_IsTransformPattern2AvailablePropertyId',
    'AnnotationType_Unknown', 'ScrollAmount_NoAmount',
    'IUIAutomation6', 'UIA_IsWindowPatternAvailablePropertyId',
    'HeadingLevel_None', 'IUIAutomationElement6',
    'UIA_GridRowCountPropertyId', 'ExpandCollapseState_LeafNode',
    'UIA_ChangesEventId', 'AnnotationType_InsertionChange',
    'UIA_AcceleratorKeyPropertyId', 'Polite',
    'StructureChangeType_ChildrenReordered', 'HeadingLevel7',
    'UIA_MarginTopAttributeId',
    'UIA_MultipleViewSupportedViewsPropertyId',
    'UIA_TableItemColumnHeaderItemsPropertyId',
    'UIA_HelpTextPropertyId',
    'TextEditChangeType_CompositionFinalized',
    'AnnotationType_DeletionChange', 'UIA_SelectionPatternId',
    'TreeTraversalOptions', 'IUIAutomationElement5',
    'UIA_TransformCanResizePropertyId', 'UIA_SystemAlertEventId',
    'DockPosition_Left', 'UIA_BackgroundColorAttributeId',
    'UIA_IsGridItemPatternAvailablePropertyId',
    'IUIAutomationVirtualizedItemPattern',
    'UIA_IsSelectionItemPatternAvailablePropertyId',
    'UIA_TitleBarControlTypeId', 'UIA_CalendarControlTypeId',
    'UIA_IsDialogPropertyId', 'UIA_MenuOpenedEventId',
    'UIA_ToolTipClosedEventId',
    'UIA_StylesFillPatternStylePropertyId', 'NavigateDirection',
    'NotificationProcessing_ImportantAll', 'IUIAutomationElement9',
    'WindowInteractionState', 'UIA_DragPatternId',
    'ExpandCollapseState_Collapsed', 'ExpandCollapseState_Expanded',
    'IUIAutomationBoolCondition', 'UIA_MenuBarControlTypeId',
    'UIA_IsOffscreenPropertyId', 'StyleId_Normal',
    'UIA_ListItemControlTypeId',
    'AnnotationType_AdvancedProofingIssue', 'IUIAutomationCondition',
    'UIA_TransformCanRotatePropertyId',
    'UIA_Selection2ItemCountPropertyId', 'UIA_OrientationPropertyId',
    'UIA_CustomLandmarkTypeId', 'HeadingLevel5',
    'UIA_BulletStyleAttributeId', 'IUIAutomationGridItemPattern',
    'UIA_ToggleToggleStatePropertyId',
    'UIA_TableColumnHeadersPropertyId', 'UIA_MenuItemControlTypeId',
    'UIA_ScrollVerticalScrollPercentPropertyId',
    'UIA_LocalizedControlTypePropertyId',
    'ProviderOptions_ProviderOwnsSetFocus',
    'UIA_ControlTypePropertyId', 'UIA_ListControlTypeId',
    'UIA_AnnotationTypesPropertyId', 'IUIAutomationTextPattern',
    'UIA_IsSelectionPatternAvailablePropertyId',
    'ZoomUnit_SmallDecrement',
    'UIA_LegacyIAccessibleDescriptionPropertyId',
    'UIA_OutlineStylesAttributeId', 'RowOrColumnMajor_ColumnMajor',
    'NotificationProcessing_ImportantMostRecent',
    'UIA_ToolTipControlTypeId', 'IAccessible', 'Off',
    'UIA_IsTableItemPatternAvailablePropertyId',
    'UIA_MenuModeEndEventId', 'UIA_AnnotationObjectsPropertyId',
    'AnnotationType_Footer', 'UIA_LandmarkTypePropertyId',
    'UIA_WindowControlTypeId',
    'StructureChangeType_ChildrenInvalidated',
    'UIA_WindowWindowInteractionStatePropertyId',
    'UIA_SelectionItem_ElementSelectedEventId',
    'ProviderOptions_UseComThreading',
    'UIA_SelectionSelectionPropertyId', 'AnnotationType_Highlighted',
    'UIA_DragDropEffectsPropertyId', 'NotificationProcessing',
    'UIA_SpinnerControlTypeId',
    'UIA_AnnotationAnnotationTypeIdPropertyId',
    'AnnotationType_TrackChanges',
    'AnnotationType_CircularReferenceError', 'UIA_TabsAttributeId',
    'StyleId_Heading5', 'UIA_CapStyleAttributeId',
    'SupportedTextSelection_Multiple', 'UIA_ExpandCollapsePatternId',
    'UIA_DocumentControlTypeId', 'OrientationType',
    'UIA_LegacyIAccessibleNamePropertyId',
    'IUIAutomationAndCondition', 'UIA_SemanticZoomControlTypeId',
    'OrientationType_None',
    'UIA_ScrollHorizontallyScrollablePropertyId',
    'UIA_SayAsInterpretAsMetadataId',
    'UIA_SelectionItemIsSelectedPropertyId',
    'UIA_IsObjectModelPatternAvailablePropertyId',
    'ProviderOptions_ServerSideProvider',
    'PropertyConditionFlags_None', 'StyleId_NumberedList',
    'UIA_MultipleViewCurrentViewPropertyId', 'UIA_FlowsToPropertyId',
    'StyleId_Quote', 'UIA_ValuePatternId',
    'UIA_Drag_DragCancelEventId', 'UIA_ItemStatusPropertyId',
    'UIA_WindowIsTopmostPropertyId', 'UIA_CustomNavigationPatternId',
    'StyleId_Custom', 'UIA_AnnotationAuthorPropertyId',
    'IUIAutomationElement8', 'UIA_ControllerForPropertyId',
    'UIA_Window_WindowClosedEventId', 'UIA_TextPatternId',
    'UIA_AsyncContentLoadedEventId', 'UIA_NamePropertyId',
    'SynchronizedInputType_KeyDown',
    'UIA_IsDockPatternAvailablePropertyId',
    'UIA_ScrollVerticalViewSizePropertyId',
    'UIA_HyperlinkControlTypeId', 'UIA_FontNameAttributeId',
    'AnnotationType_Header', 'UIA_UnderlineColorAttributeId',
    'AnnotationType_FormatChange', 'UIA_IsReadOnlyAttributeId',
    'IUIAutomationTextRange', 'PropertyConditionFlags_IgnoreCase',
    'AnnotationType_Sensitive', 'UIA_Transform2ZoomMinimumPropertyId',
    'IUIAutomationTransformPattern2',
    'UIA_IsLegacyIAccessiblePatternAvailablePropertyId',
    'UIA_TransformPatternId', 'UIA_ItemTypePropertyId',
    'IUIAutomationWindowPattern', 'UIA_HeaderItemControlTypeId',
    'UIA_TreeItemControlTypeId', 'IUIAutomationElementArray',
    'UIA_MarginLeadingAttributeId', 'UIA_RotationPropertyId',
    'UIA_IsInvokePatternAvailablePropertyId',
    'UIA_Drag_DragStartEventId', 'UIA_AnnotationDateTimePropertyId',
    'UIA_WindowCanMaximizePropertyId',
    'UIA_IsGridPatternAvailablePropertyId',
    'ProviderOptions_NonClientAreaProvider',
    'AnnotationType_SpellingError',
    'UIA_LegacyIAccessibleChildIdPropertyId', 'CUIAutomation8',
    'UIA_FontWeightAttributeId', 'UIA_IsDataValidForFormPropertyId',
    'UIA_TransformCanMovePropertyId',
    'UIA_LocalizedLandmarkTypePropertyId',
    'UIA_GridItemRowSpanPropertyId',
    'UIA_RangeValueIsReadOnlyPropertyId', 'ZoomUnit',
    'RowOrColumnMajor', 'IUIAutomationScrollItemPattern',
    'UIA_IsActiveAttributeId', 'UIA_StylesPatternId', 'TreeScope',
    'IUIAutomationStylesPattern',
    'UIA_TextEdit_ConversionTargetChangedEventId',
    'IUIAutomationNotCondition', 'UIA_SelectionPattern2Id',
    'OrientationType_Horizontal', 'ToggleState_On', 'StyleId_Title',
    'TextEditChangeType_AutoComplete', 'UIA_CulturePropertyId',
    'UIA_NotificationEventId', 'UIA_DockPatternId',
    'ExtendedProperty', 'ScrollAmount_SmallDecrement',
    'IUIAutomationTextRangeArray', 'UIA_DragGrabbedItemsPropertyId',
    'NavigateDirection_NextSibling',
    'IUIAutomationNotificationEventHandler', 'ToggleState',
    'StyleId_Heading8', 'IUIAutomationSelectionPattern2',
    'UIA_SayAsInterpretAsAttributeId',
    'SynchronizedInputType_RightMouseUp', 'IUIAutomationDockPattern',
    'IUIAutomationTextPattern2', 'UIA_OutlineThicknessPropertyId',
    'UIA_Window_WindowOpenedEventId',
    'ProviderOptions_HasNativeIAccessible',
    'UIA_IsControlElementPropertyId', 'StyleId_Heading3',
    'UIA_LiveSettingPropertyId', 'IUIAutomationValuePattern',
    'UIA_GridPatternId', 'ConnectionRecoveryBehaviorOptions_Enabled',
    'UIA_IsTextPatternAvailablePropertyId',
    'AnnotationType_UnsyncedChange',
    'NavigateDirection_PreviousSibling', 'UIA_IsItalicAttributeId',
    'TreeTraversalOptions_Default', 'UIA_LegacyIAccessiblePatternId',
    'UIA_SelectionActiveEndAttributeId',
    'UIA_AfterParagraphSpacingAttributeId',
    'UIA_BoundingRectanglePropertyId',
    'UIA_IsVirtualizedItemPatternAvailablePropertyId',
    'HeadingLevel6', 'IUIAutomationItemContainerPattern',
    'HeadingLevel2', 'ProviderOptions_UseClientCoordinates',
    'UIA_RuntimeIdPropertyId', 'UIA_ComboBoxControlTypeId',
    'StructureChangeType_ChildAdded',
    'UIA_TableItemRowHeaderItemsPropertyId',
    'SynchronizedInputType_RightMouseDown', 'SynchronizedInputType',
    'UIA_IsTogglePatternAvailablePropertyId',
    'IUIAutomationSpreadsheetItemPattern',
    'UIA_IndentationTrailingAttributeId',
    'IUIAutomationActiveTextPositionChangedEventHandler',
    'SynchronizedInputType_LeftMouseUp',
    'UIA_ValueIsReadOnlyPropertyId', 'UIA_LineSpacingAttributeId',
    'CoalesceEventsOptions_Disabled', 'TreeScope_Element',
    'TextUnit_Document', 'UIA_ProgressBarControlTypeId',
    'UIA_ThumbControlTypeId', 'IUIAutomationInvokePattern',
    'UIA_IsDragPatternAvailablePropertyId',
    'UIA_DropTarget_DragLeaveEventId', 'UIA_VirtualizedItemPatternId',
    'UIA_ProcessIdPropertyId', 'ScrollAmount', 'UIA_LevelPropertyId',
    'UIA_TabControlTypeId', 'UIA_StrikethroughStyleAttributeId',
    'UIA_ClickablePointPropertyId', 'UIA_ValueValuePropertyId',
    'StyleId_Heading6', 'UIA_IsTransformPatternAvailablePropertyId',
    'UIA_HorizontalTextAlignmentAttributeId',
    'UIA_OptimizeForVisualContentPropertyId', 'StyleId_Emphasis',
    'NotificationKind_ItemAdded', 'IUIAutomationChangesEventHandler',
    'NotificationProcessing_ImportantCurrentThenMostRecent',
    'UIA_AppBarControlTypeId', 'IUIAutomationElement',
    'UIA_LayoutInvalidatedEventId',
    'UIA_DropTargetDropTargetEffectsPropertyId',
    'NotificationKind_ActionAborted', 'UIA_GridItemPatternId',
    'UIA_GridColumnCountPropertyId',
    'UIA_WindowWindowVisualStatePropertyId', 'AutomationElementMode',
    'WindowInteractionState_Closing', 'DockPosition_None',
    'UIA_Text_TextSelectionChangedEventId',
    'UIA_SelectionItem_ElementRemovedFromSelectionEventId',
    'UIA_TableControlTypeId', 'UIA_SelectionItemPatternId',
    'UIA_FrameworkIdPropertyId', 'IUIAutomation4', 'TreeScope_None',
    'IUIAutomationSelectionItemPattern',
    'PropertyConditionFlags_MatchSubstring',
    'UIA_IsSubscriptAttributeId', 'ZoomUnit_LargeIncrement',
    'UIA_SpreadsheetItemAnnotationTypesPropertyId',
    'UIA_DescribedByPropertyId', 'UIA_StylesStyleIdPropertyId',
    'IUIAutomationProxyFactoryEntry',
    'IUIAutomationProxyFactoryMapping',
    'UIA_GridItemColumnSpanPropertyId', 'UIA_ScrollBarControlTypeId',
    'HeadingLevel4', 'ScrollAmount_LargeIncrement',
    'UIA_LegacyIAccessibleRolePropertyId',
    'UIA_InputReachedOtherElementEventId', 'TextUnit_Format',
    'AnnotationType_ExternalChange', 'IUIAutomationTextEditPattern',
    'ProviderOptions', 'IUIAutomationGridPattern',
    'UIA_LegacyIAccessibleHelpPropertyId',
    'StructureChangeType_ChildRemoved', 'IUIAutomationEventHandler',
    'UIA_IsHiddenAttributeId', 'UIA_IsSuperscriptAttributeId',
    'IUIAutomationFocusChangedEventHandler',
    'IUIAutomationDropTargetPattern',
    'IUIAutomationRangeValuePattern', 'TreeScope_Subtree',
    'UIA_SeparatorControlTypeId', 'StyleId_BulletedList',
    'UIA_StatusBarControlTypeId',
    'UIA_IsExpandCollapsePatternAvailablePropertyId',
    'UIA_IsRequiredForFormPropertyId',
    'UIA_HostedFragmentRootsInvalidatedEventId',
    'UIA_TableRowOrColumnMajorPropertyId',
    'UIA_MarginTrailingAttributeId', 'UIA_TableRowHeadersPropertyId',
    'UIA_TextPattern2Id', 'IUIAutomationEventHandlerGroup',
    'UIA_IsTablePatternAvailablePropertyId',
    'UIA_IsPasswordPropertyId', 'TreeScope_Children',
    'IUIAutomationSpreadsheetPattern',
    'IUIAutomationStructureChangedEventHandler',
    'UIA_RangeValueSmallChangePropertyId',
    'TreeTraversalOptions_PostOrder', 'TextUnit_Line',
    'UIA_CaretPositionAttributeId',
    'UIA_ScrollHorizontalScrollPercentPropertyId', 'StyleId_Heading4',
    'TextEditChangeType_Composition', 'ToggleState_Off',
    'DockPosition_Bottom', 'IUIAutomationElement3',
    'OrientationType_Vertical', 'ScrollAmount_SmallIncrement',
    'IUIAutomationTextRange2', 'UIA_WindowPatternId',
    'UIA_SpreadsheetItemPatternId', 'UIA_TabItemControlTypeId',
    'UIA_CenterPointPropertyId',
    'WindowInteractionState_NotResponding', 'UIA_FlowsFromPropertyId',
    'UIA_HeaderControlTypeId',
    'UIA_IsValuePatternAvailablePropertyId',
    'UIA_RangeValueMaximumPropertyId', 'StyleId_Heading9',
    'AutomationElementMode_Full', 'IUIAutomationElement7',
    'DockPosition_Top', 'IUIAutomationAnnotationPattern',
    'UIA_ButtonControlTypeId', 'PropertyConditionFlags',
    'AnnotationType_ConflictingChange',
    'ExpandCollapseState_PartiallyExpanded',
    'UIA_DropTarget_DragEnterEventId', 'UIA_GroupControlTypeId',
    'IUIAutomationElement4', 'UIA_ClassNamePropertyId',
    'NotificationProcessing_All', 'UIA_StylesStyleNamePropertyId',
    'ToggleState_Indeterminate', 'UIA_Text_TextChangedEventId',
    'IUIAutomation5', 'UIA_FillTypePropertyId',
    'UIA_CaretBidiModeAttributeId',
    'IUIAutomationSynchronizedInputPattern',
    'UIA_IsRangeValuePatternAvailablePropertyId',
    'UIA_AnnotationAnnotationTypeNamePropertyId',
    'UIA_IsSelectionPattern2AvailablePropertyId',
    'UIA_FormLandmarkTypeId', 'UIA_TextEdit_TextChangedEventId',
    'UIA_IndentationLeadingAttributeId', 'AnnotationType_Author',
    'UIA_Transform2ZoomMaximumPropertyId',
    'UIA_Selection_InvalidatedEventId', 'NavigateDirection_LastChild',
    'DockPosition', 'UIA_SummaryChangeId', 'HeadingLevel1',
    'UIA_AriaPropertiesPropertyId',
    'UIA_IsTextPattern2AvailablePropertyId',
    'UIA_SpreadsheetItemFormulaPropertyId',
    'UIA_IsDropTargetPatternAvailablePropertyId',
    'UIA_Selection2FirstSelectedItemPropertyId',
    'UIA_MenuControlTypeId', 'IUIAutomationCacheRequest',
    'UIA_OverlineColorAttributeId', 'NavigateDirection_Parent',
    'UIA_IsContentElementPropertyId',
    'UIA_AutomationFocusChangedEventId', 'ZoomUnit_LargeDecrement',
    'IUIAutomation2', 'UIA_IsStylesPatternAvailablePropertyId',
    'UIA_AccessKeyPropertyId', 'UIA_Transform2CanZoomPropertyId',
    'WindowVisualState', 'UIA_SynchronizedInputPatternId',
    'UIA_CheckBoxControlTypeId', 'UIA_HasKeyboardFocusPropertyId',
    'UIA_AriaRolePropertyId', 'WindowVisualState_Minimized',
    'UIA_IsScrollPatternAvailablePropertyId',
    'UIA_Transform2ZoomLevelPropertyId',
    'UIA_LegacyIAccessibleKeyboardShortcutPropertyId',
    'UIA_LegacyIAccessibleSelectionPropertyId',
    'UIA_OutlineColorPropertyId', 'UIA_DropTarget_DroppedEventId',
    'WindowInteractionState_BlockedByModalWindow',
    'StructureChangeType_ChildrenBulkRemoved',
    'NavigateDirection_FirstChild', 'SupportedTextSelection_Single',
    'SynchronizedInputType_KeyUp',
    'UIA_DropTargetDropTargetEffectPropertyId',
    'UIA_StyleNameAttributeId', 'IUIAutomation',
    'UIA_SizeOfSetPropertyId', 'UIA_TextControlTypeId',
    'UIA_AutomationPropertyChangedEventId',
    'UIA_IsCustomNavigationPatternAvailablePropertyId',
    'TextUnit_Word', 'IUIAutomationProxyFactory',
    'UIA_ScrollHorizontalViewSizePropertyId',
    'UIA_FillColorPropertyId', 'UIA_LabeledByPropertyId',
    'WindowInteractionState_Running',
    'UIA_StylesExtendedPropertiesPropertyId',
    'UIA_LegacyIAccessibleDefaultActionPropertyId',
    'ScrollAmount_LargeDecrement', 'UIA_StyleIdAttributeId',
    'IUIAutomationTextChildPattern', 'DockPosition_Fill',
    'UIA_GridItemContainingGridPropertyId', 'TreeScope_Ancestors',
    'StyleId_Heading1', 'UIA_UnderlineStyleAttributeId',
    'NotificationKind', 'UIA_ActiveTextPositionChangedEventId',
    'UIA_FullDescriptionPropertyId', 'StyleId_Heading2',
    'IUIAutomationTransformPattern', 'TextUnit_Page',
    'UIA_RangeValueLargeChangePropertyId',
    'UIA_WindowCanMinimizePropertyId', 'UIA_TextEditPatternId',
    'IUIAutomationLegacyIAccessiblePattern',
    'SupportedTextSelection_None', 'UIA_ObjectModelPatternId',
    'UIA_AutomationIdPropertyId', 'HeadingLevel8',
    'NotificationKind_ActionCompleted', 'AnnotationType_FormulaError',
    'IUIAutomationTreeWalker', 'StyleId_Subtitle',
    'TextEditChangeType_None', 'TextPatternRangeEndpoint_End',
    'UIA_AnimationStyleAttributeId', 'UIA_DataGridControlTypeId',
    'AutomationElementMode_None', 'TreeScope_Parent', 'HeadingLevel3',
    'IUIAutomation3', 'UIA_PositionInSetPropertyId',
    'UIA_CustomControlTypeId', 'ProviderOptions_ClientSideProvider',
    'IUIAutomationPropertyCondition', 'UIA_GridItemRowPropertyId',
    'NotificationKind_Other', 'UIA_NativeWindowHandlePropertyId',
    'UIA_TransformPattern2Id',
    'ProviderOptions_RefuseNonClientSupport',
    'UIA_RangeValueMinimumPropertyId', 'HeadingLevel9',
    'SynchronizedInputType_LeftMouseDown', 'UIA_EditControlTypeId',
    'UIA_TableItemPatternId', 'IRawElementProviderSimple',
    'UIA_AnnotationTargetPropertyId', 'TextEditChangeType',
    'StructureChangeType_ChildrenBulkAdded',
    'UIA_ForegroundColorAttributeId', 'AnnotationType_Mathematics',
    'UIA_StylesFillColorPropertyId', 'UIA_HeadingLevelPropertyId',
    'UIA_MainLandmarkTypeId', 'UIA_IsEnabledPropertyId',
    'TextEditChangeType_AutoCorrect', 'UIA_InputReachedTargetEventId',
    'AnnotationType_MoveChange', 'UIA_DragIsGrabbedPropertyId',
    'UIA_FontSizeAttributeId', 'UIA_RangeValueValuePropertyId',
    'UIA_SelectionItem_ElementAddedToSelectionEventId',
    'UIA_IsTextEditPatternAvailablePropertyId',
    'UIA_SelectionCanSelectMultiplePropertyId',
    'TreeTraversalOptions_LastToFirstOrder',
    'IUIAutomationOrCondition', 'UIA_ScrollItemPatternId',
    'UIA_RadioButtonControlTypeId',
    'UIA_Selection2LastSelectedItemPropertyId',
    'UIA_IsMultipleViewPatternAvailablePropertyId',
    'UIA_IsSpreadsheetPatternAvailablePropertyId',
    'UIA_MultipleViewPatternId', 'AnnotationType_EditingLockedChange',
    'UIA_GridItemColumnPropertyId',
    'UIA_ExpandCollapseExpandCollapseStatePropertyId',
    'RowOrColumnMajor_RowMajor',
    'UIA_LegacyIAccessibleStatePropertyId', 'CoalesceEventsOptions',
    'UIA_SizePropertyId',
    'UIA_IsSynchronizedInputPatternAvailablePropertyId',
    'UIA_ScrollPatternId', 'UIA_StylesShapePropertyId',
    'TextPatternRangeEndpoint', 'TextPatternRangeEndpoint_Start',
    'IUIAutomationTableItemPattern', 'IUIAutomationTogglePattern',
    'WindowVisualState_Maximized', 'AnnotationType_Comment',
    'AnnotationType_Footnote', 'IUIAutomationTextRange3',
    'NotificationProcessing_CurrentThenMostRecent',
    'UIA_AnnotationPatternId', 'TextUnit_Character',
    'UIA_LegacyIAccessibleValuePropertyId',
    'UIA_IsKeyboardFocusablePropertyId',
    'UIA_TextFlowDirectionsAttributeId',
    'ConnectionRecoveryBehaviorOptions', 'UIA_DropTargetPatternId',
    'UIA_IsAnnotationPatternAvailablePropertyId',
    'UIA_IsScrollItemPatternAvailablePropertyId',
    'IUIAutomationTablePattern',
    'IUIAutomationPropertyChangedEventHandler',
    'CoalesceEventsOptions_Enabled', 'Assertive',
    'UIA_NavigationLandmarkTypeId', 'LiveSetting',
    'UIA_SelectionIsSelectionRequiredPropertyId',
    'WindowInteractionState_ReadyForUserInteraction',
    'UIA_StructureChangedEventId', 'UIA_TogglePatternId',
    'UIA_StrikethroughColorAttributeId', 'IUIAutomationDragPattern'
]

_check_version('1.5.0', 1778860965.604350)

