"""User-requested control changes, tested offline against disposable ledgers."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from argparse import Namespace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import candidate_log
import capture_resume
import ledger
import progress_window
import recruiting_rules
import run_safety
import safe_action
import stop_controller
from test_ledger import PROFILE


def call(fn, db, **kwargs):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        fn(db, Namespace(**kwargs))
    return json.loads(stream.getvalue())


class RelaxedControlsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / 'profile.md'
        self.profile.write_text(PROFILE, encoding='utf-8')
        root_patch = patch.object(ledger, 'PROFILE_ROOT', self.root)
        root_patch.start(); self.addCleanup(root_patch.stop)
        self.db = ledger.connect(self.root / 'ledger.db')
        self.addCleanup(self.db.close)
        candidate_log.table(self.db)
        self.run = self.start()['run_id']

    def start(self, **overrides):
        args = dict(profile=str(self.profile), min_score=70)
        args.update(overrides)
        return call(ledger.start, self.db, **args)

    def payload(self, candidate='candidate-one', **overrides):
        data = dict(candidate_id=candidate, candidate_name='测试人', started_at=ledger.iso(ledger.now()),
                    electronic_resume_enabled=True, electronic=dict(score=80,evidence='实际已读取的海外销售经历'),
                    overall_score=80, hard_requirements=True, decision='greet',
                    pros='实际读取到海外销售经历',cons='未读到的信息保留未知',
                    coworker_progress=dict(state='empty',evidence='UIA同事面板明确无记录'))
        data.update(overrides)
        return data

    def record(self, candidate='candidate-one', **overrides):
        payload = self.payload(candidate, **overrides)
        return call(lambda db,args: candidate_log.record(db,args,payload),self.db,run=self.run,output_root=self.root)

    def reserve(self,candidate='candidate-one'):
        return call(ledger.reserve,self.db,run=self.run,candidate_id=candidate)

    def resolve(self,token,result='sent'):
        return call(ledger.resolve,self.db,token=token,result=result,min_gap=80,max_gap=100)

    def test_defaults_are_150_and_300_without_deadline(self):
        row=ledger.run_row(self.db,self.run)
        self.assertEqual((row['target'],row['max_views']),(150,300))
        self.assertEqual(row['deadline_at'],'')

    def test_larger_explicit_targets_and_views(self):
        row=ledger.run_row(self.db,self.start(target=10000,max_views=20000)['run_id'])
        self.assertEqual((row['target'],row['max_views']),(10000,20000))

    def test_invalid_negative_quantities_still_are_invalid_data(self):
        with self.assertRaises(ValueError): self.start(target=0)
        with self.assertRaises(ValueError): self.start(max_views=-1)

    def test_deprecated_duration_is_ignored(self):
        result=self.start(duration_min=1)
        self.assertIsNone(result['deadline_at'])

    def test_old_deadline_is_ignored_in_gate_status_overlay_and_stop_poll(self):
        self.db.execute('UPDATE runs SET deadline_at=? WHERE run_id=?',(ledger.iso(ledger.now()-timedelta(days=2)),self.run))
        self.assertTrue(call(ledger.gate,self.db,run=self.run)['may_start_candidate'])
        self.assertFalse(call(ledger.status,self.db,run=self.run)['run_expired'])
        self.assertEqual(progress_window.snapshot(self.db,self.run)['state'],'running')
        self.assertIsNone(stop_controller.poll(self.db,self.run,self.root,interrupt=False))

    def test_rolling_150_from_other_runs_does_not_block(self):
        stamp=ledger.iso(ledger.now())
        for _ in range(151):
            self.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)',(uuid.uuid4().hex,'other','older','sent',uuid.uuid4().hex,stamp,stamp,stamp))
        self.record()
        self.assertEqual(self.reserve()['state'],'ready')

    def test_old_cooldown_and_gap_arguments_do_not_wait(self):
        self.db.execute('INSERT INTO settings VALUES (?,?)',('next_allowed_at',ledger.iso(ledger.now()+timedelta(hours=10))))
        self.record(); result=self.reserve()
        self.assertEqual(result['state'],'ready')
        self.assertIsNone(self.resolve(result['token'])['next_allowed_at'])
        self.record('candidate-two')
        self.assertEqual(self.reserve('candidate-two')['state'],'ready')

    def test_unapproved_profile_warns_but_starts(self):
        self.profile.write_text(PROFILE.replace('approval: approved','approval: pending'),encoding='utf-8')
        result=self.start()
        self.assertEqual(result['state'],'started')
        self.assertTrue(result['warnings'])

    def test_unresolved_profile_conflicts_warn_but_start(self):
        self.profile.write_text(PROFILE.replace('## 冲突与待确认\n无','## 冲突与待确认\n- [ ] 待确认事项'),encoding='utf-8')
        self.assertEqual(self.start()['state'],'started')

    def test_no_stop_binding_and_no_binding_probe_required(self):
        with patch.object(stop_controller,'probe_binding',side_effect=AssertionError('must not probe')):
            result=self.start()
        self.assertEqual(result['state'],'started')

    def test_invalid_optional_binding_only_warns(self):
        result=self.start(stop_binding=self.root/'missing.json')
        self.assertEqual(result['state'],'started')
        self.assertTrue(result['warnings'])

    def test_excel_write_failure_does_not_block_record_or_send(self):
        with patch.object(candidate_log,'workbook',side_effect=PermissionError('Excel locked')):
            result=self.record()
        self.assertEqual(result['state'],'recorded')
        self.assertTrue(result['warnings'])
        self.assertEqual(self.db.execute('SELECT report_written FROM assessments').fetchone()[0],0)
        self.assertEqual(self.reserve()['state'],'ready')

    def test_missing_resume_archive_does_not_block(self):
        result=self.record(resume_evidence={'image':str(self.root/'absent.png'),'ocr_text':str(self.root/'absent.txt')})
        self.assertTrue(result['warnings'])
        self.assertEqual(self.reserve()['state'],'ready')

    def test_stale_other_report_archive_and_unknown_do_not_block(self):
        self.record(); first=self.reserve(); self.resolve(first['token'],'unknown')
        self.db.execute("UPDATE assessments SET report_written=0,send_status='assessed',pdf_status='pending',resume_archive_status='pending'")
        self.record('candidate-two')
        self.assertEqual(self.reserve('candidate-two')['state'],'ready')
        self.assertEqual(self.start()['state'],'started')

    def test_registration_is_automatic(self):
        self.record()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM candidate_progress').fetchone()[0],1)
        self.assertEqual(self.reserve()['state'],'ready')

    def test_unfinished_candidate_does_not_prevent_next(self):
        call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-unfinished')
        result=call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-next')
        self.assertEqual(result['state'],'started_candidate')
        self.assertEqual(result['current_candidate_number'],2)

    def test_finish_without_report_score_or_timing(self):
        call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-unfinished')
        result=call(ledger.candidate_finish,self.db,run=self.run,candidate_id='candidate-unfinished')
        self.assertEqual(result['state'],'finished_candidate')
        self.assertTrue(call(ledger.gate,self.db,run=self.run)['may_start_candidate'])

    def test_optional_ocr_real_text_can_trigger_meikang(self):
        rules=json.loads(recruiting_rules.CONFIG.read_text(encoding='utf-8'))
        rules.update(policy='meikang',mode='resume',greeting_mode='single')
        self.db.execute('UPDATE runs SET rule_snapshot=? WHERE run_id=?',(json.dumps(rules),self.run))
        self.record(keyword_text='本人负责IVD海外销售业务',overall_score=50,electronic=dict(score=50,evidence='实际读取到IVD海外销售职责'))
        self.assertEqual(self.reserve()['state'],'ready')

    def test_repeat_same_candidate_in_same_run_preserves_each_visit(self):
        self.record(); first=self.reserve(); self.resolve(first['token'])
        call(ledger.candidate_finish,self.db,run=self.run,candidate_id='candidate-one')
        call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-one',new_visit=True)
        self.record(); second=self.reserve(); self.resolve(second['token'])
        self.assertNotEqual(first['token'],second['token'])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM candidates WHERE status='sent'").fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM candidate_visits WHERE candidate_id=?',('candidate-one',)).fetchone()[0],2)

    def test_repeat_across_runs_is_not_skipped(self):
        self.record(); self.resolve(self.reserve()['token'])
        self.run=self.start()['run_id']
        self.record()
        self.assertEqual(self.reserve()['state'],'ready')

    def test_unknown_can_retry_without_manual_reconciliation(self):
        self.record(); first=self.reserve(); self.resolve(first['token'],'unknown')
        second=self.reserve()
        self.assertEqual(second['state'],'ready')
        self.assertNotEqual(first['token'],second['token'])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM message_attempt_history WHERE status='unknown'").fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM candidate_progress').fetchone()[0],1)

    def test_unknown_can_be_corrected_without_manual_flag(self):
        self.record(); first=self.reserve(); self.resolve(first['token'],'unknown')
        result=call(ledger.reconcile,self.db,token=first['token'],result='sent')
        self.assertEqual(result['state'],'sent')

    def test_dispatch_has_no_state_generation_or_credential_gate(self):
        run_safety.request_stop(self.db,self.run,'manual_stop')
        completed=subprocess.CompletedProcess(['mock'],0,b'{"state":"dispatched"}',b'')
        with patch.object(safe_action.subprocess,'run',return_value=completed) as action:
            result=safe_action.dispatch(self.db,self.run,-999,['mock'])
        self.assertEqual(result['state'],'dispatched')
        action.assert_called_once()

    def test_no_active_candidate_target_match_guard(self):
        self.assertIsNone(safe_action.validate_candidate_target(self.db,ledger.run_row(self.db,self.run),'invoke',{},None,'different'))

    def test_colleague_check_is_still_required_for_resume_sending(self):
        self.record()
        old=dict(state='first_record',first_greeting_at=ledger.iso(ledger.now()-timedelta(days=9)),evidence='实际UIA同事首条时间')
        self.db.execute('UPDATE assessments SET coworker_progress=?',(json.dumps(old),))
        self.assertEqual(self.reserve()['state'],'blocked')
        with self.assertRaises(ValueError): safe_action.business_check(self.db,self.run,'candidate-one')

    def test_job_match_and_profile_change_checks_are_retained(self):
        self.record()
        self.profile.write_text(PROFILE+'\n备注变更\n',encoding='utf-8')
        self.assertEqual(self.reserve()['reason'],'profile_changed_since_start')

    def test_requested_quantity_still_stops_exactly(self):
        self.run=self.start(target=1,max_views=10)['run_id']
        self.record(); self.resolve(self.reserve()['token'])
        self.assertEqual(run_safety.quantity_reason(self.db,self.run),'run_target_reached')

    def test_custom_view_goal_above_300_reaches_exact_count(self):
        self.run=self.start(target=1000,max_views=305)['run_id']
        for index in range(305):
            call(ledger.candidate_begin,self.db,run=self.run,candidate_id=f'candidate-{index}')
        self.assertEqual(run_safety.quantity_reason(self.db,self.run),'run_view_limit_reached')
        with self.assertRaisesRegex(ValueError,'run_view_limit_reached'):
            call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-over-limit')

    def test_single_followup_restriction_is_retained(self):
        with self.assertRaisesRegex(ValueError,'single_greeting_disallows_followups'):
            safe_action.validate_greeting_action(ledger.run_row(self.db,self.run),'send-text',{})

    def test_tokenless_cli_calls_action_and_creates_only_accounting_reference(self):
        self.record()
        target=self.root/'target.json'
        target.write_text(json.dumps(dict(name='打招呼',candidate_id='candidate-one',hwnd=1,runtime_id=[1])),encoding='utf-8')
        command=['safe_action.py','--db',str(self.root/'ledger.db'),'--run',self.run,'--target',str(target)]
        with patch.object(sys,'argv',command), patch.object(safe_action,'dispatch',return_value={'state':'dispatched'}) as action, contextlib.redirect_stdout(io.StringIO()):
            safe_action.main()
        self.assertTrue(action.called)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM message_attempts').fetchone()[0],1)

    def test_optional_capture_does_not_require_active_candidate(self):
        import candidate_checks
        candidate_checks.record(self.db,self.run,'not-registered',dict(state='empty',evidence='当前同事面板实际无记录'))
        call(ledger.candidate_finish,self.db,run=self.run,candidate_id='not-registered')
        self.assertEqual(capture_resume.check_candidate(self.db,self.run,'not-registered',-999)['run_id'],self.run)

    def test_manual_control_still_changes_state(self):
        self.assertEqual(call(ledger.control,self.db,run=self.run,action='pause')['state'],'paused')
        self.assertEqual(call(ledger.control,self.db,run=self.run,action='resume')['state'],'running')
        self.assertEqual(call(ledger.control,self.db,run=self.run,action='stop')['state'],'stopped')

    def test_sync_failure_warns_and_following_send_still_works(self):
        self.record(); self.resolve(self.reserve()['token'])
        with patch.object(candidate_log,'workbook',side_effect=PermissionError('locked')):
            result=call(candidate_log.sync,self.db,run=self.run,candidate_id='candidate-one',output_root=self.root)
        self.assertEqual(result['state'],'synced')
        self.assertTrue(result['warnings'])
        self.record('candidate-two')
        self.assertEqual(self.reserve('candidate-two')['state'],'ready')

    def test_coworker_skip_auto_registers_without_reading_resume(self):
        observation=self.root/'coworker.json'
        observation.write_text(json.dumps(dict(state='first_record',first_greeting_at=ledger.iso(ledger.now()-timedelta(days=9)),evidence='UIA首条同事时间')),encoding='utf-8')
        result=call(candidate_log.record_coworker_skip,self.db,run=self.run,candidate_id='candidate-skip',candidate_name='测试人',input=observation,output_root=self.root)
        self.assertEqual(result['decision'],'skip')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM candidate_progress').fetchone()[0],1)


if __name__=='__main__':
    unittest.main()
