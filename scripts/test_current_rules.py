"""Current keyword deduction, conditional model review and platform contact rules."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import candidate_log
import greeting_rate
import hr_job
import ledger
import overall_review
import recruiting_rules
from test_hr_job import document
from workflow_runner import Runner
from workflow_windows import WindowsAdapter


class CurrentRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.profile = self.root/'company'/'job.md';self.profile.parent.mkdir()
        self.profile.write_text(document(resume_words='A：医疗、免疫、试剂、检测\nB：海外、外贸、出口、欧洲', resume_negative='主管、经理').replace('7 天','0 天'),encoding='utf-8')
        self.rules = hr_job.snapshot(self.profile)
        self.facts = dict(keyword_text='医疗海外，负责主管工作，主管经验。',read_complete=True)

    def answer(self, req, suitable=True):
        return dict(request_id=req['request_id'],suitable=suitable,reason='根据完整经历判断',
                    pros='有医疗和海外经历',cons='主管职责需核实',quotes=['负责主管工作'])

    def runner(self, facts=None, rules=None):
        runner = Runner.__new__(Runner)
        runner.db = sqlite3.connect(':memory:');self.addCleanup(runner.db.close)
        runner.db.execute('CREATE TABLE run_audit(run_id,at,event,detail)')
        runner.run,runner.phase,runner.folder = 'r','assess',self.root
        runner.data = dict(candidate={'candidate_id':'synthetic','candidate_name':'虚构测试'},visit_hash='visit',facts=facts or self.facts)
        runner.status = lambda state=None:dict(state=state)
        runner.record_payload = Mock(side_effect=lambda p:runner.data.update(decision=p['decision']))
        run = dict(evaluation_mode='resume',rule_snapshot=json.dumps(rules or self.rules),min_score=70,
                   profile_path=str(self.profile),profile_hash=ledger.profile_hash(self.profile))
        return runner,run

    def step(self, runner, run):
        with patch('ledger.control_state',return_value='running'),patch('ledger.run_row',return_value=run):
            return runner.step()

    def test_each_distinct_negative_word_costs_ten_points(self):
        result = recruiting_rules.evaluate(self.rules,self.facts,70)
        self.assertEqual((result['score_before_experience'],result['negative_penalty'],result['score']), (70,10,60))
        result = recruiting_rules.evaluate(self.rules,dict(self.facts,keyword_text='医疗海外，主管主管，经理经理'),70)
        self.assertEqual((result['negative_penalty'],result['score']), (20,50))

    def test_remaining_qualified_generates_summary_without_overall_review(self):
        facts = dict(self.facts,keyword_text='医疗免疫试剂检测，海外外贸出口欧洲，主管')
        result = recruiting_rules.evaluate(self.rules,facts,70)
        self.assertEqual(result['score'],72)
        self.assertTrue(result['eligible'])
        self.assertIsNone(overall_review.request(self.rules,facts))
        runner,run = self.runner(facts)
        self.assertEqual(self.step(runner,run)['state'],'needs_summary')

    def test_positive_groups_must_pass_before_review(self):
        facts = dict(self.facts,keyword_text='医疗免疫试剂，主管')
        self.assertIsNone(overall_review.request(self.rules,facts))
        runner,run = self.runner(facts)
        self.step(runner,run)
        self.assertNotIn('request_file',runner.data)
        self.assertEqual(runner.data['decision'],'skip')

    def test_switch_off_skips_all_model_analysis_for_low_score(self):
        rules = json.loads(json.dumps(self.rules));rules['hr_job_config']['overall_review']=False
        runner,run = self.runner(rules=rules)
        self.step(runner,run)
        self.assertNotIn('request_file',runner.data)
        self.assertEqual(runner.data['decision'],'skip')
        self.assertEqual(runner.record_payload.call_args.args[0]['overall_score'],60)

    def test_review_can_allow_below_threshold_without_changing_rule_score(self):
        runner,run = self.runner()
        self.assertEqual(self.step(runner,run)['state'],'needs_overall_review')
        req = json.loads(Path(runner.data['request_file']).read_text(encoding='utf-8'))['evidence']
        Path(runner.data['response_file']).write_text(json.dumps(self.answer(req)),encoding='utf-8')
        self.step(runner,run)
        self.assertEqual(runner.phase,'send')
        payload = runner.record_payload.call_args.args[0]
        self.assertEqual(payload['overall_score'],60)
        self.assertEqual(payload['pros'],'有医疗和海外经历')
        self.assertEqual(runner.db.execute("SELECT count(*) FROM run_audit WHERE event='overall_review'").fetchone()[0],1)

    def test_review_unsuitable_and_invalid_or_changed_evidence_cannot_allow(self):
        req = overall_review.request(self.rules,self.facts)
        result = recruiting_rules.evaluate(self.rules,dict(self.facts,overall_review=self.answer(req,False)),70)
        self.assertFalse(result['eligible'])
        for answer in (dict(self.answer(req),request_id='old'),dict(self.answer(req),quotes=['编造经历']),dict(self.answer(req),suitable='是')):
            with self.assertRaises(ValueError):recruiting_rules.evaluate(self.rules,dict(self.facts,overall_review=answer),70)
        with self.assertRaises(ValueError):
            recruiting_rules.evaluate(self.rules,dict(self.facts,keyword_text=self.facts['keyword_text']+'新经历',overall_review=self.answer(req)),70)

    def test_incomplete_resume_never_gets_overall_review(self):
        self.assertIsNone(overall_review.request(self.rules,dict(self.facts,read_complete=False)))

    def test_review_and_notice_are_separately_timed(self):
        from workflow_runner import phase_activity
        self.assertEqual(phase_activity('assess',{'handoff_kind':'overall_review'}),
                         dict(actor='ai',activity='overall_review',requires_thinking=True))
        self.assertEqual(phase_activity('coworker',{'handoff_kind':'coworker_notice'}),
                         dict(actor='ai',activity='coworker_notice',requires_thinking=False))

    def test_migration_preserves_terms_values_and_existing_review_switch(self):
        import migrate_current_config
        text = document(resume_words='医疗、海外',resume_negative='主管')
        text = text.replace('单简历查看时间不低于：30 秒','单简历查看时间（为期望平均值）：45 秒')
        text = text.replace('连续招呼五次后额外休息：30 秒','查看十人后休息：2 分钟')
        text = text.replace('减分至合格线后AI整体复盘：开','减分至合格线后AI整体复盘：关')
        changed = migrate_current_config.update(text)
        self.assertIn('单简历查看时间不低于：45 秒',changed)
        self.assertIn('连续招呼五次后额外休息：120 秒',changed)
        self.assertNotIn('查看十人后休息',changed)
        self.assertFalse(hr_job.parse(changed)['overall_review'])
        self.assertEqual(hr_job.parse(changed)['resume']['negative'],['主管'])

    def test_rule_switch_and_deduction_apply_to_record_reserve_and_send_check(self):
        import safe_action
        with patch.object(ledger,'PROFILE_ROOT',self.root):
            db = ledger.connect(self.root/'test.sqlite');self.addCleanup(db.close)
            with contextlib.redirect_stdout(io.StringIO()):
                ledger.start(db,argparse.Namespace(profile=self.profile,target=2,max_views=4,min_score=70))
        rid = db.execute('SELECT run_id FROM runs').fetchone()[0]
        candidate_log.table(db);ledger.ensure_candidate(db,rid,'synthetic')
        req = overall_review.request(self.rules,self.facts)
        facts = dict(self.facts,overall_review=self.answer(req))
        result = recruiting_rules.evaluate(self.rules,facts,70)
        import fast_assessment
        payload = dict(fast_assessment.fill(facts,result),candidate_id='synthetic',candidate_name='虚构测试',
                       coworker_progress={'state':'disabled','evidence':'同事配置为0天'},pros='医疗海外',cons='待核实')
        with contextlib.redirect_stdout(io.StringIO()),patch('csv_report.setup_viewer',side_effect=lambda template,target,specs,configure=None:shutil.copy2(template,target)):
            candidate_log.record(db,argparse.Namespace(run=rid,output_root=self.root),payload)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):ledger.reserve(db,argparse.Namespace(run=rid,candidate_id='synthetic'))
        self.assertEqual(json.loads(out.getvalue())['state'],'ready')
        safe_action.business_check(db,rid,'synthetic')
        stored = db.execute('SELECT overall_score,evaluation_input FROM assessments').fetchone()
        self.assertEqual(stored['overall_score'],60)
        self.assertIn('overall_review',json.loads(stored['evaluation_input']))

    def test_background_finalize_never_opens_report_automatically(self):
        import run_safety,stop_controller
        with patch.object(ledger,'PROFILE_ROOT',self.root):
            db=ledger.connect(self.root/'finish.sqlite');self.addCleanup(db.close)
            with contextlib.redirect_stdout(io.StringIO()):
                ledger.start(db,argparse.Namespace(profile=self.profile,target=2,max_views=4,min_score=70))
        rid=db.execute('SELECT run_id FROM runs').fetchone()[0]
        report=self.root/'synthetic.xlsx';report.write_bytes(b'synthetic')
        run_safety.request_stop(db,rid,'manual_stop')
        with patch('stop_controller.final_report',return_value=report),patch('page_layout.restore'), \
             patch('stop_controller.report_status',return_value={'report_pending':False}), \
             patch('stop_controller.os.startfile') as open_file:
            self.assertEqual(stop_controller.finalize(db,rid,self.root,interrupt=False),report)
            open_file.assert_not_called()


class SendingTests(unittest.TestCase):
    def test_no_local_quota_even_if_old_counter_was_full(self):
        db = sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.execute('CREATE TABLE settings(key PRIMARY KEY,value)')
        db.execute('INSERT INTO settings VALUES (?,?)',('greeting_rate/v1','old-full-counter'))
        for i in range(25):
            self.assertEqual(greeting_rate.claim(db,str(i))['retry_after_seconds'],0)
        self.assertEqual(db.execute('SELECT value FROM settings').fetchone()[0],'old-full-counter')
        self.assertFalse(greeting_rate.status(db)['enabled'])

    def test_continue_chat_button_never_dispatches_first_greeting(self):
        adapter = WindowsAdapter.__new__(WindowsAdapter)
        adapter.query = Mock(return_value={'state':'found','match':{'label':'继续沟通','target':{}}})
        adapter.invoke = Mock()
        self.assertTrue(adapter.platform_contact_state({},'resume')['already_contacted'])
        self.assertEqual(adapter.send({},'resume')['reason'],'platform_already_contacted')
        adapter.invoke.assert_not_called()

    def test_coworker_receipt_is_required_before_capture(self):
        adapter = WindowsAdapter.__new__(WindowsAdapter)
        adapter.db,adapter.run,adapter.hwnd = Mock(),'r',1
        adapter.allow_ocr=True;adapter.folder=Path('.')
        adapter.dismiss_related=Mock()
        adapter.query=Mock(return_value={'keyword_text':'简历正文','resume_text':'简历正文','read_complete':True})
        rules = dict(current_rules=20261115,list_prefilter=True,policy='hr_job')
        with patch('ledger.run_row',return_value={'rule_snapshot':json.dumps(rules)}), \
             patch('candidate_checks.require_resume',side_effect=ValueError('coworker_pending')) as check, \
             patch('capture_resume.capture') as capture:
            with self.assertRaisesRegex(ValueError,'coworker_pending'):
                adapter.read({'candidate_id':'synthetic'},'resume')
        check.assert_called_once()
        capture.assert_not_called()


if __name__=='__main__':unittest.main()
