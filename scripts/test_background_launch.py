"""Windows error-5 fallback without weakening the original job boundary."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
from unittest.mock import Mock,patch

import background_launch
import launch_progress


class BackgroundLaunchTests(unittest.TestCase):
    def test_only_create_process_access_denied_uses_broker(self):
        pythonw=Path(sys.executable).with_name('pythonw.exe')
        denied=OSError(5,'Access is denied')
        denied.winerror=5
        with patch.object(launch_progress.subprocess,'Popen',side_effect=denied), \
                patch.object(background_launch,'launch',return_value=Mock(pid=123)) as broker:
            self.assertEqual(launch_progress.launch_process([str(pythonw),'overlay.py']).pid,123)
        broker.assert_called_once()

    def test_other_start_errors_are_not_bypassed(self):
        pythonw=Path(sys.executable).with_name('pythonw.exe')
        missing=OSError(2,'Not found')
        missing.winerror=2
        with patch.object(launch_progress.subprocess,'Popen',side_effect=missing), \
                patch.object(background_launch,'launch') as broker:
            with self.assertRaises(OSError):launch_progress.launch_process([str(pythonw),'overlay.py'])
        broker.assert_not_called()

    def test_broker_requires_the_packaged_pythonw(self):
        with self.assertRaisesRegex(ValueError,'bundled_pythonw'):
            background_launch.launch([str(Path(sys.executable)),'worker.py'])

    def test_broker_environment_does_not_include_unrelated_process_values(self):
        environment={'PATH':'safe','BOSS_BROWSER_BINDING':'binding','UNRELATED_SECRET':'must-not-copy',
                     'LOCALAPPDATA':'local','APPDATA':'roaming','TEMP':'temp'}
        selected={key:value for key,value in environment.items() if key.startswith('BOSS_') or key in (
            'PATH','PYTHONUTF8','PYTHONIOENCODING','PYTHONPATH','APPDATA','LOCALAPPDATA','USERPROFILE',
            'TEMP','TMP','CODEX_HOME')}
        self.assertNotIn('UNRELATED_SECRET',selected)
        self.assertIn('BOSS_BROWSER_BINDING',selected)

    @unittest.skipUnless(os.name=='nt','Windows task broker')
    def test_broker_process_rejects_receipt_with_wrong_birth(self):
        with self.assertRaises((OSError,ValueError)):
            background_launch.BrokerProcess(os.getpid(),0,[])


if __name__=='__main__':unittest.main()
