"""Offline regressions for notice identity, handoff latency and tab selection."""
import argparse
import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import candidate_checks
import candidate_log
import ledger
import powershell_host
import workflow_handoff
from workflow_windows import WindowsAdapter
from windows_process import hidden_options


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE workflow_state(run_id,phase,payload)')
        self.request = self.root / 'visit-summary.json'
        self.response = self.root / 'visit-summary.response.json'
        self.request.write_text(json.dumps(dict(kind='summary', evidence={'facts': 'synthetic'})), encoding='utf-8')
        self.data = dict(candidate={'candidate_name': 'synthetic'}, visits=2, handoff_kind='summary',
                         request_file=str(self.request), response_file=str(self.response), scheduler_state='needs_summary')
        self.put()
        self.control = patch('ledger.control_state', return_value='running').start()
        self.addCleanup(patch.stopall)

    def put(self):
        self.db.execute('DELETE FROM workflow_state')
        self.db.execute('INSERT INTO workflow_state VALUES (?,?,?)', ('r', 'summarize', json.dumps(self.data)))

    def test_ready_request_returns_immediately_without_sleep_or_write(self):
        before = self.db.total_changes
        with patch('workflow_handoff.time.sleep') as sleep:
            result = workflow_handoff.wait(self.db, 'r')
        self.assertEqual(result['state'], 'needs_summary')
        self.assertEqual(result['request']['evidence']['facts'], 'synthetic')
        sleep.assert_not_called()
        self.assertEqual(self.db.total_changes, before)

    def test_response_already_written_is_not_handed_off_again(self):
        self.response.write_text('{"pros":"done","cons":"done"}', encoding='utf-8')
        result = workflow_handoff.wait(self.db, 'r', timeout=0)
        self.assertTrue(result['wait_timed_out'])
        self.assertNotIn('request', result)

    def test_partial_response_and_missing_request_are_retried(self):
        self.response.write_text('{"pros":', encoding='utf-8')
        self.assertEqual(workflow_handoff.snapshot(self.db, 'r')['state'], 'handoff_file_pending')
        self.response.unlink()
        self.request.unlink()
        self.assertEqual(workflow_handoff.snapshot(self.db, 'r')['state'], 'handoff_file_pending')

    def test_pause_returns_without_exposing_stale_request(self):
        self.control.return_value = 'paused'
        result = workflow_handoff.wait(self.db, 'r')
        self.assertEqual(result['state'], 'paused')
        self.assertNotIn('request', result)

    def test_poll_detects_new_request_within_one_interval(self):
        self.data.pop('handoff_kind')
        self.put()
        def arrive(_):
            self.data['handoff_kind'] = 'summary'
            self.put()
        with patch('workflow_handoff.time.sleep', side_effect=arrive) as sleep:
            result = workflow_handoff.wait(self.db, 'r', timeout=1)
        self.assertEqual(result['state'], 'needs_summary')
        sleep.assert_called_once()
        self.assertLessEqual(sleep.call_args.args[0], .1)


class CoworkerSelectionTests(unittest.TestCase):
    def test_selected_tab_reads_once_without_invoke_or_retry(self):
        adapter = WindowsAdapter.__new__(WindowsAdapter)
        adapter.hwnd = 123
        adapter.query = Mock(return_value={'state': 'found', 'match': {'selected': True}})
        adapter.ps = Mock(return_value={'state': 'empty', 'evidence': 'explicit empty'})
        adapter.invoke = Mock()
        result = adapter.colleague({}, 'resume')
        self.assertEqual(result['state'], 'empty')
        adapter.query.assert_called_once_with('CoworkerTab')
        adapter.ps.assert_called_once()
        adapter.invoke.assert_not_called()

    def test_missing_tab_remains_unknown_with_specific_reason(self):
        adapter = WindowsAdapter.__new__(WindowsAdapter)
        adapter.query = Mock(return_value={'state': 'missing'})
        adapter.ps, adapter.invoke = Mock(), Mock()
        with patch('workflow_windows.time.sleep'):
            result = adapter.colleague({}, 'resume')
        self.assertEqual(result, dict(state='unavailable', evidence='coworker_header_not_found'))
        self.assertEqual(adapter.query.call_count, 2)
        adapter.ps.assert_not_called()
        adapter.invoke.assert_not_called()

    def test_ancestor_does_not_clear_selected_tab(self):
        helper = Path(__file__).with_name('coworker-tab-selection.ps1')
        host = powershell_host.command(helper)[0]
        script = """& { param($helper)
. $helper
$fromPattern=Test-CoworkerTabSelection $false $true ''
$fromPattern=Test-CoworkerTabSelection $fromPattern $false 'tab-list'
$fromClass=Test-CoworkerTabSelection $false $false 'tab active'
$fromClass=Test-CoworkerTabSelection $fromClass $false 'parent'
@($fromPattern,$fromClass,(Test-CoworkerTabSelection $false $false 'tab inactive'),
  (Test-CoworkerTabSelection $false $false 'tab is-active')) | ConvertTo-Json -Compress
} """ + "'" + str(helper).replace("'", "''") + "'"
        result = subprocess.run([host, '-NoProfile', '-Command', script], capture_output=True,
                                text=True, timeout=15, check=True, **hidden_options())
        self.assertEqual(json.loads(result.stdout), [True, True, False, True])


class NoticeRoundTripTests(unittest.TestCase):
    def test_repeated_record_and_reserve_preserve_notice_and_relative_date_anchor(self):
        from test_hr_job import document
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp)
            profile = root / 'Company' / 'job.md'
            profile.parent.mkdir()
            profile.write_text(document(resume_words='组装'), encoding='utf-8')
            with patch.object(ledger, 'PROFILE_ROOT', root):
                db = ledger.connect(root / 'ledger.sqlite')
                stack.callback(db.close)
                with contextlib.redirect_stdout(io.StringIO()):
                    ledger.start(db, argparse.Namespace(profile=profile, target=2, max_views=4, min_score=60))
            rid = db.execute('SELECT run_id FROM runs').fetchone()[0]
            candidate_log.table(db)
            ledger.ensure_candidate(db, rid, 'synthetic')
            at = datetime.now(timezone.utc)
            observation = dict(state='unavailable', evidence='record list unreadable', observed_at=at.isoformat())
            notice = candidate_checks.notice_id(db, rid, 'synthetic', observation)
            candidate_checks.acknowledge_notice(db, rid, 'synthetic', observation, dict(notice_id=notice, displayed=True))
            payload = dict(candidate_id='synthetic', candidate_name='虚构测试', keyword_text='组装', read_complete=True,
                           decision='greet', overall_score=60, electronic_resume_enabled=True,
                           electronic=dict(score=60, evidence='组装'), hard_requirements=False,
                           pros='组装', cons='待核实', coworker_progress=observation)
            tokens = []
            for offset in (1, 2):
                with patch('ledger.now', return_value=at + timedelta(seconds=offset)), contextlib.redirect_stdout(io.StringIO()), \
                     patch('csv_report.setup_viewer', side_effect=lambda template, target, specs, configure=None: shutil.copy2(template, target)):
                    candidate_log.record(db, argparse.Namespace(run=rid, output_root=root), payload)
                stored = json.loads(db.execute('SELECT coworker_progress FROM assessments').fetchone()[0])
                self.assertEqual(stored, observation)
                self.assertEqual(candidate_checks.notice_id(db, rid, 'synthetic', stored), notice)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    ledger.reserve(db, argparse.Namespace(run=rid, candidate_id='synthetic'))
                result = json.loads(output.getvalue())
                self.assertEqual(result['state'], 'ready')
                tokens.append(result['token'])
            self.assertEqual(tokens[0], tokens[1])
            # Genuine new evidence and known recent contact must still block.
            changed = dict(observation, evidence='different evidence')
            self.assertFalse(candidate_checks.evaluate_resume(db, rid, 'synthetic', changed)['may_continue'])
            recent = dict(state='records', evidence='recent', records=[at.isoformat()], records_complete=True)
            candidate_checks.record_resume_attempt(db, rid, 'synthetic', recent)
            self.assertFalse(candidate_checks.evaluate_resume(db, rid, 'synthetic', observation)['may_continue'])


if __name__ == '__main__':
    unittest.main()
