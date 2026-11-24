"""Small Win32 canvas host whose windows never activate, including their first show.

The progress controller keeps its existing canvas/scheduler API. Tk is not started
for the Windows overlay; explicit user dialogs may still use Tk separately.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes as w
import itertools
from types import SimpleNamespace


LRESULT=ctypes.c_ssize_t
WNDPROC=ctypes.WINFUNCTYPE(LRESULT,w.HWND,w.UINT,w.WPARAM,w.LPARAM)


class WindowClass(ctypes.Structure):
    _fields_=[('style',w.UINT),('proc',WNDPROC),('class_extra',ctypes.c_int),
              ('window_extra',ctypes.c_int),('instance',w.HINSTANCE),('icon',w.HICON),
              ('cursor',w.HANDLE),('background',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]


class PaintStruct(ctypes.Structure):
    _fields_=[('dc',w.HDC),('erase',w.BOOL),('rect',w.RECT),('restore',w.BOOL),
              ('update',w.BOOL),('reserved',ctypes.c_byte*32)]


class TrackMouse(ctypes.Structure):
    _fields_=[('size',w.DWORD),('flags',w.DWORD),('window',w.HWND),('hover',w.DWORD)]


def color(value):
    value=(value or '#000000').lstrip('#')
    return int(value[0:2],16)|(int(value[2:4],16)<<8)|(int(value[4:6],16)<<16)


class Api:
    def __init__(self):
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.gdi=ctypes.WinDLL('gdi32',use_last_error=True)
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        def define(dll,name,args,result):
            fn=getattr(dll,name);fn.argtypes=args;fn.restype=result
        for name,args,result in (
            ('RegisterClassW',[ctypes.POINTER(WindowClass)],w.ATOM),
            ('CreateWindowExW',[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,ctypes.c_void_p],w.HWND),
            ('DefWindowProcW',[w.HWND,w.UINT,w.WPARAM,w.LPARAM],LRESULT),
            ('ShowWindow',[w.HWND,ctypes.c_int],w.BOOL),
            ('DestroyWindow',[w.HWND],w.BOOL),('EnableWindow',[w.HWND,w.BOOL],w.BOOL),
            ('SetWindowTextW',[w.HWND,w.LPCWSTR],w.BOOL),
            ('SetWindowPos',[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT],w.BOOL),
            ('GetWindowRect',[w.HWND,ctypes.POINTER(w.RECT)],w.BOOL),
            ('GetClientRect',[w.HWND,ctypes.POINTER(w.RECT)],w.BOOL),
            ('ClientToScreen',[w.HWND,ctypes.POINTER(w.POINT)],w.BOOL),
            ('SetLayeredWindowAttributes',[w.HWND,w.DWORD,w.BYTE,w.DWORD],w.BOOL),
            ('SetTimer',[w.HWND,ctypes.c_size_t,w.UINT,ctypes.c_void_p],ctypes.c_size_t),
            ('KillTimer',[w.HWND,ctypes.c_size_t],w.BOOL),
            ('BeginPaint',[w.HWND,ctypes.POINTER(PaintStruct)],w.HDC),
            ('EndPaint',[w.HWND,ctypes.POINTER(PaintStruct)],w.BOOL),
            ('FillRect',[w.HDC,ctypes.POINTER(w.RECT),w.HBRUSH],ctypes.c_int),
            ('DrawTextW',[w.HDC,w.LPCWSTR,ctypes.c_int,ctypes.POINTER(w.RECT),w.UINT],ctypes.c_int),
            ('InvalidateRect',[w.HWND,ctypes.POINTER(w.RECT),w.BOOL],w.BOOL),
            ('UpdateWindow',[w.HWND],w.BOOL),
            ('TrackMouseEvent',[ctypes.POINTER(TrackMouse)],w.BOOL),
            ('LoadCursorW',[w.HINSTANCE,ctypes.c_void_p],w.HANDLE),
            ('SetCursor',[w.HANDLE],w.HANDLE),
            ('GetMessageW',[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT],ctypes.c_int),
            ('PeekMessageW',[ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT,w.UINT],w.BOOL),
            ('TranslateMessage',[ctypes.POINTER(w.MSG)],w.BOOL),
            ('DispatchMessageW',[ctypes.POINTER(w.MSG)],LRESULT),
        ):define(self.user,name,args,result)
        for name,args,result in (
            ('CreateSolidBrush',[w.DWORD],w.HBRUSH),
            ('CreatePen',[ctypes.c_int,ctypes.c_int,w.DWORD],w.HANDLE),
            ('SelectObject',[w.HDC,w.HANDLE],w.HANDLE),
            ('GetStockObject',[ctypes.c_int],w.HANDLE),
            ('DeleteObject',[w.HANDLE],w.BOOL),
            ('Rectangle',[w.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int],w.BOOL),
            ('Ellipse',[w.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int],w.BOOL),
            ('RoundRect',[w.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int],w.BOOL),
            ('SetTextColor',[w.HDC,w.DWORD],w.DWORD),('SetBkMode',[w.HDC,ctypes.c_int],ctypes.c_int),
            ('CreateFontW',[ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.LPCWSTR],w.HANDLE),
            ('CreateCompatibleDC',[w.HDC],w.HDC),
            ('CreateCompatibleBitmap',[w.HDC,ctypes.c_int,ctypes.c_int],w.HBITMAP),
            ('DeleteDC',[w.HDC],w.BOOL),
            ('BitBlt',[w.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HDC,ctypes.c_int,ctypes.c_int,w.DWORD],w.BOOL),
        ):define(self.gdi,name,args,result)
        define(self.kernel,'GetModuleHandleW',[w.LPCWSTR],w.HMODULE)
        self.windows={}
        self.class_name='CodexRecruitingPassiveOverlayV156'
        self.callback=WNDPROC(self.dispatch)
        self.instance=self.kernel.GetModuleHandleW(None)
        wc=WindowClass(0,self.callback,0,0,self.instance,None,self.user.LoadCursorW(None,ctypes.c_void_p(32512)),None,None,self.class_name)
        if not self.user.RegisterClassW(ctypes.byref(wc)):
            raise OSError(ctypes.get_last_error(),'RegisterClassW')

    def dispatch(self,hwnd,message,first,second):
        window=self.windows.get(int(hwnd))
        if message==0x0021:return 3  # WM_MOUSEACTIVATE -> MA_NOACTIVATE
        if window:
            try:
                result=window.on_message(message,first,second)
                if result is not None:return result
            except Exception as exc:
                window.root.last_error=str(exc)
        return self.user.DefWindowProcW(hwnd,message,first,second)


_api=None


class NativeRoot:
    def __init__(self,owner=None):
        global _api
        if _api is None:_api=Api()
        self.api=_api;self.root=owner.root if owner else self
        self.owner=owner;self.canvas=None;self.destroyed=False;self.close_action=None
        self.timers={};self.serial=itertools.count(1);self.alpha=1.0;self.key='#010203'
        self.last_error=None
        self.native_hwnd=self.api.user.CreateWindowExW(0x08080080,self.api.class_name,'',0x80000000,
            0,0,1,1,owner.native_hwnd if owner else None,None,self.api.instance,None)
        if not self.native_hwnd:raise OSError(ctypes.get_last_error(),'CreateWindowExW')
        self.api.windows[int(self.native_hwnd)]=self

    def make_toplevel(self):return NativeRoot(self)
    def make_canvas(self,**options):
        self.canvas=NativeCanvas(self,**options);return self.canvas
    def winfo_id(self):return int(self.native_hwnd)
    def _rect(self):
        rect=w.RECT();self.api.user.GetWindowRect(self.native_hwnd,ctypes.byref(rect));return rect
    def winfo_width(self):
        rect=w.RECT();self.api.user.GetClientRect(self.native_hwnd,ctypes.byref(rect));return rect.right
    def winfo_height(self):
        rect=w.RECT();self.api.user.GetClientRect(self.native_hwnd,ctypes.byref(rect));return rect.bottom
    def winfo_rootx(self):return self._rect().left
    def winfo_rooty(self):return self._rect().top
    def winfo_screenwidth(self):return self.api.user.GetSystemMetrics(0)
    def withdraw(self):self.api.user.ShowWindow(self.native_hwnd,0)
    def deiconify(self):self.api.user.ShowWindow(self.native_hwnd,4)
    def overrideredirect(self,*_):pass
    def configure(self,**_):pass
    def title(self,value):self.api.user.SetWindowTextW(self.native_hwnd,value)
    def attributes(self,name,value):
        if name=='-alpha':self.alpha=float(value)
        elif name=='-transparentcolor':self.key=value
        elif name=='-disabled':self.api.user.EnableWindow(self.native_hwnd,not value)
        self.api.user.SetLayeredWindowAttributes(self.native_hwnd,color(self.key),round(self.alpha*255),3)
    def geometry(self,value):
        import re
        match=re.fullmatch(r'(\d+)x(\d+)\+(-?\d+)\+(-?\d+)',value)
        if not match:raise ValueError('invalid_overlay_geometry')
        width,height,x,y=map(int,match.groups())
        self.api.user.SetWindowPos(self.native_hwnd,None,x,y,width,height,0x0014)
    def protocol(self,_name,action):self.close_action=action
    def after(self,milliseconds,action):
        token=next(self.serial)
        if not self.api.user.SetTimer(self.native_hwnd,token,max(1,int(milliseconds)),None):raise OSError('SetTimer')
        self.timers[token]=action;return token
    def after_cancel(self,token):
        self.api.user.KillTimer(self.native_hwnd,int(token));self.timers.pop(int(token),None)
    def update_idletasks(self):self.api.user.UpdateWindow(self.native_hwnd)
    def update(self):
        message=w.MSG()
        while self.api.user.PeekMessageW(ctypes.byref(message),None,0,0,1):
            if message.message==0x12:break
            self.api.user.TranslateMessage(ctypes.byref(message));self.api.user.DispatchMessageW(ctypes.byref(message))
    def mainloop(self):
        message=w.MSG()
        while not self.destroyed:
            result=self.api.user.GetMessageW(ctypes.byref(message),None,0,0)
            if result<0:raise OSError(ctypes.get_last_error(),'GetMessageW')
            if result==0:break
            self.api.user.TranslateMessage(ctypes.byref(message));self.api.user.DispatchMessageW(ctypes.byref(message))
    def destroy(self):
        if not self.destroyed:self.api.user.DestroyWindow(self.native_hwnd)
    def on_message(self,message,first,second):
        if message==0x0014:return 1  # WM_ERASEBKGND
        if message==0x000F:
            paint=PaintStruct();dc=self.api.user.BeginPaint(self.native_hwnd,ctypes.byref(paint))
            try:
                if self.canvas:self.canvas.paint(dc)
            finally:self.api.user.EndPaint(self.native_hwnd,ctypes.byref(paint))
            return 0
        if message==0x0113:
            self.api.user.KillTimer(self.native_hwnd,first)
            action=self.timers.pop(int(first),None)
            if action:action()
            return 0
        if message in (0x0200,0x0201,0x02A3) and self.canvas:
            self.canvas.mouse(message,ctypes.c_short(second & 0xffff).value,ctypes.c_short((second>>16)&0xffff).value)
            return 0
        if message==0x0010:
            if self.close_action:self.close_action()
            else:self.destroy()
            return 0
        if message==0x0002:
            self.destroyed=True
            self.api.windows.pop(int(self.native_hwnd),None)
            return 0
        return None


class NativeCanvas:
    def __init__(self,window,**options):
        self.window=window;self.items={};self.bindings={};self.serial=itertools.count(1)
        self.hovered=None;self.background=options.get('bg','#010203')
    def place(self,**_):pass
    def configure(self,**options):
        if 'cursor' in options:
            handle=self.window.api.user.LoadCursorW(None,ctypes.c_void_p(32649 if options['cursor']=='hand2' else 32512))
            self.window.api.user.SetCursor(handle)
    def add(self,kind,bounds,**options):
        token=next(self.serial);self.items[token]=dict(kind=kind,bounds=bounds,**options)
        self.invalidate();return token
    def create_polygon(self,points,**options):
        xs=points[::2];ys=points[1::2]
        return self.add('rounded',(min(xs),min(ys),max(xs),max(ys)),radius=points[0]-min(xs),**options)
    def create_rectangle(self,*bounds,**options):return self.add('rectangle',bounds,**options)
    def create_oval(self,*bounds,**options):return self.add('oval',bounds,**options)
    def create_text(self,x,y,**options):return self.add('text',(x,y,x,y),**options)
    def tag_bind(self,tag,event,action):self.bindings[tag,event]=action
    def itemconfigure(self,token,**options):self.items[token].update(options);self.invalidate()
    def itemcget(self,token,name):return self.items[token].get(name,'')
    def invalidate(self):self.window.api.user.InvalidateRect(self.window.native_hwnd,None,False)
    def mouse(self,message,x,y):
        tag=None
        for item in self.items.values():
            left,top,right,bottom=item['bounds']
            if item['kind']!='text' and left<=x<right and top<=y<bottom and item.get('tags'):
                tag=item['tags'][0];break
        event=SimpleNamespace(x=x,y=y,widget=self)
        if message==0x02A3:tag=None
        if tag!=self.hovered:
            action=self.bindings.get((self.hovered,'<Leave>'))
            if action:action(event)
            self.hovered=tag
            action=self.bindings.get((tag,'<Enter>'))
            if action:action(event)
        if message==0x0200:
            track=TrackMouse(ctypes.sizeof(TrackMouse),2,self.window.native_hwnd,0)
            self.window.api.user.TrackMouseEvent(ctypes.byref(track))
        if message==0x0201:
            action=self.bindings.get((tag,'<Button-1>'))
            if action:action(event)
    def paint(self,target):
        api=self.window.api;gdi=api.gdi;user=api.user
        width=self.window.winfo_width();height=self.window.winfo_height()
        if width<1 or height<1:return
        dc=gdi.CreateCompatibleDC(target);bitmap=gdi.CreateCompatibleBitmap(target,width,height)
        previous=gdi.SelectObject(dc,bitmap)
        try:
            area=w.RECT(0,0,width,height);brush=gdi.CreateSolidBrush(color(self.background))
            try:user.FillRect(dc,ctypes.byref(area),brush)
            finally:gdi.DeleteObject(brush)
            for item in self.items.values():self.draw(dc,item,width)
            gdi.BitBlt(target,0,0,width,height,dc,0,0,0x00CC0020)
        finally:
            gdi.SelectObject(dc,previous);gdi.DeleteObject(bitmap);gdi.DeleteDC(dc)
    def draw(self,dc,item,width):
        gdi=self.window.api.gdi;user=self.window.api.user
        left,top,right,bottom=[round(value) for value in item['bounds']]
        if item['kind']=='text':
            family,size,*style=item.get('font',('Microsoft YaHei UI',-11))
            font=gdi.CreateFontW(int(size),0,0,0,700 if 'bold' in style else 400,0,0,0,1,0,0,5,0,family)
            old=gdi.SelectObject(dc,font)
            try:
                gdi.SetBkMode(dc,1);gdi.SetTextColor(dc,color(item.get('fill')))
                text=str(item.get('text',''));line_height=abs(size)+6
                if item.get('anchor')=='w':rect=w.RECT(left,top-line_height//2,width-8,top+line_height//2);flags=0x20|0x04|0x8000
                else:
                    # Button text is centered inside the matching tagged rectangle.
                    tags=item.get('tags',())
                    shape=next((v for v in self.items.values() if v['kind']!='text' and tags and v.get('tags')==tags),None)
                    rect=w.RECT(*map(round,shape['bounds'])) if shape else w.RECT(left-50,top-20,left+50,top+20)
                    flags=0x01|0x04|(0x20 if '\n' not in text else 0x10)
                    if '\n' in text:rect.top+=max(0,(rect.bottom-rect.top-(text.count('\n')+1)*(abs(size)+3))//2)
                user.DrawTextW(dc,text,-1,ctypes.byref(rect),flags)
            finally:gdi.SelectObject(dc,old);gdi.DeleteObject(font)
            return
        brush=gdi.CreateSolidBrush(color(item.get('fill')))
        pen=gdi.CreatePen(0,max(1,round(item.get('width',1))),color(item.get('outline'))) if item.get('outline') else None
        old_brush=gdi.SelectObject(dc,brush);old_pen=gdi.SelectObject(dc,pen or gdi.GetStockObject(8))
        try:
            if item['kind']=='rounded':
                radius=max(1,round(item.get('radius',12)*2));gdi.RoundRect(dc,left,top,right,bottom,radius,radius)
            elif item['kind']=='oval':gdi.Ellipse(dc,left,top,right,bottom)
            else:gdi.Rectangle(dc,left,top,right,bottom)
        finally:
            gdi.SelectObject(dc,old_pen);gdi.SelectObject(dc,old_brush)
            if pen:gdi.DeleteObject(pen)
            gdi.DeleteObject(brush)
