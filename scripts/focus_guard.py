"""Defer background UIA actions while the user is still typing."""
from __future__ import annotations

import ctypes
import json
import os
import time
from ctypes import wintypes
from pathlib import Path


DEFAULT_QUIET_SECONDS = 3.0
DEFAULT_TIMEOUT_SECONDS = 20.0
ENABLED = True
COMPOSITION_CLASS_HINTS = (
    "composition",
    "msctfime",
    "sogou",
    "sopy",
    "qqpy",
    "baidu",
    "iflytek",
    "rime",
    "weasel",
)
COMPOSITION_TITLE_HINTS = ("candidate", "候选")


class UserTyping(RuntimeError):
    pass


if os.name == "nt":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    _user32.EnumWindows.restype = wintypes.BOOL
    _user32.IsWindowVisible.argtypes = [wintypes.HWND]
    _user32.IsWindowVisible.restype = wintypes.BOOL
    _user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetClassNameW.restype = ctypes.c_int
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _user32.GetWindowTextW.restype = ctypes.c_int
else:
    _user32 = None


def _bound_window() -> int:
    path = os.environ.get("BOSS_BROWSER_BINDING")
    if not path:
        return 0
    try:
        binding = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return int(binding.get("hwnd") or 0)
    except (OSError, TypeError, ValueError):
        return 0


def _foreground_window() -> int:
    if _user32 is None:
        return 0
    return int(_user32.GetForegroundWindow() or 0)


def _composition_visible() -> bool:
    if _user32 is None:
        return False
    found = False
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def inspect(hwnd, _lparam):
        nonlocal found
        if not _user32.IsWindowVisible(hwnd):
            return True
        class_name = ctypes.create_unicode_buffer(256)
        title = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, class_name, len(class_name))
        _user32.GetWindowTextW(hwnd, title, len(title))
        class_text = class_name.value.casefold()
        title_text = title.value.casefold()
        if any(hint in class_text for hint in COMPOSITION_CLASS_HINTS) or any(
            hint in title_text for hint in COMPOSITION_TITLE_HINTS
        ):
            found = True
            return False
        return True

    callback = callback_type(inspect)
    _user32.EnumWindows(callback, 0)
    return found


def wait_for_safe(
    *,
    quiet_seconds: float | None = None,
    timeout_seconds: float | None = None,
    foreground=None,
    last_input_age=None,
    composition_visible=None,
    clock=None,
    sleep=None,
) -> dict:
    """Only defer while an input-method candidate window is visible."""
    if not ENABLED:
        return dict(state="disabled", waited_seconds=0.0)
    bound = _bound_window()
    if not bound:
        return dict(state="unbound")
    foreground = foreground or _foreground_window
    composition_visible = composition_visible or _composition_visible
    sleep = sleep or time.sleep
    quiet = DEFAULT_QUIET_SECONDS if quiet_seconds is None else max(0, float(quiet_seconds))
    waited = 0.0
    while composition_visible() and waited < quiet:
        pause = 0.1
        pause = min(pause, max(0.01, quiet - waited))
        sleep(pause)
        waited += pause
    if int(foreground() or 0) == bound:
        return dict(state="boss_foreground", waited_seconds=round(waited, 3))
    return dict(state="idle", waited_seconds=round(waited, 3))


def requires_guard(command) -> bool:
    names = {Path(str(arg)).name.lower() for arg in command}
    if "guarded-uia-action.ps1" not in names:
        return False
    args = [str(arg).lower() for arg in command]
    if "-action" not in args:
        return True
    index = args.index("-action") + 1
    action = args[index] if index < len(args) else ""
    return action in {"invoke", "scroll", "reveal"}
