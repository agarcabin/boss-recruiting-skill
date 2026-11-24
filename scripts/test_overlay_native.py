"""Opt-in native overlay smoke check, using synthetic data and an isolated database."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import tempfile
import time
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch

import display_switch
import powershell_host
import progress_window


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview',type=Path)
    parser.add_argument('--secondary',action='store_true',help='Preview the destination button while Codex is on secondary.')
    args=parser.parse_args()
    progress_window.enable_dpi_awareness()
    native=display_switch.NativeDisplays()
    native.api.GetForegroundWindow.restype=ctypes.c_void_p
    foreground=native.api.GetForegroundWindow()
    data=dict(state='running',elapsed='00:02:16',current_step='正在读取电子简历 · 演示数据',
              current=3,remaining_minutes=5,daily_judged=8,daily_resume_viewed=5,daily_sent=3,
              viewing_average_seconds=27.2)
    with tempfile.TemporaryDirectory(prefix='recruiting-overlay-qa-') as folder:
        root=progress_window.create_overlay_root()
        after_tk=native.api.GetForegroundWindow()
        try:
            with patch.object(progress_window.ProgressWindow,'read',return_value=data):
                window=progress_window.ProgressWindow(root,Path(folder)/'isolated.sqlite3','demo',Path(folder),demo=True)
                if args.secondary:
                    window.display_button=dict(label='主屏',color='green')
                    window.refresh()
                root.update()
                if getattr(root,'last_error',None):raise AssertionError(root.last_error)
                primary=display_switch.primary_monitor(native.monitors())
                for widget in (root,window.button_window):
                    handle=progress_window.wintypes.HWND(progress_window._top_level_handle(widget))
                    if not native.api.IsWindowEnabled(handle) or not native.api.IsWindowVisible(handle):
                        raise AssertionError('overlay_not_visible_or_still_disabled')
                    if native.monitor_for_window(handle)!=primary['handle']:
                        raise AssertionError('overlay_not_on_primary')
                if native.api.GetForegroundWindow()!=foreground:
                    raise AssertionError(f'overlay_creation_stole_focus: before={foreground} after_tk={after_tk} current={native.api.GetForegroundWindow()} root={progress_window._top_level_handle(root)} buttons={progress_window._top_level_handle(window.button_window)}')
                expected_label='主屏' if args.secondary else '副屏'
                expected_color='green' if args.secondary else 'yellow'
                if window.button_canvas.itemcget(window.button_texts[3],'text')!=expected_label:
                    raise AssertionError('screen_toggle_missing')
                if window.button_canvas.itemcget(window.button_rects[3],'fill')!=progress_window.DISPLAY_BUTTON_COLORS[expected_color][0]:
                    raise AssertionError('destination_color_mismatch')
                # Exercise the real native button route and timer, without physical input.
                if hasattr(root,'native_hwnd'):
                    user=native.api
                    user.SendMessageW.argtypes=(progress_window.wintypes.HWND,progress_window.wintypes.UINT,progress_window.wintypes.WPARAM,progress_window.wintypes.LPARAM)
                    user.SendMessageW.restype=ctypes.c_ssize_t
                    handle=window.button_window.native_hwnd
                    if user.SendMessageW(handle,0x0021,root.native_hwnd,(0x0201<<16)|1)!=3:
                        raise AssertionError('button_mouse_activation_not_blocked')
                    geometry=progress_window.button_geometry(window.ui_scale)
                    x=round(progress_window.STATUS_WIDTH/window.ui_scale)+geometry['x']+sum(geometry['widths'][:3])+geometry['gap']*3+geometry['widths'][3]//2
                    y=geometry['y']+geometry['height']//2
                    point=(y<<16)|x
                    user.SendMessageW(handle,0x0200,0,point)
                    user.SendMessageW(handle,0x0201,1,point)
                    user.SendMessageW(handle,0x0202,0,point)
                    if not window.display_notice.startswith('演示模式'):
                        raise AssertionError('native_button_callback_not_dispatched')
                    fired=[];root.after(10,lambda:fired.append(True))
                    deadline=time.monotonic()+1
                    while not fired and time.monotonic()<deadline:root.update();time.sleep(.002)
                    if not fired or root.last_error:raise AssertionError(root.last_error or 'native_timer_not_dispatched')
                    if native.api.GetForegroundWindow()!=foreground:raise AssertionError('native_button_or_timer_stole_focus')
                    window.display_notice_until=0
                    window.refresh();root.update()
                if args.preview:
                    args.preview.parent.mkdir(parents=True,exist_ok=True)
                    left=root.winfo_rootx();top=root.winfo_rooty()
                    width=root.winfo_width();height=root.winfo_height()
                    target=str(args.preview.resolve()).replace("'","''")
                    code=("Add-Type -AssemblyName System.Drawing; "
                          'Add-Type \'using System;using System.Runtime.InteropServices;public static class OverlayQaDpi{[DllImport("user32.dll")]public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr v);[DllImport("user32.dll")]public static extern IntPtr GetDC(IntPtr h);[DllImport("user32.dll")]public static extern int ReleaseDC(IntPtr h,IntPtr dc);[DllImport("gdi32.dll")]public static extern bool BitBlt(IntPtr d,int x,int y,int w,int h,IntPtr s,int sx,int sy,uint op);}\';'
                          '[void][OverlayQaDpi]::SetThreadDpiAwarenessContext([IntPtr](-4));'
                          f"$b=[Drawing.Bitmap]::new({width},{height});$g=[Drawing.Graphics]::FromImage($b);"
                          '$src=[OverlayQaDpi]::GetDC([IntPtr]::Zero);$dst=$g.GetHdc();'
                          f"try {{if(![OverlayQaDpi]::BitBlt($dst,0,0,{width},{height},$src,{left},{top},0x40CC0020)){{throw 'preview_capture_failed'}}}}"
                          'finally {$g.ReleaseHdc($dst);[void][OverlayQaDpi]::ReleaseDC([IntPtr]::Zero,$src)};'
                          f"try {{$b.Save('{target}',[Drawing.Imaging.ImageFormat]::Png)}}"
                          "finally {$g.Dispose();$b.Dispose()}")
                    command=powershell_host.command(Path(__file__).with_name('test_display_native.ps1'))
                    command=command[:command.index('-File')]+['-Command',code]
                    subprocess.run(command,check=True,capture_output=True,timeout=20)
                closed=[]
                finished=SimpleNamespace(termination_result=(Path(folder)/'report.xlsx',None),demo=True,
                    root=SimpleNamespace(destroy=lambda:closed.append(True)))
                def confirm_after_close(*_args,**_kwargs):
                    if not closed:raise AssertionError('report_prompt_preceded_overlay_close')
                    return False
                with patch.object(progress_window.messagebox,'askyesno',side_effect=confirm_after_close):
                    progress_window.ProgressWindow.finish_termination(finished)
                print(json.dumps(dict(state='passed',buttons=4,primary_overlay=True,focus_preserved=True,close_before_prompt=True),ensure_ascii=False))
        finally:root.destroy()


if __name__=='__main__':main()
