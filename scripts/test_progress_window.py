"""Checks for progress snapshot stages and completion-based metrics."""

import contextlib
import io
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import ledger
import progress_window
from test_ledger import PROFILE


def invoke(fn, db, **kwargs):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        fn(db, Namespace(**kwargs))
    return json.loads(stream.getvalue())


class ProgressWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        profile_override = patch.object(ledger, "PROFILE_ROOT", self.root)
        profile_override.start()
        self.addCleanup(profile_override.stop)
        self.profile = self.root / "profile.md"
        self.profile.write_text(PROFILE, encoding="utf-8")
        self.db = ledger.connect(self.root / "ledger.db")
        self.run_id = invoke(
            ledger.start,
            self.db,
            profile=str(self.profile),
            target=3,
            duration_min=60,
            min_score=70,
        )["run_id"]

    def tearDown(self):
        self.db.close()

    def test_current_step_and_metrics_refresh_from_completed_candidates(self):
        waiting = progress_window.snapshot(self.db, self.run_id)
        self.assertEqual(waiting["current_step"], "准备下一位候选人")
        self.assertIn("平均 -- 秒/人", progress_window.metrics_text(waiting))

        candidate_id = "candidate-one"
        invoke(ledger.candidate_begin, self.db, run=self.run_id, candidate_id=candidate_id)
        opening = progress_window.snapshot(self.db, self.run_id)
        self.assertEqual(opening["current_step"], "正在打开电子简历")

        invoke(ledger.electronic_opened, self.db, run=self.run_id, candidate_id=candidate_id)
        viewing = progress_window.snapshot(self.db, self.run_id)
        self.assertEqual(viewing["current_step"], "正在查看电子简历")

        digest = ledger.run_candidate_hash(self.db, self.run_id, candidate_id)
        ended = datetime.now(timezone.utc)
        started = ended - timedelta(seconds=100)
        stamp = ledger.iso(ended)
        self.db.execute(
            "INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
            (digest, "Test Company-Sales", self.run_id, "sent", None, stamp, stamp, stamp),
        )
        self.db.execute(
            "UPDATE candidate_progress SET started_at=?, electronic_opened_at=?, finished_at=? "
            "WHERE run_id=? AND candidate_hash=?",
            (ledger.iso(started), ledger.iso(started), stamp, self.run_id, digest),
        )

        completed = progress_window.snapshot(self.db, self.run_id)
        self.assertEqual(completed["completed"], 1)
        self.assertEqual(completed["sent"], 1)
        self.assertAlmostEqual(completed["average_seconds"], 100, delta=1)
        self.assertEqual(completed["remaining_minutes"], 499)
        self.assertEqual(completed["estimate_review_baseline"], 300)
        self.assertEqual(
            progress_window.metrics_text(completed),
            "已查看 1 人 · 已招呼 1 人 · 平均 100 秒/人 · 预计剩余 499 分钟",
        )

    def test_paused_time_freezes_display_elapsed(self):
        run = ledger.run_row(self.db, self.run_id)
        started = ledger.parse_time(run["started_at"])
        with patch.object(ledger, "now", return_value=started + timedelta(seconds=30)):
            self.assertEqual(
                invoke(ledger.control, self.db, run=self.run_id, action="pause")["state"],
                "paused",
            )
        with patch.object(ledger, "now", return_value=started + timedelta(seconds=90)):
            paused = progress_window.snapshot(self.db, self.run_id)
            self.assertEqual(paused["elapsed"], "00:00:30")
            self.assertEqual(
                invoke(ledger.control, self.db, run=self.run_id, action="resume")["state"],
                "running",
            )
        with patch.object(ledger, "now", return_value=started + timedelta(seconds=100)):
            resumed = progress_window.snapshot(self.db, self.run_id)
            self.assertEqual(resumed["elapsed"], "00:00:40")

    def test_stop_delegates_without_second_confirmation(self):
        window=progress_window.ProgressWindow.__new__(progress_window.ProgressWindow)
        window.begin_termination=unittest.mock.Mock()
        with patch.object(progress_window.messagebox,"askyesno",side_effect=AssertionError("unexpected second confirmation")):
            window.stop()
        window.begin_termination.assert_called_once_with("manual_stop")


if __name__ == "__main__":
    unittest.main()
