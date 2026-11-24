"""Stop feedback must distinguish failed actions from unavailable UI evidence."""
import json
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import progress_window
import stop_controller
from windows_process import hidden_options


class StopFeedbackTests(unittest.TestCase):
    def test_unconfirmed_is_preserved_without_failure_alarm(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
        db.execute('CREATE TABLE runs(run_id TEXT,interrupt_status TEXT)')
        db.execute("INSERT INTO runs VALUES ('run',NULL)")
        receipt = dict(state='unconfirmed', reason='stop_or_idle_state_unavailable')
        with patch.object(stop_controller, 'bind_run', return_value={}), patch.object(stop_controller, 'binding_action', return_value=receipt), patch('error_alert.play') as alarm:
            self.assertEqual(stop_controller.interrupt_run(db, 'run'), 'unconfirmed')
        alarm.assert_not_called()
        self.assertEqual(json.loads(db.execute('SELECT value FROM settings').fetchone()[0]), receipt)
        self.assertEqual(db.execute('SELECT interrupt_status FROM runs').fetchone()[0], 'unconfirmed')

    def finish(self, status):
        window = progress_window.ProgressWindow.__new__(progress_window.ProgressWindow)
        window.termination_result = (Path('snapshot.xlsx'), None)
        window.demo, window.db_path, window.run_id = False, Path('unused'), 'run'
        window.root, window.status_canvas = Mock(), Mock()
        window.state_item, window.detail_item = 'state', 'detail'
        with patch.object(progress_window.ledger, 'connect', return_value=Mock()), patch.object(progress_window.ledger, 'run_row', return_value=dict(interrupt_status=status)), patch.object(progress_window.messagebox, 'showwarning') as warning, patch.object(progress_window.messagebox, 'askyesno', return_value=False) as ask, patch('error_alert.play') as alarm:
            window.finish_termination()
        ask.assert_called_once()
        window.root.destroy.assert_called_once()
        return warning, alarm

    def test_unknown_status_goes_directly_to_open_snapshot_choice(self):
        warning, alarm = self.finish('unconfirmed')
        warning.assert_not_called()
        alarm.assert_not_called()

    def test_real_failure_still_warns(self):
        warning, alarm = self.finish('failed: bound_chat_document_not_active')
        warning.assert_called_once()
        alarm.assert_called_once()

    def test_confirmed_and_auto_completion_do_not_warn(self):
        for status in ('interrupted', 'idle', 'not_required_auto_complete'):
            with self.subTest(status=status):
                warning, alarm = self.finish(status)
                warning.assert_not_called()
                alarm.assert_not_called()

    def test_stable_disappearance_and_reappearance(self):
        helper = Path(__file__).with_name('stop-confirmation.ps1')
        code = ". '"+str(helper).replace("'", "''")+"'; $result=@(); foreach($sequence in @(@(0,0),@(0,1,0),@(1,1),@(0,1,0,0))){$n=0;$r=$null;foreach($count in $sequence){$r=Get-StopConfirmation $count $n;$n=$r.missing_samples};$result+=,[bool]$r.confirmed}; ConvertTo-Json -Compress -InputObject $result"
        result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-Command', code], capture_output=True, text=True, timeout=10, **hidden_options())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [True, False, False, True])


if __name__ == '__main__':
    unittest.main()
