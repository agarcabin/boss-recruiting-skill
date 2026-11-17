import json
import sqlite3
import unittest
from argparse import Namespace
from unittest.mock import Mock, patch

import ledger
import notice_wait
from workflow_runner import Runner


class NoticeWaitTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
        self.addCleanup(self.db.close)

    def test_display_starts_persistent_thirty_seconds(self):
        notice_wait.prepare(self.db, 'run', 'first')
        self.assertIsNone(notice_wait.read(self.db, 'run')['deadline'])
        self.assertEqual(notice_wait.remaining(self.db, 'run', 'first', 100), 30)
        notice_wait.prepare(self.db, 'run', 'first')
        self.assertEqual(notice_wait.remaining(self.db, 'run', 'first', 129), 1)
        self.assertEqual(notice_wait.remaining(self.db, 'run', 'first', 130), 0)
        self.assertFalse(notice_wait.skip(self.db, 'run'))

    def test_continue_before_receipt_and_new_notice(self):
        notice_wait.prepare(self.db, 'run', 'first')
        self.assertTrue(notice_wait.skip(self.db, 'run'))
        self.assertEqual(notice_wait.remaining(self.db, 'run', 'first', 100), 0)
        notice_wait.prepare(self.db, 'run', 'second')
        self.assertEqual(notice_wait.remaining(self.db, 'run', 'second', 100), 30)
        with self.assertRaises(ValueError):
            notice_wait.remaining(self.db, 'run', 'first', 100)

    def test_continue_command_skips_wait_while_running(self):
        self.db.execute('CREATE TABLE run_control(run_id TEXT,state TEXT,pause_reason TEXT,updated_at TEXT,paused_at TEXT,paused_seconds INT)')
        notice_wait.prepare(self.db, 'run', 'first')
        self.db.commit()
        with patch.object(ledger, 'control_state', return_value='running'), patch.object(ledger, 'output'):
            ledger.control(self.db, Namespace(run='run', action='resume'))
        self.assertEqual(notice_wait.remaining(self.db, 'run', 'first', 100), 0)

    def exercise_runner(self, mismatch, count):
        self.db.execute('INSERT INTO settings VALUES (?,?)', ('boss_page_job/run', json.dumps(dict(name_mismatch=mismatch, warning='🔴岗位不同'))))
        runner = Runner.__new__(Runner)
        runner.db, runner.run, runner.phase = self.db, 'run', 'select'
        runner.data = {}
        runner.adapter = Mock()
        runner.adapter.select.return_value = dict(candidate_id='old', candidate_name='Sample')
        runner.adapter.filter_state.return_value = dict(state='read', count=count)
        runner.status = lambda state=None: dict(state=state)
        runner.handoff = lambda kind, payload: dict(kind=kind, evidence=payload)
        with patch.object(ledger, 'control_state', return_value='running'), patch.object(ledger, 'run_row', return_value=dict(evaluation_mode='resume')), patch('workflow_runner.recruiting_rules.run_rules', return_value=dict(page_layout_policy=True)), patch('workflow_runner.run_safety.quantity_reason', return_value=None), patch('notice_wait.time.time', return_value=100):
            result = runner.step()
            if not mismatch and count:
                self.assertEqual(runner.phase, 'open')
                return
            notice = result['evidence']
            self.assertIn(notice_wait.MESSAGE, notice['message'])
            self.assertEqual(runner.phase, 'filter_notice')
            self.assertIsNone(notice_wait.read(self.db, 'run')['deadline'])
            runner.response = lambda: dict(notice_id=notice['notice_id'], displayed=True)
            runner.step()
            self.assertEqual(runner.phase, 'notice_wait')
            self.assertEqual(runner.step()['state'], 'notice_wait')
            runner.adapter.open.assert_not_called()
            notice_wait.skip(self.db, 'run')
            runner.step()
            self.assertEqual(runner.phase, 'select')
            self.assertNotIn('candidate', runner.data)
            runner.step()
            self.assertEqual(runner.phase, 'open')

    def test_zero_filters_wait(self): self.exercise_runner(False, 0)
    def test_mismatch_wait(self): self.exercise_runner(True, 2)
    def test_both_share_single_wait(self): self.exercise_runner(True, 0)
    def test_matching_job_and_filters_no_wait(self): self.exercise_runner(False, 2)

    def test_overlay_reasserts_topmost_without_activating(self):
        import progress_window
        status, buttons = Mock(), Mock()
        with patch.object(progress_window, '_top_level_handle', side_effect=[11, 22]), patch.object(progress_window, '_get_window_style', return_value=0), patch.object(progress_window, '_set_window_style'), patch.object(progress_window.ctypes.windll.user32, 'SetWindowPos') as position:
            progress_window.configure_overlay_windows(status, buttons)
        self.assertEqual([(c.args[0].value, c.args[1].value) for c in position.call_args_list], [(11, progress_window.wintypes.HWND(-1).value), (22, progress_window.wintypes.HWND(-1).value)])
        for call in position.call_args_list:
            self.assertTrue(call.args[-1] & progress_window.SWP_NOACTIVATE)
            self.assertFalse(call.args[-1] & progress_window.SWP_NOZORDER)


if __name__ == '__main__':
    unittest.main()
