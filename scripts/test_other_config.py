"""New HR settings, confirmed-greeting rest and explicit coworker opt-out."""
import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import candidate_checks
import candidate_log
import coworker_progress
import greeting_view_wait
import hr_job
import ledger
from test_hr_job import document
from workflow_runner import Runner


class ConfigurationTests(unittest.TestCase):
    def test_exact_new_labels_and_snapshot(self):
        config = hr_job.parse(document())
        self.assertEqual((config['minimum_seconds'], config['rest_seconds'], config['rest_after_greetings'],
                          config['coworker_days'], config['greeting_mode']), (30, 30, 5, 7, 'single'))
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp)/'company'/'job.md';profile.parent.mkdir()
            profile.write_text(document(), encoding='utf-8')
            rules = hr_job.snapshot(profile)
            self.assertEqual(rules['view_wait_policy'], 3)
            self.assertEqual(rules['hr_job_config'], config)

    def test_legacy_labels_compile_to_current_five_greeting_policy(self):
        text = document().replace('单简历查看时间不低于', '单简历查看时间（为期望平均值）')
        text = text.replace('连续招呼五次后额外休息：30 秒', '查看十人后休息：2 分钟')
        text = text.replace('同事几天以上可打招呼（填 0 为不判断同事）', '同事几天以上可打招呼')
        config = hr_job.parse(text)
        self.assertEqual(config['rest_seconds'], 120)
        self.assertEqual(config['rest_after_greetings'], 5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'job.md';path.write_text(text, encoding='utf-8')
            self.assertEqual(hr_job.snapshot(path)['view_wait_policy'], 3)
        self.assertEqual(hr_job.parse(text.replace('（为期望平均值）', '（不足时补足）')), config)

    def test_duplicate_alias_and_invalid_values_fail(self):
        for text in (document()+'\n查看十人后休息：1 秒',
                     document().replace('7 天', '-1 天'), document().replace('30 秒', '三十秒', 1)):
            with self.subTest(text=text[-120:]), self.assertRaises(hr_job.ConfigError):
                hr_job.parse(text)

    def test_zero_days_explicitly_disables_and_old_snapshot_keeps_policy(self):
        config = hr_job.parse(document().replace('7 天', '0 天'))
        rules = dict(hr_job_config=config, coworker_notice_policy=1)
        recent = dict(state='records', evidence='recent', records=[datetime.now(timezone.utc).isoformat()], records_complete=True)
        for evidence in (None, dict(state='not_checked'), recent):
            result = coworker_progress.evaluate_for_rules(evidence, rules)
            self.assertTrue(result['may_continue'])
            self.assertFalse(result['notice_required'])
            self.assertEqual(result['state'], 'disabled')
        legacy = dict(hr_job_config=dict(coworker_days=0), coworker_notice_policy=1)
        self.assertFalse(coworker_progress.disabled(legacy))
        self.assertTrue(coworker_progress.evaluate_for_rules(dict(state='unavailable', evidence='unknown'), legacy)['notice_required'])


class GreetingTimingTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE candidates(run_id,candidate_hash,status)')
        self.config = dict(minimum_seconds=30, rest_seconds=30, rest_after_greetings=5)

    def sent(self, visit, state='sent'):
        self.db.execute('INSERT INTO candidates VALUES (?,?,?)', ('r', visit, state))

    def test_each_resume_has_own_minimum_without_average_carry(self):
        self.assertEqual(greeting_view_wait.plan(self.db, 'r', 'long', 60, self.config, 60)['seconds'], 0)
        self.assertEqual(greeting_view_wait.plan(self.db, 'r', 'short', 12, self.config, 72)['seconds'], 18)
        self.assertEqual(greeting_view_wait.plan(self.db, 'r', 'short', 99, self.config, 80)['retry_after_seconds'], 10)
        self.assertEqual(greeting_view_wait.plan(self.db, 'r', 'short', 99, self.config, 90)['retry_after_seconds'], 0)

    def test_five_confirmed_greetings_not_views_or_unknowns(self):
        for i in range(1, 5):
            self.sent(str(i))
            self.assertEqual(greeting_view_wait.plan(self.db, 'r', str(i), 40, self.config, i*40)['rest_seconds'], 0)
        for i in range(5, 16):
            self.sent(str(i), 'unknown' if i == 5 else 'skipped')
            self.assertEqual(greeting_view_wait.plan(self.db, 'r', str(i), 40, self.config, i*40)['rest_seconds'], 0)
        self.sent('fifth')
        result = greeting_view_wait.plan(self.db, 'r', 'fifth', 12, self.config, 700)
        self.assertEqual((result['view_wait_seconds'], result['rest_seconds'], result['retry_after_seconds']), (18, 30, 48))
        result = greeting_view_wait.plan(self.db, 'r', 'fifth', 60, self.config, 718)
        self.assertEqual((result['view_remaining_seconds'], result['rest_remaining_seconds']), (0, 30))
        self.assertEqual(greeting_view_wait.plan(self.db, 'r', 'fifth', 90, self.config, 748)['retry_after_seconds'], 0)
        self.sent('sixth')
        self.assertEqual(greeting_view_wait.plan(self.db, 'r', 'sixth', 40, self.config, 800)['rest_seconds'], 0)

    def test_rest_survives_database_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'wait.sqlite'
            with contextlib.closing(sqlite3.connect(path)) as target:
                self.db.backup(target)
            db = sqlite3.connect(path, isolation_level=None);db.row_factory = sqlite3.Row
            for i in range(5):db.execute('INSERT INTO candidates VALUES (?,?,?)', ('r', str(i), 'sent'))
            greeting_view_wait.plan(db, 'r', '4', 40, self.config, 100)
            db.close()
            with contextlib.closing(sqlite3.connect(path, isolation_level=None)) as db:
                db.row_factory = sqlite3.Row
                self.assertEqual(greeting_view_wait.plan(db, 'r', '4', 90, self.config, 110)['retry_after_seconds'], 20)
                self.assertEqual(db.execute('SELECT count(*) FROM greeting_rest_awards').fetchone()[0], 1)

    def test_award_and_wait_are_atomic_on_failure(self):
        greeting_view_wait.plan(self.db, 'r', 'setup', 40, self.config, 0)
        for i in range(5):self.sent(str(i))
        self.db.execute("CREATE TRIGGER fail_wait BEFORE INSERT ON greeting_view_waits BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            greeting_view_wait.plan(self.db, 'r', '4', 40, self.config, 100)
        self.assertEqual(self.db.execute('SELECT count(*) FROM greeting_rest_awards').fetchone()[0], 0)

    def test_last_candidate_finishes_minimum_and_extra_rest(self):
        for i in range(5):self.sent(str(i))
        rules = dict(view_wait_policy=3, hr_job_config=self.config)
        run = dict(evaluation_mode='resume', rule_snapshot=json.dumps(rules))
        runner = Runner.__new__(Runner)
        runner.db, runner.run, runner.phase, runner.adapter = self.db, 'r', 'next', Mock()
        runner.data = dict(visit_hash='4', resume_started_active=90, candidate={'candidate_id':'4'}, visits=4, sent=True)
        runner.status = lambda state=None: dict(state=state)
        for active, state in ((100, 'short_view_wait'), (120, 'short_view_wait'), (150, 'complete')):
            with patch('ledger.control_state', return_value='running'), patch('ledger.run_row', return_value=run), \
                 patch('run_safety.quantity_reason', return_value='target_reached'), patch('report_batch.flush_now'), \
                 patch('short_view_wait.enabled', return_value=True), patch('short_view_wait.active_clock', return_value=active):
                self.assertEqual(runner.step()['state'], state)
        runner.adapter.close.assert_not_called()
        runner.adapter.next.assert_not_called()


class CoworkerOptOutTests(unittest.TestCase):
    def test_zero_days_never_queries_ui_or_requests_notice(self):
        runner = Runner.__new__(Runner)
        runner.db, runner.run, runner.phase, runner.adapter = Mock(), 'r', 'coworker', Mock()
        runner.data = dict(candidate={'candidate_id':'synthetic'})
        rules = dict(hr_job_config=hr_job.parse(document().replace('7 天', '0 天')), coworker_notice_policy=1)
        run = dict(evaluation_mode='resume', rule_snapshot=json.dumps(rules))
        result = coworker_progress.evaluate_for_rules(None, rules)
        with patch('ledger.control_state', return_value='running'), patch('ledger.run_row', return_value=run), \
             patch('candidate_checks.record', return_value=result):
            runner.step()
        runner.adapter.colleague.assert_not_called()
        self.assertEqual(runner.phase, 'read')
        self.assertNotIn('request_file', runner.data)

    def test_record_and_reserve_accept_explicit_disabled_check(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            root = Path(tmp);path = root/'company'/'job.md';path.parent.mkdir()
            path.write_text(document(resume_words='组装').replace('7 天', '0 天'), encoding='utf-8')
            with patch.object(ledger, 'PROFILE_ROOT', root):
                db = ledger.connect(root/'ledger.sqlite');stack.callback(db.close)
                with contextlib.redirect_stdout(io.StringIO()):
                    ledger.start(db, argparse.Namespace(profile=path, target=2, max_views=4, min_score=60))
            run = db.execute('SELECT run_id FROM runs').fetchone()[0]
            candidate_log.table(db)
            ledger.ensure_candidate(db, run, 'synthetic')
            payload = dict(candidate_id='synthetic', candidate_name='虚构测试', keyword_text='组装', read_complete=True,
                           decision='greet', overall_score=60, electronic_resume_enabled=True, electronic={'score':60,'evidence':'组装'},
                           hard_requirements=False, pros='组装', cons='待核实',
                           coworker_progress={'state':'disabled','evidence':'同事配置为0天，未判断同事沟通'})
            with contextlib.redirect_stdout(io.StringIO()), patch('csv_report.setup_viewer', side_effect=lambda template,target,specs,configure=None: shutil.copy2(template,target)):
                candidate_log.record(db, argparse.Namespace(run=run, output_root=root), payload)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):ledger.reserve(db, argparse.Namespace(run=run, candidate_id='synthetic'))
            self.assertEqual(json.loads(out.getvalue())['state'], 'ready')


if __name__ == '__main__':
    unittest.main()
