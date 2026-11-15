"""Capture interruption regressions using synthetic state and no BOSS actions."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import capture_control
import capture_resume
import ledger
import managed_helper
from workflow_runner import Runner
from test_hr_job import document


class CaptureControlTests(unittest.TestCase):
    def setUp(self):
        self.stack=contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        profile=root/'Company'/'job.md'
        profile.parent.mkdir()
        profile.write_text(document(resume_words='组装'),encoding='utf-8')
        with patch.object(ledger,'PROFILE_ROOT',root):
            self.db=ledger.connect(root/'ledger.sqlite')
            self.stack.callback(self.db.close)
            with contextlib.redirect_stdout(io.StringIO()):
                ledger.start(self.db,argparse.Namespace(profile=profile,target=2,max_views=4,min_score=60))
        self.run=self.db.execute('SELECT run_id FROM runs').fetchone()[0]
        self.generation=ledger.run_row(self.db,self.run)['generation']
        self.root=root

    def test_foreground_loss_is_not_logged_as_save_failure(self):
        failure=subprocess.CalledProcessError(1,['synthetic'],stderr='bound_codex_iab_not_foreground')
        with patch('capture_resume._capture',side_effect=failure):
            with self.assertRaisesRegex(capture_control.CaptureInterrupted,'离开前台'):
                capture_resume.capture(self.db,self.run,'synthetic',1,self.root/'capture')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM run_audit WHERE event='resume_save_failed'").fetchone()[0],0)

    def test_stopped_capture_is_not_logged_as_save_failure(self):
        failure=subprocess.CalledProcessError(20,['synthetic'],stderr='helper_cancelled')
        def stopped(*args):
            self.db.execute("UPDATE runs SET stop_reason='manual_stop',generation=generation+1 WHERE run_id=?",(self.run,))
            raise failure
        with patch('capture_resume._capture',side_effect=stopped):
            with self.assertRaisesRegex(capture_control.CaptureInterrupted,'结束'):
                capture_resume.capture(self.db,self.run,'synthetic',1,self.root/'capture')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM run_audit WHERE event='resume_save_failed'").fetchone()[0],0)

    def test_real_io_failure_still_records_failure(self):
        with patch('capture_resume._capture',side_effect=PermissionError('fixture access denied')):
            with self.assertRaises(PermissionError):
                capture_resume.capture(self.db,self.run,'synthetic',1,self.root/'capture')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM run_audit WHERE event='resume_save_failed'").fetchone()[0],1)

    def test_paused_or_stale_helper_does_not_launch(self):
        for state,generation in [('paused',self.generation),('running',self.generation+1)]:
            with self.subTest(state=state):
                self.db.execute('UPDATE run_control SET state=? WHERE run_id=?',(state,self.run))
                with patch('managed_helper.subprocess.Popen') as launch:
                    with self.assertRaises(capture_control.CaptureInterrupted):
                        managed_helper.run(self.db,self.run,generation,['synthetic'])
                    launch.assert_not_called()

    def test_pause_during_capture_cancels_and_unregisters_helper(self):
        process=Mock(pid=123456)
        process.poll.return_value=None
        def communicate(timeout):
            self.db.execute("UPDATE run_control SET state='paused' WHERE run_id=?",(self.run,))
            raise subprocess.TimeoutExpired('synthetic',timeout)
        process.communicate.side_effect=communicate
        with patch('managed_helper.subprocess.Popen',return_value=process),patch('run_safety.process_birth',return_value=1):
            with self.assertRaises(capture_control.CaptureInterrupted):
                managed_helper.run(self.db,self.run,self.generation,['synthetic'])
        process.kill.assert_called_once()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM run_helpers').fetchone()[0],0)

    def test_scheduler_preserves_read_phase_and_candidate(self):
        runner=Runner(self.db,self.run,Mock(),self.root)
        runner.phase='read'
        runner.data=dict(candidate=dict(candidate_id='synthetic',candidate_name='虚构测试人'))
        runner.step=Mock(side_effect=capture_control.CaptureInterrupted('窗口离开前台',foreground_required=True))
        result=runner.advance()
        self.assertEqual(result['state'],'paused')
        self.assertEqual(result['phase'],'read')
        self.assertEqual(result['candidate']['candidate_id'],'synthetic')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM assessments').fetchone()[0],0)
        runner.step=lambda:runner.status(ledger.control_state(self.db,self.run))
        runner.advance()
        self.assertTrue(runner.data['foreground_required'])
        self.assertEqual(runner.data['error'],'窗口离开前台')

    def test_adapter_propagates_interruption_without_incomplete_assessment(self):
        from workflow_windows import WindowsAdapter
        adapter=WindowsAdapter(self.db,self.run,self.root,1)
        adapter.dismiss_related=Mock()
        adapter.query=Mock(return_value=dict(keyword_text='组装',resume_text='组装',read_complete=True))
        with patch('capture_resume.capture',side_effect=capture_control.CaptureInterrupted('窗口离开前台')):
            with self.assertRaises(capture_control.CaptureInterrupted):
                adapter.read(dict(candidate_id='synthetic'),'resume')


if __name__=='__main__':unittest.main()
