import contextlib
import sqlite3
import unittest
from unittest.mock import patch

import display_switch
import virtual_display


class FakeNative:
    def __init__(self, monitors, current):
        self._monitors = monitors
        self.current = current
        self.moves = []

    def monitors(self):
        return [dict(item) for item in self._monitors]

    def monitor_for_window(self, _hwnd):
        return self.current

    def window_pid(self, _hwnd):
        return 2

    def move(self, _hwnd, rect):
        self.moves.append(rect)
        target = [item for item in self._monitors if item["work"] == rect]
        if target:
            self.current = target[0]["handle"]


def monitor(handle, device, primary, bounds):
    return dict(handle=handle, device=device, primary=primary, bounds=bounds,
                work=bounds)


class VirtualDisplayTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")

    def tearDown(self):
        self.db.close()

    def test_mode_thresholds(self):
        self.assertEqual(virtual_display._mode_for(999), "fast")
        self.assertEqual(virtual_display._mode_for(3487), "session")
        self.assertEqual(virtual_display._mode_for(10000), "persistent")

    def test_virtual_display_must_be_right_of_primary(self):
        primary = monitor(1, r"\\.\DISPLAY1", True, (0, 0, 2560, 1600))
        right = monitor(2, r"\\.\DISPLAY20", False, (2560, 0, 4480, 1080))
        overlap = monitor(2, r"\\.\DISPLAY20", False, (1920, 0, 3840, 1080))
        lower = monitor(2, r"\\.\DISPLAY20", False, (2560, 40, 4480, 1120))
        self.assertTrue(virtual_display._right_of_primary(primary, right))
        self.assertFalse(virtual_display._right_of_primary(primary, overlap))
        self.assertFalse(virtual_display._right_of_primary(primary, lower))

    def test_physical_monitors_exclude_parsec(self):
        monitors = [
            monitor(1, r"\\.\DISPLAY1", True, (0, 0, 2560, 1600)),
            monitor(2, r"\\.\DISPLAY20", False, (2560, 0, 4480, 1080)),
        ]
        with patch.object(virtual_display, "adapter_names",
                          return_value={r"\\.\DISPLAY1": "NVIDIA GeForce RTX 4060",
                                        r"\\.\DISPLAY20": "Parsec Virtual Display Adapter"}):
            self.assertEqual([item["device"] for item in virtual_display.physical_monitors(monitors)],
                             [r"\\.\DISPLAY1"])

    def test_best_mode_prefers_exact_primary_resolution(self):
        def mode(width, height, frequency=60):
            value = virtual_display.DEVMODEW()
            value.dmPelsWidth, value.dmPelsHeight = width, height
            value.dmDisplayFrequency = frequency
            return value

        with patch.object(virtual_display, "_devmode",
                          side_effect=[mode(1920, 1080), mode(2560, 1600, 60),
                                       mode(2560, 1600, 240), None]):
            self.assertEqual(virtual_display._best_mode("x", 2560, 1600), (2560, 1600, 240))
        with patch.object(virtual_display, "_devmode",
                          side_effect=[mode(1920, 1080), mode(1920, 1200), None]):
            self.assertEqual(virtual_display._best_mode("x", 2560, 1600), (1920, 1200, 60))

    def toggle(self, monitors, current, ensure_result=None):
        native = FakeNative(monitors, current)
        calls = {"ensure": 0, "after": 0}

        def ensure(_db, _run, _hwnd, _native):
            calls["ensure"] += 1
            native._monitors.append(ensure_result["monitor"])
            return dict(ensure_result, device=ensure_result["monitor"]["device"])

        def after(_db, _run, _hwnd, _native):
            calls["after"] += 1
            return dict(state="stopped")

        fake_binding = dict(hwnd=10, process_id=2, binding_id="binding")
        physical = [item for item in monitors if "Parsec" not in item["device"]]
        with patch.object(display_switch, "bound_window", return_value=fake_binding), \
                patch.object(display_switch.run_safety, "action_lock",
                             return_value=contextlib.nullcontext()), \
                patch.object(virtual_display, "physical_monitors", return_value=physical), \
                patch.object(virtual_display, "is_virtual_device",
                             side_effect=lambda device: device.endswith("DISPLAY20")), \
                patch.object(virtual_display, "ensure", side_effect=ensure), \
                patch.object(virtual_display, "after_return", side_effect=after), \
                patch.object(virtual_display, "release_all"):
            result = display_switch.toggle(self.db, "run", native=native)
        return result, calls, native

    def test_two_physical_monitors_never_start_virtual(self):
        monitors = [
            monitor(1, r"\\.\DISPLAY1", True, (0, 0, 2560, 1600)),
            monitor(2, r"\\.\DISPLAY2", False, (2560, 0, 4480, 1080)),
        ]
        result, calls, native = self.toggle(monitors, 1)
        self.assertEqual(calls["ensure"], 0)
        self.assertFalse(result["device"].endswith("DISPLAY20"))
        self.assertEqual(native.current, 2)

    def test_single_monitor_starts_virtual_on_click(self):
        monitors = [monitor(1, r"\\.\DISPLAY1", True, (0, 0, 2560, 1600))]
        virtual = monitor(9, r"\\.\DISPLAY20", False, (2560, 0, 4480, 1080))
        result, calls, native = self.toggle(monitors, 1, dict(state="started", monitor=virtual))
        self.assertEqual(calls["ensure"], 1)
        self.assertEqual(result["device"], virtual["device"])
        self.assertEqual(native.current, 9)

    def test_returning_from_virtual_releases_or_keeps_by_policy(self):
        monitors = [
            monitor(1, r"\\.\DISPLAY1", True, (0, 0, 2560, 1600)),
            monitor(9, r"\\.\DISPLAY20", False, (2560, 0, 4480, 1080)),
        ]
        result, calls, native = self.toggle(monitors, 9)
        self.assertEqual(calls["after"], 1)
        self.assertTrue(result["display"] == "主屏")
        self.assertEqual(native.current, 1)


if __name__ == "__main__":
    unittest.main()
