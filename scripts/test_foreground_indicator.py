"""Verify foreground signal lifecycle without opening BOSS or sending messages."""
import json
import os
import unittest
from unittest.mock import Mock,patch
import foreground_activity
import managed_helper
import progress_window
import run_safety
import safe_action
import test_capture_control as fixtures


class ForegroundIndicatorTests(unittest.TestCase):
    def setUp(self):
        fixtures.CaptureControlTests.setUp(self)
        self.activate=self.stack.enter_context(patch('foreground_activity.activate'))

    def signal(self):
        data=progress_window.snapshot(self.db,self.run,self.root)
        return progress_window.indicator(data),data

    def test_capture_is_yellow_and_ocr_returns_green(self):
        with foreground_activity.track(self.db,self.run,['pwsh','resume_capture.ps1']):
            signal,data=self.signal()
            self.assertEqual(signal,('yellow','需要前台'))
            self.assertEqual(data['foreground_label'],'正在采集简历截图')
        with foreground_activity.track(self.db,self.run,['python','resume_image_pipeline.py','rapidocr']):
            self.assertEqual(self.signal()[0],('green','运行中'))

    def test_exception_cleans_activity_and_dead_owner_cannot_leave_yellow(self):
        with self.assertRaises(ValueError):
            with foreground_activity.track(self.db,self.run,['pwsh','resume_capture.ps1']):
                raise ValueError('fixture')
        self.assertIsNone(foreground_activity.current(self.db,self.run))
        self.db.execute('INSERT INTO foreground_activity VALUES (?,?,?,?,?)',
                        ('stale',self.run,os.getpid(),run_safety.process_birth(os.getpid())-1,'stale screenshot'))
        self.assertEqual(self.signal()[0],('green','运行中'))

    def test_direct_control_call_stays_green_but_keyboard_is_yellow(self):
        for action,color in [('Invoke','green'),('Scroll','green'),('Key','yellow'),('SendText','yellow')]:
            with self.subTest(action=action):
                def execute(*args,**kwargs):
                    self.assertEqual(self.signal()[0][0],color)
                    return Mock(returncode=0,stdout=b'{}')
                with patch('safe_action.subprocess.run',side_effect=execute):
                    safe_action.dispatch(self.db,self.run,None,['pwsh','guarded-uia-action.ps1','-Action',action])
        self.assertIsNone(foreground_activity.current(self.db,self.run))

    def test_text_only_card_and_mouse_modes(self):
        for command,color in [(['capture-card.ps1','-NoImage'],'green'),(['capture-card.ps1'],'yellow'),(['move-click.ps1'],'yellow')]:
            with self.subTest(command=command),foreground_activity.track(self.db,self.run,command):
                self.assertEqual(self.signal()[0][0],color)

    def test_managed_capture_publishes_activity_while_running(self):
        def execute(*args):
            self.assertEqual(self.signal()[0],('yellow','需要前台'))
            return 0
        with patch('managed_helper._run',side_effect=execute):
            managed_helper.run(self.db,self.run,self.generation,['pwsh','resume_capture.ps1'])
        self.assertEqual(self.signal()[0],('green','运行中'))

    def test_background_operations_never_activate_window(self):
        for command in (['resume_image_pipeline.py','rapidocr'],['resume_image_pipeline.py','stitch'],
                        ['capture-card.ps1','-NoImage'],['guarded-uia-action.ps1','-Action','Invoke'],
                        ['guarded-uia-action.ps1','-Action','Scroll']):
            with self.subTest(command=command),foreground_activity.track(self.db,self.run,command):
                self.activate.assert_not_called()

    def test_foreground_operation_activates_after_yellow_signal_and_cleans_failure(self):
        def activate():
            self.assertEqual(self.signal()[0],('yellow','需要前台'))
            raise RuntimeError('fixture activation failed')
        self.activate.side_effect=activate
        with self.assertRaises(RuntimeError):
            with foreground_activity.track(self.db,self.run,['resume_capture.ps1']):
                self.fail('operation must not start before foreground activation succeeds')
        self.assertIsNone(foreground_activity.current(self.db,self.run))

    def test_overlay_refresh_does_not_activate_or_maximize_window(self):
        overlay=progress_window.ProgressWindow.__new__(progress_window.ProgressWindow)
        overlay.root=Mock();overlay.timer=None;overlay.demo=True;overlay.wake=Mock()
        overlay.read=Mock(return_value=progress_window.snapshot(self.db,self.run,self.root))
        overlay.status_canvas=Mock();overlay.button_canvas=Mock()
        overlay.state_dot=1;overlay.state_item=2;overlay.detail_item=3
        overlay.button_texts=[4,5,6];overlay.button_rects=[7,8,9];overlay.detail_metrics_key=None
        with patch('progress_window.ensure_codex_maximized') as maximize:
            overlay.refresh()
            overlay.refresh()
            maximize.assert_not_called()
        self.activate.assert_not_called()

    def test_error_overrides_foreground_and_pause_is_gray(self):
        for payload,state,color in [
            (dict(error='capture failed'),'running','red'),
            (dict(scheduler_state='needs_attention'),'running','red'),
            (dict(scheduler_state='needs_page'),'running','red'),
            (dict(warnings=['report write failed']),'running','red'),
            (dict(error='return to foreground',foreground_required=True),'paused','yellow'),
            ({},'paused','gray'),
        ]:
            with self.subTest(payload=payload,state=state):
                self.db.execute('''CREATE TABLE IF NOT EXISTS workflow_state(run_id TEXT PRIMARY KEY,
                    phase TEXT,payload TEXT,updated_at TEXT)''')
                self.db.execute('INSERT OR REPLACE INTO workflow_state VALUES (?,?,?,?)',
                                (self.run,'read',json.dumps(payload),'now'))
                self.db.execute('UPDATE run_control SET state=? WHERE run_id=?',(state,self.run))
                with foreground_activity.track(self.db,self.run,['resume_capture.ps1']):
                    self.assertEqual(self.signal()[0][0],color)


if __name__=='__main__':unittest.main()
