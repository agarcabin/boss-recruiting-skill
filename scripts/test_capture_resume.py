import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import capture_resume


class CaptureResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'new-candidate'
        self.calls = []
        for target, value in [('check_candidate', None), ('ledger.run_row', {'generation': 0}),
                              ('run_safety.db_path', str(Path(self.temp.name) / 'test.db')),
                              ('powershell_host.command', ['pwsh', '-File', 'resume_capture.ps1'])]:
            p = patch('capture_resume.' + target, return_value=value)
            p.start(); self.addCleanup(p.stop)

    def execute(self, command, **kwargs):
        self.calls.append(command)
        if len(self.calls) == 1:
            image = self.out / 'resume-long.png'
            image.write_bytes(b'test-local-image')
            data = {'state': 'captured', 'bottomConfirmed': True, 'longImage': str(image)}
        else:
            (self.out / 'resume.ocr.txt').write_text('Local resume text', encoding='utf-8')
            (self.out / 'resume.ocr.json').write_text('{"state":"ok"}', encoding='utf-8')
            data = {'state': 'ok'}
        return subprocess.CompletedProcess(command, 0, json.dumps(data), '')

    def run_capture(self, execute=None):
        return capture_resume.capture(object(), 'run', 'candidate', 123, self.out, execute or self.execute)

    def test_capture_failure_never_starts_ocr(self):
        def fail(command, **kwargs):
            self.calls.append(command)
            raise subprocess.CalledProcessError(1, command, stderr='c_resume_document_missing')
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_capture(fail)
        self.assertEqual(len(self.calls), 1)

    def test_incomplete_capture_never_starts_ocr(self):
        def incomplete(command, **kwargs):
            self.calls.append(command)
            return subprocess.CompletedProcess(command, 0, '{"state":"captured","bottomConfirmed":false}', '')
        with self.assertRaisesRegex(ValueError, 'capture_not_complete'):
            self.run_capture(incomplete)
        self.assertEqual(len(self.calls), 1)

    def test_success_has_evidence_and_only_two_managed_stages(self):
        result = self.run_capture()
        self.assertEqual(result['state'], 'ready_for_assessment')
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all('managed_helper.py' in ' '.join(c) for c in self.calls))
        self.assertTrue(Path(result['resume_evidence']['ocr_text']).is_file())

    def test_ocr_failure_does_not_return_ready(self):
        def fail_ocr(command, **kwargs):
            if self.calls:
                self.calls.append(command)
                raise subprocess.CalledProcessError(1, command, stderr='ocr_failed')
            return self.execute(command, **kwargs)
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_capture(fail_ocr)
        self.assertEqual(len(self.calls), 2)

    def test_stop_after_capture_prevents_ocr(self):
        with patch('capture_resume.check_candidate', side_effect=[None, None, ValueError('run_stopped_or_finalized')]):
            with self.assertRaisesRegex(ValueError, 'run_stopped'):
                self.run_capture()
        self.assertEqual(len(self.calls), 1)

    def test_registration_failure_prevents_all_stages(self):
        with patch('capture_resume.check_candidate', side_effect=ValueError('registered_open_candidate_required')):
            with self.assertRaisesRegex(ValueError, 'registered_open'):
                self.run_capture()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.out.exists())

    def test_stale_directory_is_not_reused(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            self.run_capture()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
