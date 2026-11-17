"""Offline Browser handoff regressions; synthetic candidates, no website messages."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import browser_bridge
import capture_control
import capture_resume
import ledger
import startup_plan
import workflow_handoff
from test_hr_job import document
from workflow_browser import BrowserAdapter, HybridAdapter
from workflow_runner import Runner, resolve_uia_binding


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.dict(os.environ, {'BOSS_STATE_DIR': str(self.root/'state')}))
        profile = self.root/'Company'/'job.md'
        profile.parent.mkdir()
        profile.write_text(document(resume_words='组装').replace('AI总评：关','AI总评：开'), encoding='utf-8')
        with patch.object(ledger, 'PROFILE_ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
            self.db = ledger.connect(self.root/'ledger.sqlite')
            ledger.start(self.db, argparse.Namespace(profile=profile, target=2, max_views=4, min_score=60))
        self.stack.callback(self.db.close)
        self.run = self.db.execute('SELECT run_id FROM runs').fetchone()[0]
        (self.root/'workflow').mkdir()
        self.stack.enter_context(patch('browser_bridge.workflow_dir', return_value=self.root/'workflow'))
        self.stack.enter_context(patch('workflow_runner.workflow_dir', return_value=self.root/'workflow'))
        self.tab = dict(provider='browser-plugin', browser='iab', tab_id='test-tab',
                        url='https://www.zhipin.com/web/chat/recommend')
        self.source = self.root/'binding.json'
        startup_plan.write(self.source, self.tab)
        browser_bridge.binding(self.db, self.run, self.source)
        self.bridge = browser_bridge.Bridge(self.db, self.run, self.tab)

    def service(self, result, operation='select'):
        request = browser_bridge.pending(self.db, self.run)
        self.assertEqual(request['operation'], operation)
        browser_bridge.claim(self.db, self.run, request['request_id'])
        browser_bridge.complete(self.db, self.run, request['request_id'], result)
        return request

    def test_tool_handoff_roundtrip_is_visible_and_consumed(self):
        Runner(self.db, self.run, Mock(), self.root)
        def service(_):
            state = workflow_handoff.snapshot(self.db, self.run)
            self.assertEqual(state['state'], 'needs_browser')
            self.assertEqual(state['request']['binding'], self.tab)
            self.service(dict(candidate=None))
        with patch('browser_bridge.time.sleep', side_effect=service), patch('subprocess.run', side_effect=AssertionError('no native UI')):
            self.assertEqual(self.bridge.request('select'), dict(candidate=None))
        self.assertIsNone(browser_bridge.pending(self.db, self.run))
        self.assertNotEqual(workflow_handoff.snapshot(self.db, self.run)['state'], 'needs_browser')

    def test_one_claim_only(self):
        def service(_):
            request = browser_bridge.pending(self.db, self.run)
            browser_bridge.claim(self.db, self.run, request['request_id'])
            with self.assertRaisesRegex(ValueError, 'not_pending'):
                browser_bridge.claim(self.db, self.run, request['request_id'])
            browser_bridge.complete(self.db, self.run, request['request_id'], {})
        with patch('browser_bridge.time.sleep', side_effect=service):
            self.bridge.request('close')

    def test_pause_rejects_result_and_cancels_pending_action(self):
        def pause(_):
            request = browser_bridge.pending(self.db, self.run)
            browser_bridge.claim(self.db, self.run, request['request_id'])
            self.db.execute("UPDATE run_control SET state='paused' WHERE run_id=?", (self.run,))
            with self.assertRaises(capture_control.CaptureInterrupted):
                browser_bridge.complete(self.db, self.run, request['request_id'], {})
        with patch('browser_bridge.time.sleep', side_effect=pause):
            with self.assertRaises(capture_control.CaptureInterrupted):
                self.bridge.request('close')
        self.assertIsNone(browser_bridge.pending(self.db, self.run))

    def test_expiry_prevents_claim(self):
        clock = [100.0]
        def expire(_):
            clock[0] += 11
            request = browser_bridge.pending(self.db, self.run)
            with self.assertRaisesRegex(ValueError, 'expired'):
                browser_bridge.claim(self.db, self.run, request['request_id'])
        with patch('browser_bridge.time.time', side_effect=lambda: clock[0]), patch('browser_bridge.time.sleep', side_effect=expire):
            with self.assertRaisesRegex(ValueError, 'expired'):
                self.bridge.request('colleague', timeout=10)
        self.assertIsNone(browser_bridge.pending(self.db, self.run))

    def test_dead_runner_request_cannot_be_claimed(self):
        def service(_):
            request = browser_bridge.pending(self.db, self.run)
            with patch('run_safety.process_birth', side_effect=ProcessLookupError('exited')):
                with self.assertRaisesRegex(ValueError, 'owner_exited'):
                    browser_bridge.claim(self.db, self.run, request['request_id'])
            raise RuntimeError('test complete')
        with patch('browser_bridge.time.sleep', side_effect=service):
            with self.assertRaisesRegex(RuntimeError, 'test complete'):
                self.bridge.request('open')

    def test_foreign_tab_reply_is_rejected(self):
        def wrong(_):
            request = browser_bridge.pending(self.db, self.run)
            startup_plan.write(request['response_file'], dict(request_id=request['request_id'],
                binding=dict(self.tab, tab_id='other-tab'), generation=request['generation'], result={}))
        with patch('browser_bridge.time.sleep', side_effect=wrong):
            with self.assertRaisesRegex(ValueError, 'response_mismatch'):
                self.bridge.request('read')

    def test_binding_rejects_native_and_foreign_urls(self):
        for changed in ({'provider':'uia'}, {'browser':'chrome'}, {'url':'https://zhipin.com.attacker.test'},
                        {'url':'http://www.zhipin.com'}, {'url':'https://name:secret@www.zhipin.com'}, {'tab_id':''}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                browser_bridge.validate_binding(dict(self.tab, **changed))

    def test_run_cannot_silently_switch_tabs(self):
        startup_plan.write(self.source, dict(self.tab, tab_id='other-tab'))
        with self.assertRaisesRegex(ValueError, 'binding_changed'):
            browser_bridge.binding(self.db, self.run, self.source)

    def test_uia_binding_defaults_beside_browser_binding(self):
        uia = self.source.with_name('uia-binding.json')
        uia.write_text('{}', encoding='utf-8')
        self.assertEqual(resolve_uia_binding(self.source), uia.resolve())
        other = self.root/'other'
        other.mkdir()
        self.assertIsNone(resolve_uia_binding(other/'browser-binding.json'))

    def test_sending_requires_business_check_at_claim(self):
        def service(_):
            request = browser_bridge.pending(self.db, self.run)
            with patch('safe_action.business_check', side_effect=ValueError('assessment_not_eligible')):
                with self.assertRaisesRegex(ValueError, 'assessment_not_eligible'):
                    browser_bridge.claim(self.db, self.run, request['request_id'])
            raise RuntimeError('test complete')
        with patch('browser_bridge.time.sleep', side_effect=service):
            with self.assertRaisesRegex(RuntimeError, 'test complete'):
                self.bridge.request('send', dict(candidate=dict(candidate_id='synthetic')))

    def test_no_slot_means_no_send_claim(self):
        def service(_):
            request = browser_bridge.pending(self.db, self.run)
            with patch('safe_action.business_check'):
                with self.assertRaisesRegex(ValueError, 'requires_reserved_quota'):
                    browser_bridge.claim(self.db, self.run, request['request_id'])
            raise RuntimeError('test complete')
        with patch('browser_bridge.time.sleep', side_effect=service):
            with self.assertRaisesRegex(RuntimeError, 'test complete'):
                self.bridge.request('send', dict(candidate=dict(candidate_id='synthetic')))

    def adapter(self):
        with patch('workflow_browser.workflow_dir', return_value=self.root/'workflow'):
            return BrowserAdapter(self.db, self.run, self.root, self.tab)

    def test_verify_never_dispatches_send(self):
        adapter = self.adapter()
        adapter.call = Mock(return_value=dict(label='继续沟通'))
        self.assertEqual(adapter.verify(dict(candidate_id='synthetic'), 'resume'), dict(state='sent'))
        self.assertEqual(adapter.call.call_args.args[0], 'verify')

    def test_sent_without_platform_label_stays_unknown(self):
        adapter = self.adapter()
        adapter.platform_contact_state = Mock(return_value=dict(already_contacted=False))
        adapter.call = Mock(return_value=dict(state='sent'))
        with patch('safe_action.business_check'):
            self.assertEqual(adapter.send(dict(candidate_id='synthetic'), 'resume')['state'], 'unknown')

    def test_already_contacted_does_not_click_send(self):
        adapter = self.adapter()
        adapter.platform_contact_state = Mock(return_value=dict(already_contacted=True))
        adapter.call = Mock()
        with patch('safe_action.business_check'):
            self.assertEqual(adapter.send(dict(candidate_id='synthetic'), 'resume')['state'], 'not-sent')
        adapter.call.assert_not_called()

    def test_short_resume_requires_verified_capture_and_preserves_all_text(self):
        adapter = self.adapter()
        text = self.root/'ocr.txt'
        text.write_text('教育经历：机械', encoding='utf-8')
        adapter.call = Mock(return_value=dict(read_complete=True, resume_text='',
            expectation_text='期望岗位：组装', advantage_text='个人优势：焊接', capture=dict(pages=[])))
        evidence = dict(resume_evidence=dict(ocr_text=str(text)))
        with patch('capture_resume.import_browser_capture', return_value=evidence) as capture:
            result = adapter.read(dict(candidate_id='synthetic'), 'resume')
        self.assertTrue(result['read_complete'])
        for word in ('组装', '焊接', '机械'):
            self.assertIn(word, result['keyword_text'])
        capture.assert_called_once()

    def test_unread_region_does_not_run_ocr_or_pass(self):
        adapter = self.adapter()
        adapter.call = Mock(return_value=dict(read_complete=False, overview_text='部分经历'))
        with patch('capture_resume.import_browser_capture') as capture:
            self.assertFalse(adapter.read(dict(candidate_id='synthetic'), 'resume')['read_complete'])
        capture.assert_not_called()

    def test_scheduler_uses_browser_requests_through_first_greeting(self):
        self.exercise_first_greeting()

    def test_crash_after_click_resumes_verify_without_replaying_send(self):
        self.exercise_first_greeting(lose_reply=True)

    def exercise_first_greeting(self, lose_reply=False):
        candidate = dict(candidate_id='synthetic', candidate_name='测试候选人',
            card_runtime='test-visit', business_id='test-id', summary='组装经验',
            bounds=dict(x=0, y=0, width=100, height=100), scroll_percent=0)
        operations = []
        adapter = self.adapter()
        adapter.allow_ocr = False  # This synthetic test exercises the explicit no-OCR option.
        runner = Runner(self.db, self.run, adapter, self.root)
        responses = dict(close=dict(state='already_closed'), select=dict(candidate=candidate),
            filter_state=dict(state='read', count=1), prefilter=dict(card=dict(readable_text='组装经验'), raw_text='组装经验'),
            open=dict(state='opened', candidate_id='synthetic'), platform_state=dict(label='打招呼'),
            colleague=dict(state='empty', records=[], records_complete=True, lookup_completed=True, evidence='empty synthetic panel'),
            read=dict(read_complete=True, keyword_text='组装工作经历'), send=dict(state='sent', label='继续沟通'),
            verify=dict(label='继续沟通'))
        def service(_):
            request = browser_bridge.pending(self.db, self.run)
            operation = request['operation']
            operations.append(operation)
            if operation == 'send':
                saved = self.db.execute('SELECT phase FROM workflow_state WHERE run_id=?', (self.run,)).fetchone()
                self.assertEqual(saved['phase'], 'verify')
                if lose_reply:
                    browser_bridge.claim(self.db, self.run, request['request_id'])
                    raise KeyboardInterrupt('synthetic worker exits after click, before reply')
            self.service(responses[operation], operation)
        with patch('browser_bridge.time.sleep', side_effect=service), patch('subprocess.run', side_effect=AssertionError('no native UI')), patch('candidate_log.workbook'):
            for _ in range(20):
                runner.save()
                try:
                    status = runner.step()
                except KeyboardInterrupt:
                    runner = Runner(self.db, self.run, adapter, self.root)
                    self.assertEqual(runner.phase, 'verify')
                    continue
                if status and status.get('state', '').startswith('needs_'):
                    request = json.loads(Path(status['request_file']).read_text(encoding='utf-8-sig'))
                    self.assertEqual(request['kind'], 'summary')
                    startup_plan.write(status['response_file'], dict(pros='实际命中组装经验', cons='其他经验未核实'))
                if runner.phase == 'favorite':
                    break
        self.assertEqual(operations.count('send'), 1)
        self.assertEqual(operations.count('verify'), int(lose_reply))
        self.assertLess(operations.index('colleague'), operations.index('read'))
        self.assertLess(operations.index('read'), operations.index('send'))
        self.assertEqual(self.db.execute('SELECT status FROM candidates WHERE run_id=?', (self.run,)).fetchone()[0], 'sent')

    def hybrid(self):
        with patch('workflow_windows.workflow_dir', return_value=self.root/'workflow'):
            return HybridAdapter(self.db, self.run, self.root, 123, self.tab)

    def test_hybrid_send_and_verify_stay_in_background_uia(self):
        adapter = self.hybrid()
        adapter.query = Mock(side_effect=[
            dict(state='found', match=dict(label='打招呼', target=dict(name='打招呼'))),
            dict(state='found', match=dict(label='继续沟通')), ])
        adapter.invoke = Mock()
        with patch.object(adapter.bridge, 'request', side_effect=AssertionError('unexpected Browser handoff')):
            self.assertEqual(adapter.send(dict(candidate_id='synthetic'), 'resume'), dict(state='sent'))
        adapter.invoke.assert_called_once()

    def test_hybrid_capture_uses_one_browser_request(self):
        adapter = self.hybrid()
        folder = self.root/'capture'
        folder.mkdir()
        candidate = dict(candidate_id='synthetic', candidate_name='测试候选人')
        capture = dict(candidate_id='synthetic', topConfirmed=True, bottomConfirmed=True,
                       contentStable=True, occluded=False, evidence='complete', pages=[])
        adapter.bridge.request = Mock(return_value=capture)
        imported = dict(state='ready_for_assessment', resume_evidence=dict(image='x'))
        with patch('capture_resume.import_browser_capture', return_value=imported) as importer:
            self.assertEqual(adapter.capture(candidate, folder), imported)
        adapter.bridge.request.assert_called_once()
        self.assertEqual(adapter.bridge.request.call_args.args[0], 'capture')
        importer.assert_called_once_with(self.db, self.run, 'synthetic', folder.resolve(), capture)

    def test_hybrid_resume_read_uses_uia_then_one_capture(self):
        adapter = self.hybrid()
        adapter.dismiss_related = Mock()
        adapter.query = Mock(return_value=dict(resume_text='', read_complete=False))
        text = self.root/'hybrid-ocr.txt'
        text.write_text('组装工作经历', encoding='utf-8')
        adapter.capture = Mock(return_value=dict(
            resume_evidence=dict(image='x', ocr_text=str(text), ocr_json='x')))
        with patch('workflow_windows.ledger.run_row', return_value=dict()), \
             patch('workflow_windows.recruiting_rules.run_rules', return_value=dict(list_prefilter=True)), \
             patch('candidate_checks.require_resume'):
            result = adapter.read(dict(candidate_id='synthetic'), 'resume')
        self.assertTrue(result['read_complete'])
        self.assertIn('组装工作经历', result['keyword_text'])
        adapter.query.assert_called_once_with('ResumeFull')
        adapter.capture.assert_called_once()

class BrowserCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.candidate = 'synthetic'
        self.capture = dict(candidate_id=self.candidate, topConfirmed=True, bottomConfirmed=True,
            contentStable=True, occluded=False, evidence='synthetic complete viewport', pages=[])
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('capture_resume.ledger.run_row', return_value={'generation':1}))
        self.stack.enter_context(patch('capture_resume.check_candidate'))

    def page(self, name, offset):
        from resume_image_pipeline import write_image
        import numpy as np
        path = self.folder/name
        write_image(path, np.full((100, 100, 3), 255, dtype=np.uint8))
        return dict(image=str(path), offset=offset)

    def test_complete_single_page_runs_only_local_image_tools(self):
        self.capture['pages'] = [self.page('page-001.jpg', 0)]
        commands = []
        def execute(command, **kwargs):
            commands.append(command)
            import subprocess
            if 'stitch' in command:
                return subprocess.run(command, **kwargs)
            (self.folder/'resume.ocr.txt').write_text('组装经历', encoding='utf-8')
            (self.folder/'resume.ocr.json').write_text('{"state":"ok"}', encoding='utf-8')
            return Mock(stdout=b'{"state":"ok"}')
        result = capture_resume.import_browser_capture(None, 'test', self.candidate, self.folder, self.capture, execute)
        self.assertEqual(result['state'], 'ready_for_assessment')
        self.assertTrue((self.folder/'resume-long.png').is_file())
        self.assertTrue(all('resume_image_pipeline.py' in str(c[1]) for c in commands))

    def test_missing_bottom_or_occluded_or_other_candidate_rejects(self):
        for changes in ({'bottomConfirmed':False}, {'occluded':True}, {'contentStable':False}, {'candidate_id':'other'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'not_complete'):
                capture_resume.import_browser_capture(None, 'test', self.candidate, self.folder, dict(self.capture, **changes))

    def test_capture_gaps_reject_before_ocr(self):
        self.capture['pages'] = [self.page('page-001.jpg', 0), self.page('page-002.jpg', 110)]
        with self.assertRaisesRegex(ValueError, 'offsets_gap'):
            capture_resume.import_browser_capture(None, 'test', self.candidate, self.folder, self.capture)

    def test_non_jpeg_inline_bytes_reject(self):
        import base64
        self.capture['pages'] = [dict(jpeg_base64=base64.b64encode(b'not a screenshot').decode(), offset=0)]
        with self.assertRaisesRegex(ValueError, 'jpeg_bytes_required'):
            capture_resume.import_browser_capture(None, 'test', self.candidate, self.folder, self.capture)

    def test_outside_capture_directory_rejects_before_ocr(self):
        with tempfile.TemporaryDirectory() as other:
            path = Path(other)/'page.jpg'
            path.write_bytes(b'test')
            self.capture['pages'] = [dict(image=str(path), offset=0)]
            with self.assertRaisesRegex(ValueError, 'outside_candidate_directory'):
                capture_resume.import_browser_capture(None, 'test', self.candidate, self.folder, self.capture)


if __name__ == '__main__':
    unittest.main()
