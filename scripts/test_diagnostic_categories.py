"""Expected interruptions stay distinct from actionable bugs in current and old reports."""
import json
import subprocess
import unittest
from unittest.mock import patch
from openpyxl import Workbook
import candidate_log
import capture_control
import capture_resume
import ledger
import resume_diagnostics as diagnostics
import run_safety
import test_capture_control as fixtures


class DiagnosticCategoryTests(unittest.TestCase):
    def setUp(self):
        fixtures.CaptureControlTests.setUp(self)
        candidate_log.table(self.db)

    def sheet(self,rows=()):
        book=Workbook()
        run=ledger.run_row(self.db,self.run)
        diagnostics.append_sheet(book,self.db,run['profile_path'],run['started_at'],run_id=self.run,report_rows=rows)
        return book['运行状态']

    def test_legacy_normal_interruptions_and_real_program_bugs_are_separated(self):
        for message,expected in [('bound_codex_iab_not_foreground',diagnostics.NORMAL),
                                 ('ValueError: helper_cancelled',diagnostics.NORMAL),
                                 ('resume_capture_geometry_changed',diagnostics.NORMAL),
                                 ('UnicodeDecodeError: invalid UTF-8; helper_cancelled',diagnostics.BUG),
                                 ('ocr_not_complete_no_assessment',diagnostics.BUG),
                                 ('PermissionError: access denied',diagnostics.BUG)]:
            with self.subTest(message=message):
                self.assertEqual(diagnostics.classification(message),expected)

    def test_normal_interruptions_are_recorded_without_failure_event(self):
        error=capture_control.CaptureInterrupted('截图区域已改变',normal=True)
        diagnostics.record(self.db,self.run,'synthetic','电子简历采集中断',error,event='resume_interrupted')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM run_audit WHERE event='resume_save_failed'").fetchone()[0],0)
        self.assertEqual(self.sheet()['E2'].value,diagnostics.NORMAL)

    def test_historical_rows_are_reclassified_without_rewriting_audit(self):
        originals=[]
        for message in ('bound_codex_iab_not_foreground','ValueError: helper_cancelled','UnicodeDecodeError: bad byte'):
            detail=json.dumps(dict(candidate_id='synthetic',candidate_hash='synthetic',stage='电子简历采集/保存',reason=message))
            originals.append(detail)
            self.db.execute('INSERT INTO run_audit(run_id,at,event,detail) VALUES (?,?,?,?)',
                            (self.run,ledger.iso(ledger.now()),'resume_save_failed',detail))
        sheet=self.sheet()
        self.assertEqual([sheet.cell(i,5).value for i in (2,3,4)],[diagnostics.NORMAL,diagnostics.NORMAL,diagnostics.BUG])
        self.assertEqual(sheet['E4'].fill.fgColor.rgb,'00FDE9E7')
        self.assertEqual([r[0] for r in self.db.execute('SELECT detail FROM run_audit')],originals)

    def test_manual_stop_is_normal_even_without_a_candidate(self):
        run_safety.request_stop(self.db,self.run,'manual_stop')
        sheet=self.sheet()
        self.assertEqual(sheet['E2'].value,diagnostics.NORMAL)
        self.assertIn('手动结束',sheet['F2'].value)

    def test_list_only_no_screenshot_is_normal_but_unexplained_missing_file_is_bug(self):
        row=dict(evaluation_mode='resume',evaluation_input=json.dumps(dict(evaluation_stage='list')),
                 resume_image_path=None,resume_archive_status='not_applicable',eligibility_json='{}',
                 updated_at=ledger.iso(ledger.now()),run_id=self.run,candidate_name='虚构测试人',
                 pdf_status='not_applicable',pdf_note='',resume_archive_note='')
        self.assertEqual(self.sheet([row])['E2'].value,diagnostics.NORMAL)
        row['evaluation_input']='{}'
        self.assertEqual(self.sheet([row])['E2'].value,diagnostics.BUG)

    def test_real_bug_is_not_hidden_by_concurrent_manual_stop(self):
        run_safety.request_stop(self.db,self.run,'manual_stop')
        error=subprocess.CalledProcessError(1,['synthetic'],stderr=b'UnicodeDecodeError: bad byte')
        with patch('capture_resume._capture',side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError):
                capture_resume.capture(self.db,self.run,'synthetic',1,self.root/'capture')
        data=json.loads(self.db.execute("SELECT detail FROM run_audit WHERE event='resume_save_failed'").fetchone()[0])
        self.assertEqual(data['classification'],diagnostics.BUG)


if __name__=='__main__':unittest.main()
