"""Small Windows progress and control window for a recruiting run."""

from __future__ import annotations

import argparse
import contextlib
import threading
import stop_controller
import run_safety
import ctypes
import ctypes.wintypes as wintypes
import io
import math
import os
import sqlite3
import time
import tkinter as tk
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import messagebox

import ledger
import daily_metrics
from keep_awake import KeepAwake
from report_paths import report_path


CN_TZ = timezone(timedelta(hours=8))
SW_MAXIMIZE = 3
SW_HIDE = 0
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

STATUS_WIDTH = 650
BUTTON_WIDTH = 300
PANEL_HEIGHT = 80
PANEL_TOP = 6
PANEL_ALPHA = 0.78
TRANSPARENT_KEY = "#010203"
PANEL_BG = "#17212B"
PANEL_FG = "#E8EEF5"
PANEL_MUTED = "#AAB8C7"
PANEL_BORDER = "#3C4D5D"
BUTTON_BG = "#30404F"
BUTTON_ACTIVE_BG = "#42576A"
BUTTON_DISABLED_BG = "#26333E"
BUTTON_BORDER = "#3C4D5D"
ESTIMATE_REVIEW_BASELINE = 300


def hide_console_window() -> None:
    if os.name != "nt":
        return
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)


def enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass
    ctypes.windll.user32.SetProcessDPIAware()


def _top_level_handle(widget: tk.Misc) -> int:
    hwnd = widget.winfo_id()
    parent = ctypes.windll.user32.GetParent(hwnd)
    return int(parent or hwnd)


def _get_window_style(hwnd: int) -> int:
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        getter = ctypes.windll.user32.GetWindowLongPtrW
        getter.restype = ctypes.c_ssize_t
        return int(getter(hwnd, GWL_EXSTYLE))
    return int(ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE))


def _set_window_style(hwnd: int, style: int) -> None:
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        setter = ctypes.windll.user32.SetWindowLongPtrW
        setter.restype = ctypes.c_ssize_t
        setter(hwnd, GWL_EXSTYLE, style)
    else:
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


def _rounded_rectangle(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs):
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1,
        x2, y1 + radius, x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2, x1, y2,
        x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def configure_overlay_windows(status_window: tk.Tk, button_window: tk.Toplevel) -> None:
    if os.name != "nt":
        return
    status_hwnd = _top_level_handle(status_window)
    status_style = _get_window_style(status_hwnd)
    _set_window_style(
        status_hwnd,
        status_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
    )
    button_hwnd = _top_level_handle(button_window)
    button_style = _get_window_style(button_hwnd)
    _set_window_style(button_hwnd, button_style | WS_EX_LAYERED | WS_EX_TOOLWINDOW)
    flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
    ctypes.windll.user32.SetWindowPos(status_hwnd, 0, 0, 0, 0, 0, flags)
    ctypes.windll.user32.SetWindowPos(button_hwnd, 0, 0, 0, 0, 0, flags)


def _window_text(hwnd: int) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def _window_class(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value


def _window_process_name(hwnd: int) -> str:
    pid = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ""
    try:
        size = wintypes.DWORD(2048)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not ctypes.windll.kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return ""
        return Path(buffer.value).name
    finally:
        ctypes.windll.kernel32.CloseHandle(process)


def find_codex_window() -> int | None:
    if os.name != "nt":
        return None
    candidates: list[tuple[int, int]] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd, _lparam):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        if _window_process_name(hwnd).lower() != "chatgpt.exe":
            return True
        if "Chrome_WidgetWin" not in _window_class(hwnd):
            return True
        if not _window_text(hwnd).strip():
            return True
        rect = wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
        candidates.append((area, int(hwnd)))
        return True

    callback = callback_type(collect)
    ctypes.windll.user32.EnumWindows(callback, 0)
    return max(candidates)[1] if candidates else None


def ensure_codex_maximized() -> tuple[bool, bool]:
    hwnd = find_codex_window()
    if hwnd is None:
        return False, False
    if ctypes.windll.user32.IsZoomed(hwnd):
        return True, True
    ctypes.windll.user32.ShowWindowAsync(hwnd, SW_MAXIMIZE)
    time.sleep(0.08)
    return True, bool(ctypes.windll.user32.IsZoomed(hwnd))


def snapshot(db: sqlite3.Connection, run_id: str, output_root=None) -> dict:
    run = ledger.run_row(db, run_id)
    progress = db.execute("""SELECT COUNT(*) AS started, COUNT(finished_at) AS completed,
        COUNT(electronic_opened_at) AS electronic FROM candidate_progress WHERE run_id=?""", (run_id,)).fetchone()
    active = ledger.active_progress(db, run_id)
    sent = db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'", (run_id,)).fetchone()[0]
    state = ledger.control_state(db, run_id)
    drain_reason=run_safety.quantity_reason(db,run_id)
    if state=="running" and drain_reason: state="draining"
    elapsed = ledger.active_elapsed_seconds(db, run_id)
    average_row = db.execute("""SELECT AVG((julianday(finished_at)-julianday(started_at))*86400.0)
        FROM candidate_progress WHERE run_id=? AND finished_at IS NOT NULL""", (run_id,)).fetchone()
    average_seconds = round(average_row[0]) if average_row[0] is not None else None
    remaining_minutes,basis=daily_metrics.estimate(run,progress["started"],sent,average_seconds,elapsed)
    daily=daily_metrics.daily_counts(db,run,output_root or Path.home()/"Desktop")
    return {"state": state, "elapsed": f"{elapsed // 3600:02d}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",
            "current_step": current_step(db, state, active), "drain_reason":drain_reason,
            "current": active["ordinal"] if active else None, "started": progress["started"],
            "completed": progress["completed"], "electronic": progress["electronic"],
            "sent": sent, "target": run["target"], "average_seconds": average_seconds,
            "remaining_minutes": remaining_minutes,"estimate_basis":basis,**daily,
            "estimate_review_baseline": run["max_views"],
            "started_at": run["started_at"], "profile_path": run["profile_path"]}


def current_step(db: sqlite3.Connection, state: str, active: sqlite3.Row | None) -> str:
    state_labels = {
        "paused": "等待继续",
        "login_required": "等待人工登录",
        "stopped": "任务已结束",
        "expired": "任务已到期",
    }
    if state in state_labels:
        return state_labels[state]
    if active is None:
        return "准备下一位候选人"
    if active["electronic_opened_at"] is None:
        if ledger.run_row(db,active["run_id"])["evaluation_mode"]!="card": return "正在打开电子简历"
    has_assessments = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='assessments'"
    ).fetchone()
    assessment = None
    if has_assessments:
        assessment = db.execute(
            "SELECT send_status,pdf_status FROM assessments WHERE run_id=? AND candidate_hash=?",
            (active["run_id"], active["candidate_hash"]),
        ).fetchone()
    candidate = db.execute(
        "SELECT status FROM candidates WHERE candidate_hash=?", (active["candidate_hash"],)
    ).fetchone()
    if candidate:
        if candidate["status"] == "pending":
            return "正在打招呼"
        if candidate["status"] == "sent" and assessment and assessment["pdf_status"] == "pending":
            return "正在归档简历"
        if candidate["status"] in ("review", "skipped", "not-sent"):
            return "正在整理评估记录"
    if assessment:
        if assessment["send_status"] == "pending":
            return "正在打招呼"
        if assessment["send_status"] == "assessed":
            return "正在准备打招呼"
        return "正在整理评估记录"
    return "正在评估列表名片" if ledger.run_row(db,active["run_id"])["evaluation_mode"]=="card" else "正在查看电子简历"


def metrics_text(data):
    remaining="估算中" if data['remaining_minutes'] is None else str(data['remaining_minutes'])+" 分钟"
    pending=" · 表格待同步" if data.get('report_pending') else ""
    return f"今日已查看 {data.get('daily_viewed',0)} 人 · 已招呼 {data.get('daily_sent',0)} 人 · 预计剩余 {remaining}{pending}"


def button_geometry(scale=1.0):
    height=round(PANEL_HEIGHT/scale)
    button_h=round(64/scale)
    return dict(y=(height-button_h)//2,height=button_h,gap=round(8/scale),x=round(8/scale),widths=[round(v/scale) for v in (80,80,108)])


class ProgressWindow:
    def __init__(self, root: tk.Tk, db_path: Path, run_id: str, output_root: Path, demo: bool = False):
        self.root, self.db_path, self.run_id, self.output_root = root, db_path, run_id, output_root
        self.demo = demo
        self.wake = KeepAwake()
        self.timer: str | None = None
        self.last_codex_check = 0.0
        self.detail_metrics_key: tuple[int, int, int, int | None] | None = None
        self.pause_enabled = False
        logical_screen_width = max(1, root.winfo_screenwidth())
        physical_screen_width = ctypes.windll.user32.GetSystemMetrics(0) if os.name == "nt" else logical_screen_width
        self.ui_scale = max(1.0, physical_screen_width / logical_screen_width)
        root.title("自动打招呼 · 演示窗口" if demo else "自动打招呼 · 运行进度")
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT_KEY)
        root.attributes("-topmost", True)
        root.attributes("-alpha", PANEL_ALPHA)
        try:
            root.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass

        status_width = round(STATUS_WIDTH / self.ui_scale)
        button_width = round(BUTTON_WIDTH / self.ui_scale)
        panel_height = round(PANEL_HEIGHT / self.ui_scale)
        panel_top = round(PANEL_TOP / self.ui_scale)
        total_width = status_width + button_width
        left = max(0, (root.winfo_screenwidth() - total_width) // 2)
        root.geometry(f"{status_width}x{panel_height}+{left}+{panel_top}")

        self.button_window = tk.Toplevel(root)
        self.button_window.overrideredirect(True)
        self.button_window.configure(bg=TRANSPARENT_KEY)
        self.button_window.attributes("-topmost", True)
        self.button_window.attributes("-alpha", PANEL_ALPHA)
        try:
            self.button_window.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            pass
        self.button_window.geometry(
            f"{button_width}x{panel_height}+{left + status_width}+{panel_top}"
        )

        self.status_canvas = tk.Canvas(
            root, width=status_width, height=panel_height,
            bg=TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self.status_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        rounded_radius = round(18 / self.ui_scale)
        _rounded_rectangle(
            self.status_canvas, 0, 0, status_width, panel_height, rounded_radius,
            fill=PANEL_BG, outline=PANEL_BORDER, width=1,
        )
        self.status_canvas.create_rectangle(
            status_width - rounded_radius, 0, status_width, panel_height,
            fill=PANEL_BG, outline="",
        )
        self.state_dot = self.status_canvas.create_oval(
            round(14 / self.ui_scale), round(14 / self.ui_scale),
            round(22 / self.ui_scale), round(22 / self.ui_scale),
            fill="#4ADE80", outline="",
        )
        self.state_item = self.status_canvas.create_text(
            round(30 / self.ui_scale), round(19 / self.ui_scale),
            text="正在读取账本…", anchor="w", fill=PANEL_FG,
            font=("Microsoft YaHei UI", -13, "bold"),
        )
        self.detail_item = self.status_canvas.create_text(
            round(30 / self.ui_scale), round(44 / self.ui_scale),
            text="", anchor="w", fill=PANEL_MUTED,
            font=("Microsoft YaHei UI", -11),
        )

        self.button_canvas = tk.Canvas(
            self.button_window, width=button_width, height=panel_height,
            bg=TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self.button_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        _rounded_rectangle(
            self.button_canvas, 0, 0, button_width, panel_height, rounded_radius,
            fill=PANEL_BG, outline=PANEL_BORDER, width=1,
        )
        self.button_canvas.create_rectangle(
            0, 0, rounded_radius, panel_height, fill=PANEL_BG, outline="",
        )
        geometry=button_geometry(self.ui_scale)
        button_y=geometry["y"];button_gap=geometry["gap"];button_x=geometry["x"]
        button_h=geometry["height"];button_widths=geometry["widths"]
        self.button_rects = []
        self.button_texts = []
        self.button_enabled = [False, True, True]
        labels = ["暂停", "结束", "查看报告"]
        for index, (label, width) in enumerate(zip(labels, button_widths)):
            x1 = button_x + sum(button_widths[:index]) + button_gap * index
            x2 = x1 + width
            rect = _rounded_rectangle(
                self.button_canvas, x1, button_y, x2, button_y + button_h,
                round(12 / self.ui_scale), fill=BUTTON_BG, outline=BUTTON_BORDER, width=1,
                tags=(f"button-{index}",),
            )
            text = self.button_canvas.create_text(
                (x1 + x2) / 2, button_y + button_h / 2,
                text=label, fill="#F4F7FA", font=("Microsoft YaHei UI", -11),
                tags=(f"button-{index}",),
            )
            self.button_rects.append(rect)
            self.button_texts.append(text)
            self.button_canvas.tag_bind(
                f"button-{index}", "<Enter>",
                lambda _e, button_index=index: self._hover_button(button_index, True),
            )
            self.button_canvas.tag_bind(
                f"button-{index}", "<Leave>",
                lambda _e, button_index=index: self._hover_button(button_index, False),
            )
        self.button_canvas.tag_bind("button-0", "<Button-1>", lambda _e: self.pause_or_resume() if self.pause_enabled else None)
        self.button_canvas.tag_bind("button-1", "<Button-1>", lambda _e: self.stop())
        self.button_canvas.tag_bind("button-2", "<Button-1>", lambda _e: self.open_report())

        root.update_idletasks()
        self.button_window.update_idletasks()
        configure_overlay_windows(root, self.button_window)
        root.protocol("WM_DELETE_WINDOW", self.stop)
        self.button_window.protocol("WM_DELETE_WINDOW", self.stop)
        self.keep_codex_maximized()
        self.refresh()

    def _hover_button(self, index: int, hovering: bool) -> None:
        enabled = self.button_enabled[index]
        self.button_canvas.configure(cursor="hand2" if enabled else "")
        fill = ("#15803D" if hovering else "#166534") if enabled and index==0 else BUTTON_ACTIVE_BG if enabled and hovering else (BUTTON_BG if enabled else BUTTON_DISABLED_BG)
        self.button_canvas.itemconfigure(self.button_rects[index], fill=fill)

    def keep_codex_maximized(self) -> None:
        if self.demo:
            return
        if time.monotonic() - self.last_codex_check < 4:
            return
        self.last_codex_check = time.monotonic()
        ensure_codex_maximized()

    def read(self) -> dict:
        db = ledger.connect(self.db_path)
        try:
            return snapshot(db, self.run_id, self.output_root)
        finally:
            db.close()

    def change(self, action: str) -> None:
        db = ledger.connect(self.db_path)
        try:
            from argparse import Namespace
            with contextlib.redirect_stdout(io.StringIO()):
                ledger.control(db, Namespace(run=self.run_id, action=action))
        finally:
            db.close()
        self.refresh()

    def refresh(self) -> None:
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.keep_codex_maximized()
        try:
            data = self.read()
            labels = {"running": "运行中", "paused": "已暂停", "login_required": "等待人工登录", "stopped": "已结束", "expired": "已到运行期限", "draining":"完成当前候选人"}
            state = data["state"]
            if not self.demo: self.wake.set_running(state in ("running","draining"))
            if state in ("expired","stopped") or (state=="draining" and data["current"] is None):
                self.begin_termination("run_expired" if state=="expired" else data.get("drain_reason") or "manual_stop")
                return
            dot_colors = {
                "running": "#4ADE80",
                "draining": "#F6C857",
                "paused": "#F6C857",
                "login_required": "#FB923C",
                "stopped": "#94A3B8",
                "expired": "#EF6262",
            }
            self.status_canvas.itemconfigure(self.state_dot, fill=dot_colors[state])
            self.status_canvas.itemconfigure(
                self.state_item, text=f"{labels[state]} · {data['elapsed']} · {data['current_step']}"
            )
            metrics_key = (data.get("daily_viewed"),data.get("daily_sent"),data["remaining_minutes"],data.get("report_pending"))
            if metrics_key != self.detail_metrics_key:
                self.status_canvas.itemconfigure(self.detail_item, text=metrics_text(data))
                self.detail_metrics_key = metrics_key
            self.pause_enabled = state in ("running", "paused")
            self.button_enabled = [self.pause_enabled, True, True]
            self.button_canvas.itemconfigure(
                self.button_texts[0], text="继续" if state == "paused" else "暂停",
                fill="#F4F7FA" if self.pause_enabled else "#7C8A97",
            )
            self.button_canvas.itemconfigure(
                self.button_rects[0],
                fill="#166534" if self.pause_enabled else BUTTON_DISABLED_BG,
            )
            self.button_canvas.itemconfigure(self.button_rects[1], fill=BUTTON_BG)
            self.button_canvas.itemconfigure(self.button_texts[1], fill="#F4F7FA")
            self.button_canvas.itemconfigure(self.button_rects[2], fill=BUTTON_BG)
            self.button_canvas.itemconfigure(self.button_texts[2], fill="#F4F7FA")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.wake.close()
            self.status_canvas.itemconfigure(self.state_dot, fill="#EF6262")
            self.status_canvas.itemconfigure(self.state_item, text="读取状态失败")
            self.status_canvas.itemconfigure(self.detail_item, text=str(exc)[:100])
            self.pause_enabled = False
            self.detail_metrics_key = None
            self.button_enabled = [False, True, True]
            self.button_canvas.itemconfigure(self.button_rects[0], fill=BUTTON_DISABLED_BG)
            self.button_canvas.itemconfigure(self.button_texts[0], fill="#7C8A97")
            self.button_canvas.itemconfigure(self.button_rects[1], fill=BUTTON_BG)
            self.button_canvas.itemconfigure(self.button_texts[1], fill="#F4F7FA")
            self.button_canvas.itemconfigure(self.button_rects[2], fill=BUTTON_BG)
            self.button_canvas.itemconfigure(self.button_texts[2], fill="#F4F7FA")
        self.timer = self.root.after(1000, self.refresh)

    def pause_or_resume(self) -> None:
        try:
            self.change("resume" if self.read()["state"] == "paused" else "pause")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("状态更新失败", str(exc))

    def begin_termination(self, reason):
        if getattr(self, "terminating", False): return
        self.terminating = True
        self.wake.close()
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        self.termination_result = None
        def worker():
            try:
                with contextlib.closing(ledger.connect(self.db_path)) as db:
                    run_safety.request_stop(db,self.run_id,reason)
                    report=stop_controller.finalize(db,self.run_id,self.output_root,
                        interrupt=not self.demo,opener=lambda _:None)
                self.termination_result=(report,None)
            except Exception as exc: self.termination_result=(None,str(exc))
        threading.Thread(target=worker,daemon=False).start()
        self.root.after(100,self.finish_termination)

    def finish_termination(self):
        if self.termination_result is None:
            self.root.after(100,self.finish_termination)
            return
        report,error=self.termination_result
        if error:
            self.terminating=False
            messagebox.showerror("结束失败",error,parent=self.root)
            return
        self.root.destroy()
        if report: os.startfile(report)

    def stop(self) -> None:
        self.begin_termination("manual_stop")

    def open_report(self) -> None:
        try:
            state = self.read()
            path = report_path(self.output_root, state["started_at"], state["profile_path"])
            if not path.is_file():
                messagebox.showinfo("简报尚未生成", "处理完第一位候选人后，简报才会生成。", parent=self.root)
                return
            os.startfile(path)  # Windows opens the workbook with the registered Excel app.
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("打开报告失败", str(exc), parent=self.root)


def main() -> None:
    hide_console_window()
    enable_dpi_awareness()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ledger.DEFAULT_DB)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output-root", type=Path, default=Path.home() / "Desktop")
    parser.add_argument("--demo", action="store_true", help="Label a temporary test run as demo data")
    args = parser.parse_args()
    with contextlib.closing(ledger.connect(args.db)) as db:
        ledger.run_row(db, args.run)
    root = tk.Tk()
    window=ProgressWindow(root,args.db,args.run,args.output_root,demo=args.demo)
    try: root.mainloop()
    finally: window.wake.close()


if __name__ == "__main__":
    main()
