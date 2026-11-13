import argparse
import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import candidate_log
import coworker_progress
import fast_assessment
import hr_job
import hr_view_wait
import ledger
import project_registry
import recruiting_rules
from workflow_runner import Runner


TEMPLATE = (Path(__file__).resolve().parents[1]/'docs/HR-JOB-TEMPLATE.md').read_text(encoding='utf-8')


def document(list_words='', list_negative='', resume_words='', resume_negative=''):
    chunks = TEMPLATE.replace('{{岗位名称}}', '仓库保管员').split('### ')
    for i, value in enumerate((list_words, list_negative, resume_words, resume_negative), 1):
        body, sep, tail = chunks[i].partition('\n## ')
        chunks[i] = body+'\n'+value+'\n'+(sep+tail if sep else '')
    return '### '.join(chunks)


class HRTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = patch.dict(os.environ, {'BOSS_STATE_DIR': str(self.root/'state')})
        env.start()
        self.addCleanup(env.stop)
        self.path = self.root/'01 测试企业'/'仓库保管员.md'
        self.path.parent.mkdir()
        self.path.write_text(document(), encoding='utf-8')

    def rules(self, **kwargs):
        self.path.write_text(document(**kwargs), encoding='utf-8')
        return recruiting_rules.snapshot(self.path, project_registry.front_matter(self.path))

    def test_identity_without_json(self):
        self.assertEqual(project_registry.read_project(self.path)['company'], '测试企业')
        self.assertTrue(ledger.profile_check(self.path)[0])

    def test_recompile_ignores_old_rules_and_keeps_identity(self):
        sidecar = self.path.with_name('.'+self.path.stem+'.project.json')
        sidecar.write_text(json.dumps(dict(company='测试企业', project_id='test-job', candidate_namespace='keep-id',
            rules=dict(fulltext_groups=dict(a=['旧词'], b=['旧词'])), greeting_mode='triple')), encoding='utf-8')
        before = sidecar.read_bytes()
        old = self.rules(resume_words='仓管')
        new = self.rules(resume_words='库存')
        payload = dict(keyword_text='有仓管经验', read_complete=True)
        self.assertTrue(recruiting_rules.evaluate(old, payload, 100)['eligible'])
        self.assertFalse(recruiting_rules.evaluate(new, payload, 0)['eligible'])
        self.assertEqual(new['namespace'], 'keep-id')
        self.assertEqual(new['greeting_mode'], 'single')
        self.assertEqual(sidecar.read_bytes(), before)

    def test_independent_stages_and_veto(self):
        rules = self.rules(list_words='仓管、库管', list_negative='销售', resume_words='Excel', resume_negative='前台')
        for text, eligible in [('库管', True), ('Excel', False), ('仓管 销售', False)]:
            self.assertEqual(recruiting_rules.list_match(rules, dict(raw_text=text))['eligible'], eligible)
        for text, eligible in [('熟练Excel', True), ('Excel 前台', False)]:
            self.assertEqual(recruiting_rules.evaluate(rules, dict(keyword_text=text, read_complete=True), 100)['eligible'], eligible)
        self.assertFalse(recruiting_rules.evaluate(rules, dict(keyword_text='Excel', read_complete=False), 0)['eligible'])

    def test_empty_positive_still_checks_veto(self):
        rules = self.rules(list_negative='销售', resume_negative='前台')
        self.assertFalse(recruiting_rules.list_match(rules, dict(raw_text='销售'))['eligible'])
        self.assertTrue(recruiting_rules.list_match(rules, dict(raw_text='仓管'))['eligible'])
        self.assertFalse(recruiting_rules.evaluate(rules, dict(keyword_text='前台', read_complete=True), 0)['eligible'])
        self.assertTrue(recruiting_rules.evaluate(rules, dict(keyword_text='仓管', read_complete=True), 100)['eligible'])
        self.assertTrue(recruiting_rules.list_match(self.rules(), {})['eligible'])

    def test_expression_confirmed_by_user(self):
        rules = self.rules(resume_words='A1：仓管\nB1：Excel\nB2：WMS\n匹配方式：A1+B1/B2')
        for text, expected in [('仓管 Excel', True), ('仓管 WMS', True), ('仓管', False), ('WMS', False), ('不会Excel，做过仓管', False)]:
            with self.subTest(text=text):
                self.assertEqual(recruiting_rules.evaluate(rules, dict(keyword_text=text, read_complete=True), 0)['eligible'], expected)

    def test_and_default_and_or_explicit(self):
        for formula, expected in [('', False), ('\n匹配方式：A/B', True)]:
            rules = self.rules(resume_words='A：仓管\nB：Excel'+formula)
            self.assertEqual(recruiting_rules.evaluate(rules, dict(keyword_text='仓管', read_complete=True), 0)['eligible'], expected)

    def test_invalid_configuration_fails_before_start(self):
        for text in [document(list_words='xx'), document(resume_words='A：仓管\n匹配方式：A+C'),
                     document().replace('30 秒', '-1 秒'), document().replace('7 天', '七天'),
                     document().replace('2. 减分词库', '2. 错误标题', 1)]:
            with self.subTest(text=text[:20]), self.assertRaises(hr_job.ConfigError):
                hr_job.parse(text)

    def test_ocr_failure_is_not_complete(self):
        rules = self.rules(resume_words='仓管')
        result = recruiting_rules.evaluate(rules, dict(keyword_text='仓管', read_complete=True,
            resume_evidence=dict(ocr_text=str(self.root/'missing.txt'))), 0)
        self.assertFalse(result['eligible'])

    def test_coworker_custom_threshold(self):
        rules = self.rules()
        rules['hr_job_config']['coworker_days'] = 3
        at = datetime(2026, 11, 12, tzinfo=timezone.utc)
        def check(days):
            return coworker_progress.evaluate_for_rules(dict(state='records', evidence='已读取记录', records_complete=True,
                records=[(at-timedelta(days=days)).isoformat()]), rules, at)
        self.assertTrue(check(3)['skip'])
        self.assertTrue(check(3.01)['may_continue'])
        self.assertFalse(coworker_progress.evaluate_for_rules({}, rules, at)['may_continue'])

    def test_record_and_reserve_share_eligibility(self):
        rules = self.rules(resume_words='仓管')
        payload = dict(candidate_id='candidate-001', candidate_name='测试候选人', started_at='2026-11-12T10:00:00+08:00',
            keyword_text='有仓管经验', read_complete=True, coworker_progress=dict(state='empty', evidence='未见同事沟通记录'))
        result = recruiting_rules.evaluate(rules, payload, 70)
        filled = fast_assessment.fill(payload, result)
        filled.update(trigger_policy='hr_job', direct_trigger=True)
        candidate_log.validate(filled, rules)
        self.assertTrue(ledger.assessment_eligible(dict(rule_snapshot=json.dumps(rules), min_score=70), dict(evaluation_input=json.dumps(payload))))

    def test_actual_start_persists_frozen_json(self):
        rules = self.rules(resume_words='仓管')
        with patch.object(ledger, 'PROFILE_ROOT', self.root):
            db = ledger.connect(self.root/'test.sqlite')
            self.addCleanup(db.close)
            result = io.StringIO()
            with contextlib.redirect_stdout(result):
                ledger.start(db, argparse.Namespace(profile=self.path, target=1, max_views=2, min_score=70))
            self.assertEqual(json.loads(result.getvalue())['state'], 'started')
            self.assertEqual(json.loads(db.execute('SELECT rule_snapshot FROM runs').fetchone()[0])['hr_job_config'], rules['hr_job_config'])


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.config = dict(average_seconds=50, rest_seconds=120)

    def test_average_and_separate_rest_and_retries(self):
        active = 0
        for i in range(1, 11):
            elapsed = 60 if i == 1 else 40 if i == 2 else 50
            active += elapsed
            r = hr_view_wait.plan(self.db, 'run', str(i), elapsed, self.config, active)
            self.assertEqual(r['seconds'], 120 if i == 10 else 0)
            self.assertEqual(hr_view_wait.plan(self.db, 'run', str(i), elapsed, self.config, active)['seconds'], r['seconds'])
            active += r['seconds']
            self.assertEqual(hr_view_wait.plan(self.db, 'run', str(i), elapsed, self.config, active)['retry_after_seconds'], 0)
        self.assertEqual(hr_view_wait.plan(self.db, 'run', '11', 0, self.config, active)['seconds'], 50)

    def runner(self):
        r = Runner.__new__(Runner)
        r.db, r.run = self.db, 'run'
        r.data = dict(visit_hash='v', candidate=dict(candidate_id='candidate'), processed=[], visits=0)
        r.phase, r.adapter = 'next', Mock()
        r.status = lambda state=None: dict(state=state)
        return r

    def test_unopened_resume_not_counted(self):
        runner = self.runner()
        run = dict(rule_snapshot=json.dumps(dict(hr_job_config=self.config)))
        with patch('short_view_wait.active_clock') as clock:
            self.assertEqual(hr_view_wait.runner_wait(runner, run)['retry_after_seconds'], 0)
            clock.assert_not_called()

    def test_resume_clock_begins_after_open(self):
        runner = self.runner()
        runner.phase = 'list_open'
        run = dict(evaluation_mode='resume', rule_snapshot=json.dumps(dict(hr_job_config=self.config)))
        with patch('ledger.control_state', return_value='running'), patch('ledger.run_row', return_value=run), \
             patch('workflow_runner.call'), patch('short_view_wait.active_clock', return_value=123):
            runner.step()
        self.assertEqual(runner.data['resume_started_active'], 123)

    def test_final_view_wait_before_complete(self):
        runner = self.runner()
        runner.data['resume_started_active'] = 100
        run = dict(evaluation_mode='resume', rule_snapshot=json.dumps(dict(hr_job_config=self.config)))
        for active, expected in [(110, 'short_view_wait'), (150, 'complete')]:
            with patch('ledger.control_state', return_value='running'), patch('ledger.run_row', return_value=run), \
                 patch('run_safety.quantity_reason', return_value='target_reached'), patch('report_batch.flush_now'), \
                 patch('short_view_wait.active_clock', return_value=active):
                self.assertEqual(runner.step()['state'], expected)


if __name__ == '__main__':
    unittest.main()
