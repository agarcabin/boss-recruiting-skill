"""Keep the Windows foreground lock active for the duration of a recruiting run.

The lock prevents a background BOSS/Chromium window from taking the foreground
when UIA invokes a control. The original value is stored in the ledger so it can
be restored when the run stops or is replaced.
"""
from __future__ import annotations

import ctypes
import os
import sqlite3

try:
    import winreg
except ImportError:  # pragma: no cover - the skill runs on Windows
    winreg = None

SPI_GETFOREGROUNDLOCKTIMEOUT = 0x2000
SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2001
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02
TARGET_TIMEOUT_MS = 200000
KEY_ORIGINAL = "foreground_lock_timeout/original"
KEY_OWNER = "foreground_lock_timeout/run"

if os.name == "nt":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.SystemParametersInfoW.argtypes = [
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_uint,
    ]
    _user32.SystemParametersInfoW.restype = ctypes.c_bool
else:
    _user32 = None


def _require_windows():
    if _user32 is None:
        raise OSError("windows_only")


def _get_timeout() -> int:
    _require_windows()
    value = ctypes.c_uint(0)
    if not _user32.SystemParametersInfoW(
        SPI_GETFOREGROUNDLOCKTIMEOUT, 0, ctypes.byref(value), 0
    ):
        raise OSError(ctypes.get_last_error(), "SPI_GETFOREGROUNDLOCKTIMEOUT failed")
    return int(value.value)


def _set_timeout(milliseconds: int) -> None:
    _require_windows()
    # For this SPI the timeout is passed as the pvParam value itself.
    if not _user32.SystemParametersInfoW(
        SPI_SETFOREGROUNDLOCKTIMEOUT,
        0,
        ctypes.c_void_p(int(milliseconds)),
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
    ):
        raise OSError(ctypes.get_last_error(), "SPI_SETFOREGROUNDLOCKTIMEOUT failed")


def _write_registry(milliseconds: int) -> None:
    if winreg is None:
        raise OSError("windows_only")
    key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE
    )
    try:
        winreg.SetValueEx(
            key, "ForegroundLockTimeout", 0, winreg.REG_DWORD, int(milliseconds)
        )
    finally:
        winreg.CloseKey(key)


def _setting(db: sqlite3.Connection, key: str):
    try:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    except sqlite3.OperationalError:
        return None
    return row[0] if row else None


def _save(db: sqlite3.Connection, key: str, value) -> None:
    try:
        db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
        db.commit()
    except sqlite3.OperationalError:
        pass


def _delete(db: sqlite3.Connection, key: str) -> None:
    try:
        db.execute("DELETE FROM settings WHERE key=?", (key,))
        db.commit()
    except sqlite3.OperationalError:
        pass


def apply(db: sqlite3.Connection, run_id: str) -> dict:
    """Persist and apply the foreground lock for *run_id*.

    The value is written to HKCU as well as applied through SPI so it survives
    a restart. It is intentionally kept after the run; use restore() manually
    if the previous value is needed.
    """
    original = _setting(db, KEY_ORIGINAL)
    owner = _setting(db, KEY_OWNER)
    try:
        current = _get_timeout()
        read_error = None
    except OSError as exc:
        current = None
        read_error = str(exc)
    if original is None and current is not None:
        _save(db, KEY_ORIGINAL, current)
    _save(db, KEY_OWNER, run_id)

    registry_ok = True
    registry_error = None
    try:
        _write_registry(TARGET_TIMEOUT_MS)
    except OSError as exc:
        registry_ok = False
        registry_error = str(exc)

    if current == TARGET_TIMEOUT_MS:
        return dict(
            state="already_target",
            original=int(original) if original is not None else current,
            registry=registry_ok,
            changed=False,
        )
    try:
        _set_timeout(TARGET_TIMEOUT_MS)
    except OSError as exc:
        return dict(
            state="registry_only" if registry_ok else "failed",
            original=int(original) if original is not None else current,
            registry=registry_ok,
            changed=False,
            error=registry_error or str(exc),
            read_error=read_error,
        )
    return dict(
        state="applied",
        original=int(original) if original is not None else current,
        registry=registry_ok,
        changed=True,
        read_error=read_error,
    )


def restore(db: sqlite3.Connection, run_id: str | None = None) -> dict:
    """Restore the saved value; never restore another active run's value."""
    original = _setting(db, KEY_ORIGINAL)
    owner = _setting(db, KEY_OWNER)
    if original is None:
        return dict(state="not_applied")
    if run_id and owner and owner != run_id:
        return dict(state="owned_by_other_run", owner=owner)
    registry_ok = True
    registry_error = None
    try:
        _write_registry(int(original))
    except OSError as exc:
        registry_ok = False
        registry_error = str(exc)
    try:
        _set_timeout(int(original))
    except OSError as exc:
        return dict(
            state="registry_only" if registry_ok else "failed",
            original=int(original),
            registry=registry_ok,
            error=registry_error or str(exc),
        )
    _delete(db, KEY_ORIGINAL)
    _delete(db, KEY_OWNER)
    return dict(state="restored", original=int(original), registry=registry_ok)


def recover(db: sqlite3.Connection) -> dict:
    """Restore a stale value left by a run that is no longer active."""
    original = _setting(db, KEY_ORIGINAL)
    owner = _setting(db, KEY_OWNER)
    if original is None or not owner:
        return dict(state="nothing_to_recover")
    try:
        row = db.execute("SELECT state FROM run_control WHERE run_id=?", (owner,)).fetchone()
    except sqlite3.OperationalError:
        row = None
    if row and row[0] in ("running", "paused"):
        return dict(state="active_run_owns", owner=owner)
    return restore(db, owner)
