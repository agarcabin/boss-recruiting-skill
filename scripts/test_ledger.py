"""Behavior checks for quota, uncertainty, restart, and profile binding."""

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from argparse import Namespace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import ledger
import candidate_log
import progress_window


PROFILE = """---
schema: boss-greeting-profile/v1
company: Test Company
position: Sales
approval: approved
approved_by: owner
approved_at: 2026-10-19
---
## 页面核验
Test Company, Sales, Test City.
## 企业与岗位事实
Test facts.
## 自动筛选条件
Test criteria.
## 评分规则
Score each observed source 0 to 100; overall at least 70 and all hard requirements met.
## 加分项
Test bonuses.
## 待人工确认
Test followups.
## 固定招呼话术
This is an approved greeting for a test candidate.
## 冲突与待确认
无
## 来源
Test source.
"""


def call(fn, db, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fn(db, Namespace(**kwargs))
    return json.loads(out.getvalue())


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        root_override = patch.object(ledger, "PROFILE_ROOT", self.root)
        root_override.start()
        self.addCleanup(root_override.stop)
        self.profile = self.root / "profile.md"
        self.profile.write_text(PROFILE, encoding="utf-8")
        self.db_path = self.root / "ledger.db"
        self.db = ledger.connect(self.db_path)
        candidate_log.table(self.db)
        self.run = call(ledger.start, self.db, profile=str(self.profile), target=50, duration_min=60, min_score=70)["run_id"]

    def tearDown(self):
        self.db.close()

    def reserve(self, candidate):
        gate=call(ledger.gate,self.db,run=self.run)
        if not gate["may_continue"]: return {"state":"blocked","reason":"run_stopped" if gate["state"]=="stopped" else gate.get("drain_reason") or "run_"+gate["state"]}
        if not gate["may_start_candidate"] and ledger.active_progress(self.db,self.run) is None: return {"state":"blocked","reason":gate["drain_reason"]}
        if not self.db.execute("SELECT 1 FROM candidate_progress WHERE run_id=? AND candidate_hash=?", (self.run, ledger.candidate_hash("Test Company-Sales", candidate))).fetchone():
            call(ledger.candidate_begin, self.db, run=self.run, candidate_id=candidate)
        digest = ledger.candidate_hash("Test Company-Sales", candidate)
        if not self.db.execute("SELECT 1 FROM assessments WHERE run_id=? AND candidate_hash=?", (self.run, digest)).fetchone():
            stamp = ledger.now().isoformat()
            payload = {"candidate_id": candidate, "candidate_name": "Candidate", "started_at": stamp,
                       "coworker_progress": {"state": "empty", "evidence": "Test UIA coworker panel explicitly empty"},
                       "list": {"score": 80, "evidence": "Relevant sales work"},
                       "electronic_resume_enabled": False, "overall_score": 80, "hard_requirements": True,
                       "decision": "greet", "pros": "Sales", "cons": "No extra data"}
            path = self.root / "assessment.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            call(candidate_log.record, self.db, run=self.run, input=path, output_root=self.root)
        return call(ledger.reserve, self.db, run=self.run, candidate_id=candidate)

    def finish(self, candidate):
        stamp = ledger.iso(ledger.now())
        call(candidate_log.finalize_timing, self.db, run=self.run, candidate_id=candidate,
             ended_at=stamp, output_root=self.root)
        return call(ledger.candidate_finish, self.db, run=self.run, candidate_id=candidate,
                    ended_at=stamp)

    def test_pending_blocks_all_runs_and_unknown_requires_reconciliation(self):
        first = self.reserve("https://example.test/candidate/001")
        self.assertEqual(first["state"], "ready")
        self.assertEqual(call(ledger.reserve, self.db, run=self.run, candidate_id="https://example.test/candidate/002")["reason"], "unresolved_prior_send")
        call(ledger.resolve, self.db, token=first["token"], result="unknown", min_gap=64, max_gap=80)
        self.db.close()
        self.db = ledger.connect(self.db_path)
        self.assertEqual(call(ledger.reserve, self.db, run=self.run, candidate_id="https://example.test/candidate/002")["reason"], "unresolved_prior_send")
        call(ledger.reconcile, self.db, token=first["token"], result="not-sent", manual_confirmed=True)
        call(candidate_log.sync, self.db, run=self.run, candidate_id="https://example.test/candidate/001", output_root=self.root)
        self.finish("https://example.test/candidate/001")
        self.assertEqual(self.reserve("https://example.test/candidate/001")["reason"], "candidate_seen")
        self.assertEqual(self.reserve("https://example.test/candidate/002")["state"], "ready")

    def test_sent_gap_and_rolling_limit_survive_restart(self):
        first = self.reserve("https://example.test/candidate/001")
        sent = call(ledger.resolve, self.db, token=first["token"], result="sent", min_gap=64, max_gap=64)
        self.assertEqual(sent["rolling_sent"], 1)
        call(candidate_log.sync, self.db, run=self.run, candidate_id="https://example.test/candidate/001", output_root=self.root)
        call(candidate_log.missing, self.db, run=self.run, candidate_id="https://example.test/candidate/001", reason="test no PDF", output_root=self.root)
        call(candidate_log.missing_resume, self.db, run=self.run, candidate_id="https://example.test/candidate/001", candidate_hash=None, reason="test no resume image", output_root=self.root)
        self.finish("https://example.test/candidate/001")
        self.db.close()
        self.db = ledger.connect(self.db_path)
        self.assertEqual(self.reserve("https://example.test/candidate/002")["state"], "wait")
        future = ledger.now() + timedelta(seconds=65)
        with patch.object(ledger, "now", return_value=future):
            self.assertEqual(self.reserve("https://example.test/candidate/002")["state"], "ready")
        self.db.execute("UPDATE candidates SET status='sent', sent_at=? WHERE status='pending'", (ledger.iso(ledger.now()),))
        self.db.execute("UPDATE message_attempts SET status='sent' WHERE message_index=1 AND status='pending'")
        self.db.execute("UPDATE assessments SET send_status='sent',pdf_status='missing',resume_archive_status='missing' WHERE send_status='assessed'")
        self.finish("https://example.test/candidate/002")
        prior_run = call(ledger.start, self.db, profile=str(self.profile), target=50, duration_min=60, min_score=70)["run_id"]
        for i in range(ledger.MAX_ROLLING_SENDS - 2):
            self.db.execute(
                "INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
                (f"filled-{i}", "Test Company-Sales", prior_run, "sent", None, ledger.iso(ledger.now()), ledger.iso(ledger.now()), ledger.iso(ledger.now())),
            )
        self.assertEqual(self.reserve("https://example.test/candidate/003")["reason"], "rolling_limit_reached")
        self.assertEqual(call(ledger.status, self.db, run=self.run)["rolling_remaining"], 0)

    def test_profile_change_stops_existing_run(self):
        self.profile.write_text(PROFILE + "\nchanged\n", encoding="utf-8")
        self.assertEqual(self.reserve("https://example.test/candidate/001")["reason"], "profile_changed_since_start")

    def test_rolling_window_expires_without_clearing_history(self):
        old = ledger.iso(ledger.now() - timedelta(hours=24,minutes=1))
        for i in range(50):
            self.db.execute(
                "INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
                (f"old-{i}", "Test Company-Sales", "older-run", "sent", None, old, old, old),
            )
        self.assertEqual(call(ledger.status, self.db, run=self.run)["rolling_remaining"], ledger.MAX_ROLLING_SENDS)
        self.assertEqual(self.reserve("https://example.test/candidate/new")["state"], "ready")

    def test_pending_profile_cannot_start(self):
        self.profile.write_text(PROFILE.replace("approval: approved", "approval: pending"), encoding="utf-8")
        result = call(ledger.start, self.db, profile=str(self.profile), target=50, duration_min=60, min_score=70)
        self.assertEqual(result["reason"], "approval_missing")

    def test_window_pause_resume_stop_persists_and_blocks_new_actions(self):
        candidate = "https://example.test/candidate/control"
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="pause")["state"], "paused")
        self.assertEqual(call(ledger.candidate_begin, self.db, run=self.run, candidate_id=candidate)["reason"], "run_paused")
        self.db.close()
        self.db = ledger.connect(self.db_path)
        self.assertEqual(call(ledger.gate, self.db, run=self.run)["state"], "paused")
        self.assertEqual(progress_window.snapshot(self.db, self.run)["state"], "paused")
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="resume")["state"], "running")
        self.assertEqual(call(ledger.candidate_begin, self.db, run=self.run, candidate_id=candidate)["state"], "started_candidate")
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="stop")["state"], "stopped")
        self.assertEqual(self.reserve(candidate)["reason"], "run_stopped")
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="resume")["state"], "stopped")
        self.assertFalse(call(ledger.gate, self.db, run=self.run)["may_continue"])

    def test_candidate_timing_uses_switch_click_boundaries(self):
        candidate = "https://example.test/candidate/timing"
        run_start = ledger.parse_time(ledger.run_row(self.db, self.run)["started_at"])
        started_at = run_start
        begin = call(
            ledger.candidate_begin,
            self.db,
            run=self.run,
            candidate_id=candidate,
            started_at=ledger.iso(started_at),
        )
        self.assertEqual(begin["candidate_started_at"], ledger.iso(started_at))

        digest = ledger.run_candidate_hash(self.db, self.run, candidate)
        ended_at = ledger.now()
        stamp = ledger.iso(ended_at)
        self.db.execute(
            "INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
            (digest, "Test Company-Sales", self.run, "skipped", None, stamp, stamp, stamp),
        )
        candidate_log.table(self.db)
        self.db.execute(
            """INSERT INTO assessments
               (run_id,candidate_hash,candidate_name,started_at,ended_at,overall_score,
                hard_requirements,decision,pros,cons,electronic_enabled,send_status,
                updated_at,report_written)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                self.run, digest, "Candidate", ledger.iso(started_at), stamp, 10,
                "false", "skip", "none", "none", 1, "skipped", stamp, 1,
            ),
        )
        finish = call(
            ledger.candidate_finish,
            self.db,
            run=self.run,
            candidate_id=candidate,
            ended_at=stamp,
        )
        self.assertEqual(finish["candidate_ended_at"], stamp)
        stored = self.db.execute(
            "SELECT started_at,finished_at FROM candidate_progress WHERE run_id=? AND candidate_hash=?",
            (self.run, digest),
        ).fetchone()
        self.assertEqual(stored["started_at"], ledger.iso(started_at))
        self.assertEqual(stored["finished_at"], stamp)

    def test_logout_waits_for_manual_login_and_unresolved_send(self):
        candidate = "https://example.test/candidate/logout"
        ready = self.reserve(candidate)
        self.assertEqual(ready["state"], "ready")
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="login-required", reason="risk_logout")["state"], "login_required")
        self.assertFalse(call(ledger.gate, self.db, run=self.run)["may_continue"])
        self.assertEqual(progress_window.snapshot(self.db, self.run)["state"], "login_required")
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="resume")["state"], "login_required")
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="login-confirmed")["reason"], "manual_login_confirmation_required")
        blocked = call(ledger.control, self.db, run=self.run, action="login-confirmed", manual_confirmed=True)
        self.assertEqual(blocked["reason"], "unresolved_prior_send")
        call(ledger.reconcile, self.db, token=ready["token"], result="not-sent", manual_confirmed=True)
        self.assertEqual(call(ledger.control, self.db, run=self.run, action="login-confirmed", manual_confirmed=True)["state"], "running")
        self.assertTrue(call(ledger.gate, self.db, run=self.run)["may_continue"])

    def test_login_wait_does_not_extend_deadline(self):
        call(ledger.control, self.db, run=self.run, action="login-required", reason="session_expired")
        later = ledger.now() + timedelta(minutes=61)
        with patch.object(ledger, "now", return_value=later):
            result = call(ledger.control, self.db, run=self.run, action="login-confirmed", manual_confirmed=True)
            self.assertEqual(result["reason"], "run_expired")
            self.assertEqual(call(ledger.gate, self.db, run=self.run)["state"], "expired")

    def test_old_control_table_gains_login_reason_column(self):
        old_path = self.root / "old.sqlite3"
        old = sqlite3.connect(old_path)
        old.execute("CREATE TABLE run_control (run_id TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at TEXT NOT NULL)")
        old.close()
        migrated = ledger.connect(old_path)
        try:
            self.assertIn("pause_reason", {row[1] for row in migrated.execute("PRAGMA table_info(run_control)")})
            columns = {row[1] for row in migrated.execute("PRAGMA table_info(run_control)")}
            self.assertIn("paused_at", columns)
            self.assertIn("paused_seconds", columns)
        finally:
            migrated.close()

    def test_recovery_lists_token_and_counts_confirmed_send_from_confirmation(self):
        first = self.reserve("https://example.test/candidate/recover")
        pending = call(ledger.unresolved_items, self.db)
        self.assertEqual(pending["items"][0]["token"], first["token"])
        later = ledger.now() + timedelta(minutes=70)
        with patch.object(ledger, "now", return_value=later):
            self.assertEqual(call(ledger.reconcile, self.db, token=first["token"], result="sent", manual_confirmed=True)["state"], "reconciled")
            self.assertEqual(ledger.rolling_count(self.db, later), 1)

    def test_live_progress_counts_resume_opens_and_current_candidate_after_restart(self):
        candidate = "https://example.test/candidate/progress"
        started = call(ledger.candidate_begin, self.db, run=self.run, candidate_id=candidate)
        self.assertEqual(started["current_candidate_number"], 1)
        call(ledger.electronic_opened, self.db, run=self.run, candidate_id=candidate)
        call(ledger.electronic_opened, self.db, run=self.run, candidate_id=candidate)
        self.db.close()
        self.db = ledger.connect(self.db_path)
        later = ledger.now() + timedelta(minutes=3)
        with patch.object(ledger, "now", return_value=later):
            status = call(ledger.status, self.db, run=self.run)
        self.assertEqual(status["current_candidate_number"], 1)
        self.assertEqual(status["electronic_resume_opened_candidates"], 1)
        self.assertEqual(status["greetings_sent"], 0)
        self.assertGreaterEqual(status["elapsed_seconds"], 180)
        self.assertEqual(call(ledger.candidate_begin, self.db, run=self.run, candidate_id=candidate)["state"], "resumed")
        live = io.StringIO()
        with patch.object(ledger.time, "sleep", side_effect=KeyboardInterrupt), contextlib.redirect_stdout(live):
            ledger.watch(self.db, Namespace(run=self.run, interval=1))
        self.assertIn("当前处理 第1位候选人", live.getvalue())
        self.assertIn("已打开电子简历 1 人", live.getvalue())
        recent = call(ledger.recent_runs, self.db)["items"][0]
        self.assertEqual(recent["run_id"], self.run)
        self.assertEqual(recent["profile_path"], str(self.profile.resolve()))
        self.assertEqual(recent["company"], "Test Company")
        self.assertEqual(recent["position"], "Sales")
        self.assertEqual(recent["display_name"], "Test Company - Sales")
        self.assertEqual(recent["run_state"], "running")
        self.assertTrue(recent["resumable"])

    def test_approved_flag_does_not_override_unresolved_criteria(self):
        self.profile.write_text(PROFILE.replace("Test criteria.", "学历待确认。"), encoding="utf-8")
        result = call(ledger.start, self.db, profile=str(self.profile), target=50, duration_min=60, min_score=70)
        self.assertEqual(result["reason"], "unresolved_policy_text")


if __name__ == "__main__":
    unittest.main()
