"""Regression checks for the BOSS login-notice dismissal boundary."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import powershell_host


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


class BossLoginNoticeTests(unittest.TestCase):
    def test_dialog_logic_dispatches_unique_confirm_once(self):
        command = powershell_host.command(SCRIPTS / "test-boss-login-notice.ps1")
        done = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=60,
        )
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        result = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(result["state"], "passed")
        self.assertGreaterEqual(result["checks"], 5)

    def test_entry_points_dismiss_login_notice(self):
        for name in (
            "bind-boss-browser.ps1",
            "workflow-uia.ps1",
            "guarded-uia-action.ps1",
            "probe-boss-window.ps1",
            "ensure-recommendation.ps1",
            "capture-card.ps1",
            "resume_capture.ps1",
            "read-coworker-progress.ps1",
            "uia-query.ps1",
        ):
            text = (SCRIPTS / name).read_text(encoding="utf-8-sig")
            self.assertIn("Dismiss-BossLoginNotice", text, name)


if __name__ == "__main__":
    unittest.main()
