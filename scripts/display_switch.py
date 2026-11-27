"""Move only the run's bound Codex window between attached displays, without activation."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess

import powershell_host
import run_safety
import virtual_display
from windows_process import hidden_options, decode_output

SWP_PASSIVE = 0x0004 | 0x0010 | 0x0200  # NOZORDER | NOACTIVATE | NOOWNERZORDER
SW_RESTORE = 9
SW_MAXIMIZE = 3


class MonitorInfo(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('bounds', wintypes.RECT),
                ('work', wintypes.RECT), ('flags', wintypes.DWORD),
                ('device', wintypes.WCHAR * 32)]


def rectangle(rect):
    return (rect.left, rect.top, rect.right, rect.bottom)


class NativeDisplays:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('屏幕切换仅支持 Windows。')
        self.api = ctypes.WinDLL('user32', use_last_error=True)
        self.api.SetThreadDpiAwarenessContext.argtypes=(wintypes.HANDLE,)
        self.api.SetThreadDpiAwarenessContext.restype=wintypes.HANDLE
        self.api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE,
                                               wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        self.api.EnumDisplayMonitors.argtypes = (wintypes.HDC, ctypes.POINTER(wintypes.RECT), self.callback_type, wintypes.LPARAM)
        self.api.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
        self.api.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
        self.api.MonitorFromWindow.restype = wintypes.HANDLE
        self.api.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        self.api.GetWindowRect.restype = wintypes.BOOL
        self.api.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        self.api.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, wintypes.UINT)
        self.api.IsIconic.argtypes = (wintypes.HWND,)
        self.api.IsZoomed.argtypes = (wintypes.HWND,)
        self.api.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)

    def monitors(self):
        result = []
        errors = []
        @self.callback_type
        def visit(handle, _dc, _rect, _data):
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            if not self.api.GetMonitorInfoW(handle, ctypes.byref(info)):
                errors.append(ctypes.get_last_error())
                return False
            result.append(dict(handle=int(handle), device=info.device, primary=bool(info.flags & 1),
                               bounds=rectangle(info.bounds), work=rectangle(info.work)))
            return True
        if not self.api.EnumDisplayMonitors(None, None, visit, 0) or errors:
            raise OSError('无法读取当前显示器。')
        return result

    def monitor_for_window(self, hwnd):
        return int(self.api.MonitorFromWindow(hwnd, 2) or 0)

    def window_pid(self, hwnd):
        pid = wintypes.DWORD()
        if not self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)):
            raise OSError('绑定的 Codex 窗口已关闭，请重新绑定。')
        return pid.value

    def move(self, hwnd, rect):
        if self.api.IsIconic(hwnd):
            raise ValueError('Codex 窗口已最小化，请先手动还原窗口。')
        left, top, right, bottom = rect
        zoomed = bool(self.api.IsZoomed(hwnd))
        if zoomed:
            # SetWindowPos on a maximized window only changes its restore
            # rectangle; Windows keeps it maximized on the old monitor.
            self.api.ShowWindow(hwnd, SW_RESTORE)
        try:
            if not self.api.SetWindowPos(hwnd, None, left, top, right-left, bottom-top, SWP_PASSIVE):
                raise OSError(ctypes.get_last_error(), '窗口移动失败。')
            current = wintypes.RECT()
            if (self.api.GetWindowRect(hwnd, ctypes.byref(current)) and
                    (current.left, current.top, current.right, current.bottom) != (left, top, right, bottom)):
                if not self.api.SetWindowPos(hwnd, None, left, top, right-left, bottom-top, SWP_PASSIVE):
                    raise OSError(ctypes.get_last_error(), '窗口移动失败。')
        finally:
            if zoomed:
                self.api.ShowWindow(hwnd, SW_MAXIMIZE)


def primary_monitor(monitors):
    primary = [item for item in monitors if item['primary']]
    if len(primary) != 1:
        raise ValueError('无法确定唯一主屏，请检查 Windows 显示设置。')
    return primary[0]


def destination(monitors, current, preferred=None):
    primary = primary_monitor(monitors)
    if current != primary['handle']:
        return primary
    secondary = [item for item in monitors if not item['primary']]
    if not secondary:
        raise ValueError('未检测到已启用的副屏，请先连接显示器或启用虚拟副屏。')
    return next((item for item in secondary if item['device'] == preferred),
                sorted(secondary, key=lambda item: item['device'])[0])


def remember_binding(db, run_id, path):
    path = Path(path).resolve()
    binding = json.loads(path.read_text(encoding='utf-8-sig'))
    if binding.get('browser_target') != 'codex_iab' or not binding.get('hwnd') or not binding.get('chat_title'):
        raise ValueError('invalid_codex_iab_binding')
    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',
               ('boss_browser_binding/'+run_id, json.dumps(dict(path=str(path), binding_id=binding.get('binding_id')))))


def saved_binding(db, run_id):
    row = db.execute('SELECT value FROM settings WHERE key=?', ('boss_browser_binding/'+run_id,)).fetchone()
    if not row:
        raise ValueError('本轮尚未绑定 BOSS 窗口，请启动本轮执行器后重试。')
    saved = json.loads(row[0])
    path = Path(saved['path'])
    binding = json.loads(path.read_text(encoding='utf-8-sig'))
    if not saved.get('binding_id') or binding.get('binding_id') != saved['binding_id']:
        raise ValueError('BOSS 窗口绑定已改变，请重新启动本轮执行器。')
    return path,binding


def button_state(db,run_id,native=None):
    native=native or NativeDisplays()
    _,binding=saved_binding(db,run_id)
    hwnd=int(binding['hwnd'])
    if native.window_pid(hwnd)!=int(binding['process_id']):
        raise ValueError('绑定的 Codex 窗口已改变。')
    primary=primary_monitor(native.monitors())
    if native.monitor_for_window(hwnd)==primary['handle']:
        return dict(label='副屏',color='yellow')
    return dict(label='主屏',color='green')


def bound_window(db, run_id):
    path,binding=saved_binding(db,run_id)
    result = subprocess.run(powershell_host.command(Path(__file__).with_name('probe-boss-window.ps1')),
        capture_output=True, timeout=12, env={**os.environ, 'BOSS_BROWSER_BINDING':str(path)}, **hidden_options())
    if result.returncode:
        raise ValueError('无法核验本轮 Codex/BOSS 窗口：'+decode_output(result.stderr)[-400:])
    receipt = json.loads(decode_output(result.stdout))
    if receipt.get('state') != 'bound' or receipt.get('binding_id') != binding['binding_id']:
        raise ValueError('BOSS 窗口核验失败，请重新绑定。')
    return receipt


def toggle(db, run_id, native=None):
    native = native or NativeDisplays()
    binding = bound_window(db, run_id)
    with run_safety.action_lock(db):
        hwnd = int(binding['hwnd'])
        if native.window_pid(hwnd) != int(binding['process_id']):
            raise ValueError('绑定的 Codex 窗口已改变，未移动其他窗口。')
        monitors = native.monitors()
        if len(virtual_display.physical_monitors(monitors)) >= 2:
            virtual_display.release_all()
            monitors = native.monitors()
        row = db.execute('SELECT value FROM settings WHERE key=?', ('secondary_display/'+run_id,)).fetchone()
        current=native.monitor_for_window(hwnd)
        source=next((item for item in monitors if item['handle']==current),None)
        primary = primary_monitor(monitors)
        if current == primary['handle'] and len(virtual_display.physical_monitors(monitors)) < 2:
            started = virtual_display.ensure(db, run_id, hwnd, native)
            monitors = native.monitors()
            target = next((item for item in monitors if item['device'] == started.get('device')), None)
            if target is None:
                raise ValueError('虚拟副屏已启动但未找到目标屏幕，请检查 Windows 显示设置。')
        else:
            target = destination(monitors, current, row[0] if row else None)
        native.move(hwnd, target['work'])
        if native.monitor_for_window(hwnd) != target['handle']:
            raise ValueError('尚未确认窗口已移至目标屏幕，请检查显示设置。')
        if not target['primary']:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('secondary_display/'+run_id, target['device']))
        elif source and not source['primary']:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('secondary_display/'+run_id, source['device']))
            if virtual_display.is_virtual_device(source['device']):
                virtual_display.after_return(db, run_id, hwnd, native)
        return dict(state='moved', display='主屏' if target['primary'] else '副屏', device=target['device'], hwnd=hwnd)
