"""Move the mouse in a slow bounded orbit while the agent waits."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wintypes
import json
import math
import os
import sys
import time


try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


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


def parse_bounds(value: str) -> tuple[int, int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("content bounds must be left,top,right,bottom")
    left, top, right, bottom = parts
    if right <= left or bottom <= top:
        raise ValueError("content bounds must describe a positive rectangle")
    return left, top, right, bottom


def orbit_points(
    center_x: int,
    center_y: int,
    radius: int,
    period_ms: int,
    duration_ms: int,
    sample_ms: int = 40,
    start_x: int | None = None,
    start_y: int | None = None,
) -> list[tuple[int, int]]:
    if radius < 4:
        raise ValueError("radius must be at least 4")
    if period_ms < 500:
        raise ValueError("period_ms must be at least 500")
    if duration_ms < 500:
        raise ValueError("duration_ms must be at least 500")
    if sample_ms < 16:
        raise ValueError("sample_ms must be at least 16")
    steps = max(2, duration_ms // sample_ms)
    entry_ms = min(900, duration_ms // 4)
    source_x = center_x if start_x is None else start_x
    source_y = center_y if start_y is None else start_y
    points: list[tuple[int, int]] = []
    for index in range(steps + 1):
        elapsed = duration_ms * index / steps
        angle = 2 * math.pi * elapsed / period_ms
        orbit_x = center_x + radius * math.cos(angle)
        orbit_y = center_y + radius * math.sin(angle)
        if elapsed < entry_ms:
            progress = elapsed / entry_ms
            eased = progress * progress * (3 - 2 * progress)
            x = source_x + (orbit_x - source_x) * eased
            y = source_y + (orbit_y - source_y) * eased
        else:
            x, y = orbit_x, orbit_y
        points.append((round(x), round(y)))
    return points


def orbit_schedule(
    center_x: int,
    center_y: int,
    radius: int,
    period_ms: int,
    duration_ms: int,
    active_ms: int = 5000,
    rest_ms: int = 5000,
    sample_ms: int = 40,
    start_x: int | None = None,
    start_y: int | None = None,
) -> tuple[list[tuple[float, int, int]], int]:
    """Return timed orbit points and the number of active movement pulses."""
    if active_ms < 500:
        raise ValueError("active_ms must be at least 500")
    if rest_ms < 0:
        raise ValueError("rest_ms must be non-negative")

    schedule: list[tuple[float, int, int]] = []
    cursor_x = start_x
    cursor_y = start_y
    elapsed_ms = 0
    pulses = 0

    while elapsed_ms < duration_ms:
        active = min(active_ms, duration_ms - elapsed_ms)
        points = orbit_points(
            center_x,
            center_y,
            radius,
            period_ms,
            active,
            sample_ms,
            cursor_x,
            cursor_y,
        )
        for index, (x, y) in enumerate(points):
            offset = elapsed_ms + active * index / max(1, len(points) - 1)
            schedule.append((offset, x, y))
        cursor_x, cursor_y = points[-1]
        pulses += 1
        elapsed_ms += active
        if elapsed_ms >= duration_ms:
            break
        elapsed_ms += min(rest_ms, duration_ms - elapsed_ms)

    return schedule, pulses


def validate_points(points: list[tuple[int, int]], bounds: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = bounds
    for x, y in points:
        if not (left <= x <= right and top <= y <= bottom):
            raise ValueError(f"orbit point outside content bounds: {x},{y}")


def current_cursor() -> tuple[int, int] | None:
    point = wintypes.POINT()
    if os.name == "nt" and ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        return point.x, point.y
    return None


def main() -> None:
    enable_dpi_awareness()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--x", type=int, required=True, help="orbit center X")
    parser.add_argument("--y", type=int, required=True, help="orbit center Y")
    parser.add_argument("--radius", type=int, default=24)
    parser.add_argument("--period-ms", type=int, default=2600)
    parser.add_argument("--duration-ms", type=int, default=12000)
    parser.add_argument("--active-ms", type=int, default=5000, help="movement duration per pulse")
    parser.add_argument("--rest-ms", type=int, default=5000, help="pause between movement pulses")
    parser.add_argument("--sample-ms", type=int, default=40)
    parser.add_argument("--content-bounds", required=True, help="left,top,right,bottom")
    parser.add_argument("--window-handle", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    bounds = parse_bounds(args.content_bounds)
    if args.window_handle and not args.dry_run:
        if os.name != "nt" or not ctypes.windll.user32.IsWindow(args.window_handle):
            raise ValueError("window handle is not a valid top-level window")
    cursor = current_cursor() if not args.dry_run else None
    start_x = cursor[0] if cursor else None
    start_y = cursor[1] if cursor else None
    schedule, active_pulses = orbit_schedule(
        args.x,
        args.y,
        args.radius,
        args.period_ms,
        args.duration_ms,
        args.active_ms,
        args.rest_ms,
        args.sample_ms,
        start_x,
        start_y,
    )
    validate_points([(x, y) for _, x, y in schedule], bounds)
    if not args.dry_run:
        if os.name != "nt":
            raise ValueError("cursor movement is supported only on Windows")
        started = time.perf_counter()
        for offset_ms, x, y in schedule:
            target = started + offset_ms / 1000
            delay = target - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            if not ctypes.windll.user32.SetCursorPos(x, y):
                raise OSError("SetCursorPos failed")
    print(json.dumps({
        "state": "dry_run" if args.dry_run else "completed",
        "points": len(schedule),
        "activePulses": active_pulses,
        "activeMs": args.active_ms,
        "restMs": args.rest_ms,
        "center": {"x": args.x, "y": args.y},
        "radius": args.radius,
        "contentBounds": {"left": bounds[0], "top": bounds[1], "right": bounds[2], "bottom": bounds[3]},
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(json.dumps({"state": "error", "reason": str(exc)}, ensure_ascii=False))
        sys.exit(2)
