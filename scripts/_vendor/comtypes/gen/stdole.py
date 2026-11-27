from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    StdFont, OLE_YSIZE_CONTAINER, Checked, OLE_COLOR, FONTITALIC,
    Monochrome, FONTNAME, IEnumVARIANT, _check_version,
    OLE_XPOS_HIMETRIC, Font, OLE_XPOS_CONTAINER, DISPMETHOD,
    FontEvents, GUID, Picture, OLE_YPOS_PIXELS, Gray,
    OLE_XSIZE_CONTAINER, VgaColor, FONTBOLD, IPictureDisp, StdPicture,
    IPicture, dispid, Unchecked, Default, IFontDisp, IUnknown,
    OLE_YPOS_CONTAINER, typelib_path, Library, OLE_YPOS_HIMETRIC,
    OLE_YSIZE_PIXELS, OLE_OPTEXCLUSIVE, OLE_XPOS_PIXELS, OLE_HANDLE,
    OLE_XSIZE_PIXELS, COMMETHOD, OLE_ENABLEDEFAULTBOOL,
    OLE_YSIZE_HIMETRIC, IDispatch, IFontEventsDisp, OLE_CANCELBOOL,
    EXCEPINFO, OLE_XSIZE_HIMETRIC, HRESULT, FONTUNDERSCORE, FONTSIZE,
    DISPPROPERTY, BSTR, Color, FONTSTRIKETHROUGH, IFont, DISPPARAMS,
    VARIANT_BOOL, CoClass, _lcid
)


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


__all__ = [
    'StdFont', 'OLE_YPOS_HIMETRIC', 'OLE_YSIZE_PIXELS',
    'OLE_OPTEXCLUSIVE', 'OLE_YSIZE_CONTAINER', 'Checked',
    'OLE_XPOS_PIXELS', 'OLE_COLOR', 'OLE_HANDLE', 'FONTITALIC',
    'OLE_XSIZE_PIXELS', 'Monochrome', 'FONTNAME', 'OLE_XPOS_HIMETRIC',
    'Font', 'OLE_XPOS_CONTAINER', 'OLE_ENABLEDEFAULTBOOL',
    'FontEvents', 'OLE_YSIZE_HIMETRIC', 'Picture', 'IFontEventsDisp',
    'OLE_YPOS_PIXELS', 'Gray', 'OLE_XSIZE_CONTAINER', 'VgaColor',
    'OLE_TRISTATE', 'LoadPictureConstants', 'FONTBOLD',
    'IPictureDisp', 'OLE_CANCELBOOL', 'StdPicture',
    'OLE_XSIZE_HIMETRIC', 'IPicture', 'FONTUNDERSCORE', 'FONTSIZE',
    'Unchecked', 'Default', 'IFontDisp', 'Color', 'FONTSTRIKETHROUGH',
    'OLE_YPOS_CONTAINER', 'IFont', 'typelib_path', 'Library'
]

