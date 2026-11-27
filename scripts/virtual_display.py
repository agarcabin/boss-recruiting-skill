"""On-demand virtual secondary display for single-monitor Windows hosts.

Windows has no user-mode API that creates a monitor. This module drives the
signed Parsec IddCx driver: it plugs a virtual display, extends the desktop to
the right of the primary monitor, and keeps the driver alive with a 50ms ping.
Physical secondary monitors always win; the virtual display is never created
when a real second screen is active.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
import uuid
from ctypes import wintypes
from pathlib import Path

import ledger
import powershell_host
from windows_process import hidden_options

VDD_GUID_TEXT = "00b41627-04c4-429e-a26e-0265cf50c8fa"
IOCTL_ADD, IOCTL_REMOVE, IOCTL_UPDATE, IOCTL_VERSION = 0x0022E004, 0x0022A008, 0x0022A00C, 0x0022E010
INSTALLER_NAME = "parsec-vdd-0.41.0.0.exe"
INSTALLER_URLS = (
    "https://github.com/HaliComing/parsec-vdd-cli/releases/download/v1.0/" + INSTALLER_NAME,
    "https://gh-proxy.com/https://github.com/HaliComing/parsec-vdd-cli/releases/download/v1.0/" + INSTALLER_NAME,
)
INSTALLER_SHA256 = "317977c5abd58f1c3f7b27ef7f96947efd07e6d35b27e415cea5daa6007629b1"
FAST_MS = 1000
PERSISTENT_MS = 10000
SESSION_IDLE_SECONDS = 300
PERSISTENT_IDLE_SECONDS = 1800
VIRTUAL_NAMES = ("parsec", "gameviewer", "virtual", "idd", "remote", "spacedesk")


class VirtualDisplayError(RuntimeError):
    pass


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("InterfaceClassGuid", GUID),
                ("Flags", wintypes.DWORD), ("Reserved", ctypes.c_void_p)]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p),
                ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD),
                ("hEvent", wintypes.HANDLE)]


class DISPLAY_DEVICE(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32),
                ("DeviceString", wintypes.WCHAR * 128), ("StateFlags", wintypes.DWORD),
                ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG), ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", wintypes.SHORT), ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT), ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT), ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD),
    ]


ENUM_CURRENT_SETTINGS = 0xFFFFFFFF
DM_PELSWIDTH, DM_PELSHEIGHT, DM_DISPLAYFREQUENCY = 0x00080000, 0x00100000, 0x00400000
CDS_UPDATEREGISTRY = 0x00000001


VDD_GUID = GUID.from_buffer_copy(uuid.UUID(VDD_GUID_TEXT).bytes_le)
_setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32 = ctypes.WinDLL("user32", use_last_error=True)

_setupapi.SetupDiGetClassDevsW.argtypes = (ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD)
_setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
_setupapi.SetupDiEnumDeviceInterfaces.argtypes = (wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID),
                                                 wintypes.DWORD, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA))
_setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
_setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = (wintypes.HANDLE, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
                                                       ctypes.c_void_p, wintypes.DWORD,
                                                       ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
_setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
_setupapi.SetupDiDestroyDeviceInfoList.argtypes = (wintypes.HANDLE,)
_setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

_kernel32.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
_kernel32.CreateFileW.restype = wintypes.HANDLE
_kernel32.DeviceIoControl.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                      ctypes.POINTER(OVERLAPPED))
_kernel32.DeviceIoControl.restype = wintypes.BOOL
_kernel32.GetOverlappedResult.argtypes = (wintypes.HANDLE, ctypes.POINTER(OVERLAPPED),
                                          ctypes.POINTER(wintypes.DWORD), wintypes.BOOL)
_kernel32.GetOverlappedResult.restype = wintypes.BOOL
_kernel32.CreateEventW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR)
_kernel32.CreateEventW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

_user32.EnumDisplayDevicesW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD,
                                        ctypes.POINTER(DISPLAY_DEVICE), wintypes.DWORD)
_user32.EnumDisplayDevicesW.restype = wintypes.BOOL
_user32.EnumDisplaySettingsW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW))
_user32.EnumDisplaySettingsW.restype = wintypes.BOOL
_user32.ChangeDisplaySettingsExW.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(DEVMODEW),
                                             wintypes.HWND, wintypes.DWORD, ctypes.c_void_p)
_user32.ChangeDisplaySettingsExW.restype = wintypes.LONG

_session = None
_session_lock = threading.Lock()


def _open_device():
    info = _setupapi.SetupDiGetClassDevsW(ctypes.byref(VDD_GUID), None, None, 0x12)
    if info in (None, -1):
        raise VirtualDisplayError("virtual_display_driver_missing")
    try:
        index = 0
        while True:
            interface = SP_DEVICE_INTERFACE_DATA()
            interface.cbSize = ctypes.sizeof(interface)
            if not _setupapi.SetupDiEnumDeviceInterfaces(info, None, ctypes.byref(VDD_GUID), index,
                                                        ctypes.byref(interface)):
                raise VirtualDisplayError("virtual_display_driver_unavailable")
            index += 1
            size = wintypes.DWORD()
            _setupapi.SetupDiGetDeviceInterfaceDetailW(info, ctypes.byref(interface), None, 0,
                                                       ctypes.byref(size), None)
            buffer = ctypes.create_string_buffer(size.value)
            ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if not _setupapi.SetupDiGetDeviceInterfaceDetailW(info, ctypes.byref(interface), buffer, size.value,
                                                              ctypes.byref(size), None):
                continue
            path = ctypes.wstring_at(ctypes.addressof(buffer) + 4)
            handle = _kernel32.CreateFileW(path, 0xC0000000, 3, None, 3, 0xE0000080, None)
            if handle not in (None, -1, wintypes.HANDLE(-1).value):
                return handle, path
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(info)
    raise VirtualDisplayError("virtual_display_driver_inaccessible")


def _ioctl(handle, code, data=b""):
    in_buffer = ctypes.create_string_buffer(32)
    if data:
        ctypes.memmove(in_buffer, data, min(len(data), 32))
    out = wintypes.DWORD()
    overlapped = OVERLAPPED()
    event = _kernel32.CreateEventW(None, False, False, None)
    overlapped.hEvent = event
    try:
        ok = _kernel32.DeviceIoControl(handle, code, in_buffer, 32, ctypes.byref(out), 4, None,
                                       ctypes.byref(overlapped))
        if not ok:
            error = ctypes.get_last_error()
            if error != 997:
                raise VirtualDisplayError(f"virtual_display_ioctl_failed:{error}")
        transferred = wintypes.DWORD()
        _kernel32.GetOverlappedResult(handle, ctypes.byref(overlapped), ctypes.byref(transferred), True)
        return out.value
    finally:
        _kernel32.CloseHandle(event)


def driver_status():
    try:
        handle, _ = _open_device()
    except (OSError, VirtualDisplayError):
        return dict(installed=False)
    try:
        return dict(installed=True, version=_ioctl(handle, IOCTL_VERSION))
    finally:
        _kernel32.CloseHandle(handle)


def adapter_names():
    result = {}
    index = 0
    while True:
        device = DISPLAY_DEVICE()
        device.cb = ctypes.sizeof(device)
        if not _user32.EnumDisplayDevicesW(None, index, ctypes.byref(device), 0):
            break
        index += 1
        if device.StateFlags & 0x1:
            result[device.DeviceName] = device.DeviceString
    return result


def is_virtual_device(device):
    name = str(adapter_names().get(device, "")).lower()
    return any(word in name for word in VIRTUAL_NAMES)


def physical_monitors(monitors):
    names = adapter_names()
    return [item for item in monitors
            if not any(word in str(names.get(item["device"], "")).lower() for word in VIRTUAL_NAMES)]


def _wait_monitor(native, predicate, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        monitors = native.monitors()
        match = [item for item in monitors if predicate(item)]
        if match:
            return match[0], monitors
        time.sleep(0.02)
    return None, native.monitors()


def _wait_no_virtual(native, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(is_virtual_device(item["device"]) for item in native.monitors()):
            return True
        time.sleep(0.05)
    return False


def _primary(monitors):
    primary = [item for item in monitors if item["primary"]]
    if len(primary) != 1:
        raise VirtualDisplayError("virtual_display_primary_not_unique")
    return primary[0]


def _right_of_primary(primary, monitor):
    left, top, _right, _bottom = monitor["bounds"]
    pleft, ptop, pright, _pbottom = primary["bounds"]
    return abs(top - ptop) <= 2 and left >= pright - 4 and left > pleft


def _devmode(device, index):
    value = DEVMODEW()
    value.dmSize = ctypes.sizeof(value)
    if not _user32.EnumDisplaySettingsW(device, index, ctypes.byref(value)):
        return None
    return value


def _best_mode(device, width, height):
    exact = []
    same_ratio = []
    index = 0
    while True:
        mode = _devmode(device, index)
        if mode is None:
            break
        index += 1
        if mode.dmPelsWidth == width and mode.dmPelsHeight == height:
            exact.append((mode.dmDisplayFrequency, mode.dmPelsWidth, mode.dmPelsHeight))
        elif abs((mode.dmPelsWidth / max(1, mode.dmPelsHeight)) - (width / max(1, height))) < 0.02:
            same_ratio.append((mode.dmPelsWidth * mode.dmPelsHeight,
                               mode.dmDisplayFrequency, mode.dmPelsWidth, mode.dmPelsHeight))
    if exact:
        frequency, w, h = max(exact)
        return w, h, frequency
    if same_ratio:
        _area, frequency, w, h = max(same_ratio)
        return w, h, frequency
    return None


def _match_primary_mode(device, primary):
    width = primary["bounds"][2] - primary["bounds"][0]
    height = primary["bounds"][3] - primary["bounds"][1]
    current = _devmode(device, ENUM_CURRENT_SETTINGS)
    if current is None:
        return dict(changed=False, reason="mode_unreadable")
    if current.dmPelsWidth == width and current.dmPelsHeight == height:
        return dict(changed=False, width=width, height=height, frequency=current.dmDisplayFrequency)
    best = _best_mode(device, width, height)
    if best is None:
        return dict(changed=False, reason="mode_unsupported", width=current.dmPelsWidth,
                    height=current.dmPelsHeight)
    target_width, target_height, frequency = best
    mode = _devmode(device, ENUM_CURRENT_SETTINGS)
    mode.dmPelsWidth = target_width
    mode.dmPelsHeight = target_height
    mode.dmDisplayFrequency = frequency
    mode.dmFields |= DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFREQUENCY
    result = _user32.ChangeDisplaySettingsExW(device, ctypes.byref(mode), None, CDS_UPDATEREGISTRY, None)
    return dict(changed=result == 0, result=result, width=target_width, height=target_height,
                frequency=frequency)


class _Session:
    def __init__(self, native, hwnd):
        self.native = native
        self.hwnd = hwnd
        self.handle, self.path = _open_device()
        self.index = None
        self.device = ""
        self.mode = "fast"
        self.startup_ms = None
        self.last_used = time.monotonic()
        self.stop = threading.Event()
        self.pinger = threading.Thread(target=self._ping, daemon=True)
        self.pinger.start()
        self.watchdog = threading.Thread(target=self._watch, daemon=True)
        self.watchdog.start()

    def _ping(self):
        while not self.stop.is_set():
            try:
                _ioctl(self.handle, IOCTL_UPDATE)
            except (OSError, VirtualDisplayError):
                pass
            self.stop.wait(0.05)

    def _watch(self):
        while not self.stop.is_set():
            self.stop.wait(5)
            if self.stop.is_set() or self.index is None or self.mode == "fast":
                continue
            idle = SESSION_IDLE_SECONDS if self.mode == "session" else PERSISTENT_IDLE_SECONDS
            if time.monotonic() - self.last_used < idle:
                continue
            try:
                primary = _primary(self.native.monitors())
                if self.native.monitor_for_window(self.hwnd) == primary["handle"]:
                    self.release()
            except (OSError, ValueError):
                continue
            return

    def touch(self):
        self.last_used = time.monotonic()

    def start(self):
        if self.index is not None:
            self.touch()
            return dict(state="reused", device=self.device, startup_ms=self.startup_ms, mode=self.mode)
        primary = _primary(self.native.monitors())
        first_start = time.perf_counter()
        self.index = _ioctl(self.handle, IOCTL_ADD)
        subprocess.run(["DisplaySwitch.exe", "/extend"], capture_output=True, timeout=15,
                       **hidden_options())
        monitor, monitors = _wait_monitor(self.native,
                                          lambda item: not item["primary"] and is_virtual_device(item["device"]),
                                          20)
        elapsed = (time.perf_counter() - first_start) * 1000
        if monitor is None:
            self.release()
            raise VirtualDisplayError("virtual_display_monitor_not_detected")
        mode = _match_primary_mode(monitor["device"], primary)
        if mode.get("changed"):
            time.sleep(0.4)
            monitors = self.native.monitors()
            monitor = next((item for item in monitors if item["device"] == monitor["device"]), monitor)
        after_primary = _primary(monitors)
        if (after_primary["device"] != primary["device"] or
                after_primary["bounds"] != primary["bounds"]):
            self.release()
            raise VirtualDisplayError(
                "virtual_display_primary_changed:" +
                json.dumps(dict(before=primary, after=after_primary), ensure_ascii=False))
        if not _right_of_primary(primary, monitor):
            self.release()
            raise VirtualDisplayError("virtual_display_not_right_of_primary")
        self.device = monitor["device"]
        self.startup_ms = elapsed
        return dict(state="started", device=self.device, startup_ms=elapsed, mode=self.mode,
                    monitor=monitor, primary=primary, display_mode=mode)

    def release(self):
        if self.stop.is_set():
            return
        self.stop.set()
        try:
            if self.index is not None:
                _ioctl(self.handle, IOCTL_REMOVE, int(self.index).to_bytes(2, "big"))
        except (OSError, VirtualDisplayError):
            pass
        try:
            _kernel32.CloseHandle(self.handle)
        except OSError:
            pass
        self.index = None
        self.device = ""
        _wait_no_virtual(self.native, 6)


def _mode_for(startup_ms):
    if startup_ms < FAST_MS:
        return "fast"
    if startup_ms >= PERSISTENT_MS:
        return "persistent"
    return "session"


def _stored_startup(db):
    row = db.execute("SELECT value FROM settings WHERE key='virtual_display/startup_ms'").fetchone()
    try:
        return float(row[0]) if row and row[0] is not None else None
    except (TypeError, ValueError):
        return None


def _remember_startup(db, value):
    db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)",
               ("virtual_display/startup_ms", str(round(value))))
    db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)",
               ("virtual_display/mode", _mode_for(value)))
    db.commit()


def _ensure_driver():
    status = driver_status()
    if status["installed"]:
        return status
    target_dir = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Codex" / "recruiting-greetings" / "vdd"
    target = target_dir / INSTALLER_NAME
    bundled = Path(__file__).resolve().parents[1] / "runtime" / "vdd" / INSTALLER_NAME
    downloaded = False
    if bundled.is_file():
        target = bundled
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        last_error = None
        for url in INSTALLER_URLS:
            try:
                urllib.request.urlretrieve(url, target)
                downloaded = True
                last_error = None
                break
            except (OSError, ValueError) as exc:
                last_error = exc
        if last_error is not None:
            raise VirtualDisplayError("virtual_display_driver_download_failed") from last_error
    if hashlib.sha256(target.read_bytes()).hexdigest().lower() != INSTALLER_SHA256:
        if downloaded:
            target.unlink(missing_ok=True)
        raise VirtualDisplayError("virtual_display_driver_checksum_mismatch")
    verify = (
        "$s=Get-AuthenticodeSignature -LiteralPath '" + str(target).replace("'", "''") + "';"
        "if($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Parsec Cloud')"
        "{throw 'virtual_display_driver_signature_invalid'}"
    )
    checked = subprocess.run(["powershell.exe", "-NoProfile", "-Command", verify],
                             capture_output=True, text=True, timeout=30, **hidden_options())
    if checked.returncode:
        raise VirtualDisplayError("virtual_display_driver_signature_invalid")
    install = (
        "Start-Process -FilePath '" + str(target).replace("'", "''") + "' "
        "-ArgumentList '/S' -Verb RunAs -Wait"
    )
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-Command", install], timeout=240,
                       capture_output=True, **hidden_options())
    except (OSError, subprocess.SubprocessError) as exc:
        raise VirtualDisplayError("virtual_display_driver_install_cancelled") from exc
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status = driver_status()
        if status["installed"]:
            return status
        time.sleep(0.5)
    raise VirtualDisplayError("virtual_display_driver_not_ready")

def ensure(db, run_id, hwnd, native=None):
    """Start or reuse the virtual display after a secondary-screen click."""
    global _session
    native = native or __import__("display_switch").NativeDisplays()
    monitors = native.monitors()
    if len(physical_monitors(monitors)) >= 2:
        return dict(state="physical")
    if any(is_virtual_device(item["device"]) for item in monitors):
        _wait_no_virtual(native, 2.5)
    with _session_lock:
        if _session is not None and _session.index is None:
            _session = None
        if _session is None:
            _ensure_driver()
            _session = _Session(native, hwnd)
        stored = _stored_startup(db)
        if stored is None:
            _session.start()
            _session.release()
            _session = _Session(native, hwnd)
            second = _session.start()
            stored = float(second["startup_ms"])
            _remember_startup(db, stored)
        else:
            _session.startup_ms = stored
        _session.mode = _mode_for(stored)
        _session.touch()
        result = _session.start()
        result["mode"] = _session.mode
        result["startup_ms"] = stored
        if "monitor" not in result:
            current = native.monitors()
            result["monitor"] = next(item for item in current if item["device"] == _session.device)
            result["primary"] = _primary(current)
        return result


def after_return(db, run_id, hwnd, native=None):
    """Called after the window moved back to the primary monitor."""
    global _session
    with _session_lock:
        if _session is None:
            return dict(state="stopped")
        _session.touch()
        if _session.mode == "fast":
            _session.release()
            _session = None
            return dict(state="stopped")
        return dict(state="kept", mode=_session.mode)


def release_all():
    global _session
    with _session_lock:
        if _session is not None:
            _session.release()
            _session = None
