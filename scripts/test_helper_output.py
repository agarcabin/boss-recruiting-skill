"""Real harmless child processes reproduce mixed-encoding failures and exit codes."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import capture_control
import capture_resume
import foreground_activity
import managed_helper
import powershell_host
import resume_diagnostics
import test_capture_control as fixtures
from windows_process import decode_output,hidden_options


class HelperOutputTests(unittest.TestCase):
    setUp=fixtures.CaptureControlTests.setUp

    def child(self,message,encoding='gbk',code=37):
        data=message.encode(encoding)
        return [sys.executable,'-c',
                'import os,sys;os.write(2,bytes.fromhex('+repr(data.hex())+'));sys.exit('+str(code)+')']

    def test_real_gbk_foreground_error_keeps_reason_and_original_bytes(self):
        text='子进程前置失败：bound_codex_iab_not_foreground'
        with patch('foreground_activity.powershell_host.command',return_value=self.child(text)):
            with self.assertRaises(capture_control.CaptureInterrupted) as caught:
                foreground_activity.activate()
        self.assertTrue(caught.exception.foreground_required)
        self.assertEqual(caught.exception.__cause__.stderr,text.encode('gbk'))
        self.assertEqual(caught.exception.__cause__.returncode,37)

    def test_real_utf8_binding_error_is_an_interruption_not_save_failure(self):
        text='窗口绑定发生变化：codex_iab_chat_changed'
        with patch('foreground_activity.powershell_host.command',return_value=self.child(text,'utf-8')):
            with self.assertRaises(capture_control.CaptureInterrupted) as caught:
                foreground_activity.activate()
        self.assertFalse(caught.exception.foreground_required)
        self.assertIn(text,str(caught.exception))

    def test_arbitrary_binary_stderr_cannot_crash_a_reader_thread(self):
        data=b'failure: \xff\xfe\x81\xff'
        command=[sys.executable,'-c','import os,sys;os.write(2,bytes.fromhex('+repr(data.hex())+'));sys.exit(37)']
        with patch('foreground_activity.powershell_host.command',return_value=command):
            with self.assertRaises(capture_control.CaptureInterrupted) as caught:
                foreground_activity.activate()
        self.assertEqual(caught.exception.__cause__.stderr,data)
        self.assertIn('failure:',str(caught.exception))

    def test_capture_failure_preserves_exit_code_and_chinese_diagnostic(self):
        text='测试文件写入失败'
        def execute(command,**options):
            self.assertNotIn('encoding',options)
            self.assertNotIn('text',options)
            return subprocess.run(self.child(text),**options)
        with patch('capture_resume.check_candidate'):
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                capture_resume.capture(self.db,self.run,'synthetic',1,self.root/'capture',execute=execute)
        self.assertEqual(caught.exception.returncode,37)
        self.assertEqual(caught.exception.stderr,text.encode('gbk'))
        diagnostic=json.loads(self.db.execute("SELECT detail FROM run_audit WHERE event='resume_save_failed'").fetchone()[0])
        self.assertIn(text,diagnostic['reason'])

    def test_real_managed_child_forwards_binary_streams_and_exit_code(self):
        stdout=io.BytesIO();stderr=io.BytesIO()
        command=[sys.executable,'-c',
                 "import os,sys;os.write(1,b'x'*100000);os.write(2,bytes.fromhex('d7d3bdf8b3cc'));sys.exit(37)"]
        with patch('managed_helper.sys.stdout',SimpleNamespace(buffer=stdout)),patch('managed_helper.sys.stderr',SimpleNamespace(buffer=stderr)):
            code=managed_helper.run(self.db,self.run,self.generation,command)
        self.assertEqual(code,37)
        self.assertEqual(len(stdout.getvalue()),100000)
        self.assertEqual(decode_output(stderr.getvalue()),'子进程')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM run_helpers').fetchone()[0],0)

    def test_registration_error_cleans_already_started_child(self):
        process=Mock(pid=123456)
        process.poll.return_value=None
        with patch('managed_helper.subprocess.Popen',return_value=process),patch('managed_helper.run_safety.process_birth',side_effect=RuntimeError('fixture registration failure')):
            with self.assertRaisesRegex(RuntimeError,'registration failure'):
                managed_helper.run(self.db,self.run,self.generation,['synthetic'])
        process.kill.assert_called_once()
        process.wait.assert_called_once()

    def test_interruption_round_trip_keeps_yellow_flag_and_avoids_failure_event(self):
        stderr=io.BytesIO()
        args=['managed_helper.py','--db',str(self.root/'ledger.sqlite'),'--run',self.run,
              '--generation',str(self.generation),'--','resume_capture.ps1']
        interrupted=capture_control.CaptureInterrupted('无法前置窗口，请继续。',foreground_required=True)
        with patch.object(sys,'argv',args),patch('managed_helper.run',side_effect=interrupted),patch('managed_helper.sys.stderr',SimpleNamespace(buffer=stderr)):
            with self.assertRaises(SystemExit) as exit_result:managed_helper.main()
        self.assertEqual(exit_result.exception.code,20)
        message=json.loads(stderr.getvalue())
        self.assertTrue(message['foreground_required'])
        self.assertNotIn(b'Traceback',stderr.getvalue())
        error=subprocess.CalledProcessError(20,['synthetic'],stderr=stderr.getvalue())
        with patch('capture_resume._capture',side_effect=error):
            with self.assertRaises(capture_control.CaptureInterrupted) as caught:
                capture_resume.capture(self.db,self.run,'synthetic',1,self.root/'capture')
        self.assertTrue(caught.exception.foreground_required)
        self.assertEqual(str(caught.exception),'无法前置窗口，请继续。')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM run_audit WHERE event='resume_save_failed'").fetchone()[0],0)

    def test_real_powershell_chinese_failure_is_utf8_on_the_wire(self):
        header=Path(__file__).with_name('request-boss-foreground.ps1').read_text(encoding='utf-8').split('Add-Type',1)[0]
        script=self.root/'synthetic-output.ps1'
        script.write_text(header+"[Console]::Error.WriteLine('子进程错误测试'); exit 37",encoding='utf-8')
        result=subprocess.run(powershell_host.command(script),capture_output=True,**hidden_options())
        self.assertEqual(result.returncode,37)
        self.assertIn('子进程错误测试',result.stderr.decode('utf-8-sig'))

    def test_real_foreground_entry_rejects_missing_binding_without_losing_error(self):
        # The nonexistent binding stops the real entry before any window operation.
        with patch.dict(os.environ,{'BOSS_BROWSER_BINDING':str(self.root/'missing-binding.json')}):
            with self.assertRaises(capture_control.CaptureInterrupted) as caught:
                foreground_activity.activate()
        self.assertIn('codex_iab_binding_required',str(caught.exception))
        self.assertIn('codex_iab_binding_required',caught.exception.__cause__.stderr.decode('utf-8-sig'))


if __name__=='__main__':unittest.main()
