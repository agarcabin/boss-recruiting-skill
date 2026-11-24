"""Watch transient foreground and edit focus changes during a detached overlay launch.

Only native handles/event codes are recorded. No input text is read or written.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import time
import tempfile

import launch_progress


class GuiThreadInfo(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('flags',wintypes.DWORD),
              ('active',wintypes.HWND),('focus',wintypes.HWND),('capture',wintypes.HWND),
              ('menu_owner',wintypes.HWND),('move_size',wintypes.HWND),('caret',wintypes.HWND),
              ('caret_rect',wintypes.RECT)]


def main():
    if os.name!='nt':raise RuntimeError('Windows required')
    api=ctypes.WinDLL('user32',use_last_error=True)
    api.GetForegroundWindow.restype=wintypes.HWND
    api.GetWindowThreadProcessId.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.DWORD))
    api.GetGUIThreadInfo.argtypes=(wintypes.DWORD,ctypes.POINTER(GuiThreadInfo))
    foreground=api.GetForegroundWindow()
    thread=api.GetWindowThreadProcessId(foreground,None)
    def state():
        info=GuiThreadInfo();info.size=ctypes.sizeof(info)
        if not api.GetGUIThreadInfo(thread,ctypes.byref(info)):raise OSError('GetGUIThreadInfo')
        return dict(foreground=api.GetForegroundWindow(),active=info.active,focus=info.focus,caret=info.caret)
    initial=state()
    events=[];transitions=[]
    callback_type=ctypes.WINFUNCTYPE(None,wintypes.HANDLE,wintypes.DWORD,wintypes.HWND,
                                  wintypes.LONG,wintypes.LONG,wintypes.DWORD,wintypes.DWORD)
    def observe(_hook,event,hwnd,obj,child,_thread,timestamp):
        pid=wintypes.DWORD()
        if hwnd:api.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        events.append(dict(event=event,hwnd=hwnd,pid=pid.value,obj=obj,child=child,at=timestamp,actual=state()))
    callback=callback_type(observe)
    api.SetWinEventHook.argtypes=(wintypes.DWORD,wintypes.DWORD,wintypes.HMODULE,callback_type,
                                 wintypes.DWORD,wintypes.DWORD,wintypes.DWORD)
    api.SetWinEventHook.restype=wintypes.HANDLE
    api.UnhookWinEvent.argtypes=(wintypes.HANDLE,)
    hooks=[api.SetWinEventHook(event,event,None,callback,0,0,0) for event in (3,0x8005)]
    if not all(hooks):raise OSError('SetWinEventHook')
    process=None
    try:
        logs=tempfile.TemporaryDirectory(prefix='overlay-focus-')
        log=Path(logs.name)/'child.log'
        code="import sys,runpy;sys.stdout=open(sys.argv[1],'w',encoding='utf-8',buffering=1);sys.stderr=sys.stdout;target=sys.argv[2];sys.path.insert(0,str(__import__('pathlib').Path(target).parent));sys.argv=[target];runpy.run_path(target,run_name='__main__')"
        process=launch_progress.launch_process([str(Path(sys.executable).with_name('pythonw.exe')),
            '-X','utf8','-c',code,str(log),str(Path(__file__).with_name('test_overlay_native.py'))])
        until=time.monotonic()+3
        previous=initial
        message=wintypes.MSG()
        while time.monotonic()<until:
            while api.PeekMessageW(ctypes.byref(message),None,0,0,1):
                api.TranslateMessage(ctypes.byref(message));api.DispatchMessageW(ctypes.byref(message))
            current=state()
            if current!=previous:
                transitions.append(current);previous=current
            time.sleep(.003)
        result=dict(initial=initial,final=state(),child_pid=process.pid,child_exit=process.poll(),
                    overlay_focus_events=[event for event in events if event['pid']==process.pid],transitions=transitions)
        print(json.dumps(result))
        print(log.read_text(encoding='utf-8') if log.exists() else 'child_log_missing')
        if any(event['actual']!=initial for event in result['overlay_focus_events']) or transitions or process.poll()!=0:
            raise SystemExit(1)
    finally:
        for hook in hooks:api.UnhookWinEvent(hook)
        if process and process.poll() is None:
            process.terminate();process.wait(timeout=5)
        if 'logs' in locals():logs.cleanup()


if __name__=='__main__':main()
