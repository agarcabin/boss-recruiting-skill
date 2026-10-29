"""Regressions found on the live BOSS page; no real UI or sends in these tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from workflow_windows import WindowsAdapter
import recruiting_rules


class LivePageRegressions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.adapter=WindowsAdapter(None,'test',self.root,hwnd=1)
        self.candidate=dict(candidate_id='actual-visit',card_runtime='1,2',open_target={'runtime_id':[1,2]})
        self.rules=json.loads(recruiting_rules.CONFIG.read_text(encoding='utf-8'))
        self.rules.update(policy='meikang',mode='resume')
        for target,value in [('workflow_windows.ledger.run_row',{}),('workflow_windows.recruiting_rules.run_rules',self.rules)]:
            patcher=patch(target,return_value=value);patcher.start();self.addCleanup(patcher.stop)

    def test_open_waits_for_document_without_reading_resume(self):
        self.adapter.invoke=Mock()
        def query(action):
            if action=='Resume':raise AssertionError('body read before colleague check')
            return {'document_target':{'runtime_id':[9]}}
        self.adapter.query=Mock(side_effect=query)
        self.adapter.open(self.candidate,'resume')
        self.adapter.invoke.assert_called_once_with(self.candidate['open_target'])
        self.assertTrue(self.adapter.detail_open)

    def test_already_open_does_not_reopen_or_read_body(self):
        self.adapter.invoke=Mock()
        def query(action):
            if action=='Resume':raise AssertionError('body read before colleague check')
            return {'document_target':{'runtime_id':[9]}}
        self.adapter.query=Mock(side_effect=query)
        self.adapter.open(dict(self.candidate,already_open=True),'resume')
        self.adapter.invoke.assert_not_called()

    def test_large_overview_does_not_hide_missing_body_from_ocr(self):
        overview='经历概览\n普通生物公司\n教育经历\n'+'已读取概览。'*60
        self.adapter.query=Mock(return_value=dict(keyword_text=overview,resume_text='',overview_text=overview))
        text=self.root/'body.txt';text.write_text('工作经历\n实际海外销售正文',encoding='utf-8')
        evidence=dict(ocr_text=str(text))
        with patch('workflow_windows.capture_resume.capture',return_value={'resume_evidence':evidence}) as capture:
            facts=self.adapter.read(self.candidate,'resume')
        capture.assert_called_once()
        self.assertIn('实际海外销售正文',facts['keyword_text'])
        self.assertIn(overview,facts['keyword_text'])
        self.assertEqual(facts['read_source'],'local_ocr_and_overview_uia')

    def test_direct_overview_still_avoids_unnecessary_ocr(self):
        overview='经历概览\n迈瑞医疗\n海外销售经理'
        self.adapter.query=Mock(return_value=dict(keyword_text=overview,resume_text='',overview_text=overview))
        with patch('workflow_windows.capture_resume.capture',side_effect=AssertionError('unnecessary OCR')):
            self.assertEqual(self.adapter.read(self.candidate,'resume')['keyword_text'],overview)

    def test_explicit_no_ocr_retains_available_evidence(self):
        overview='经历概览\n普通公司销售岗位\n'+'可读概览。'*60
        self.adapter.allow_ocr=False
        self.adapter.query=Mock(return_value=dict(keyword_text=overview,resume_text='',overview_text=overview))
        with patch('workflow_windows.capture_resume.capture',side_effect=AssertionError('OCR disabled')):
            self.assertEqual(self.adapter.read(self.candidate,'resume')['keyword_text'],overview)

    def test_readable_body_does_not_force_ocr(self):
        body='工作经历\n普通公司的真实岗位职责。'*30
        self.adapter.query=Mock(return_value=dict(keyword_text=body,resume_text=body,overview_text=''))
        with patch('workflow_windows.capture_resume.capture',side_effect=AssertionError('unnecessary OCR')):
            self.assertEqual(self.adapter.read(self.candidate,'resume')['keyword_text'],body)

    def test_ocr_failure_remains_optional_and_preserves_truthful_evidence(self):
        overview='经历概览\n实际可读内容'
        self.adapter.query=Mock(return_value=dict(keyword_text=overview,resume_text='',overview_text=overview))
        with patch('workflow_windows.capture_resume.capture',side_effect=ValueError('window_occluded')):
            facts=self.adapter.read(self.candidate,'resume')
        self.assertEqual(facts['keyword_text'],overview)
        self.assertEqual(facts['read_warning'],'window_occluded')

    def test_next_verifies_transition_without_reading_next_resume(self):
        self.adapter.detail_open=True;self.adapter.processed=[]
        self.adapter.invoke=Mock()
        successor=dict(candidate_id='second',card_runtime='3,4')
        signatures=iter(('old-structure','new-structure'))
        def query(action,**kwargs):
            if action=='Resume':raise AssertionError('next body read before colleague check')
            if action=='Select':return dict(ordered_runtime_ids=['1,2','3,4'],candidate=successor)
            if action=='Next':return dict(state='found',match=dict(target={'runtime_id':[8]}))
            return dict(document_target={'runtime_id':[9]},view_signature=next(signatures))
        self.adapter.query=Mock(side_effect=query)
        self.assertEqual(self.adapter.next(self.candidate,'resume'),dict(next_candidate=successor))

    def test_close_keyboard_fallback_only_checks_document_presence(self):
        self.adapter.detail_open=True;self.adapter.invoke=Mock()
        def query(action):
            if action=='Resume':raise AssertionError('close must not read body')
            return dict(state='unavailable') if action=='Close' else dict(document_target={'runtime_id':[9]})
        self.adapter.query=Mock(side_effect=query)
        self.adapter.close()
        self.adapter.invoke.assert_called_once_with({'runtime_id':[9]},'Key','Escape')


    def test_missing_navigation_signal_uses_list_instead_of_blind_next(self):
        self.adapter.detail_open=True;self.adapter.processed=[]
        self.adapter.invoke=Mock();self.adapter.close=Mock()
        def query(action,**kwargs):
            if action=='Resume':raise AssertionError('body read before colleague check')
            if action=='Select':return dict(ordered_runtime_ids=['1,2','3,4'],candidate={'card_runtime':'3,4'})
            if action=='Next':return dict(state='found',match={'target':{'runtime_id':[8]}})
            return dict(document_target={'runtime_id':[9]},view_signature='')
        self.adapter.query=Mock(side_effect=query)
        self.assertIsNone(self.adapter.next(self.candidate,'resume'))
        self.adapter.invoke.assert_not_called()
        self.adapter.close.assert_called_once()


if __name__=='__main__':unittest.main()
