import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import hr_job
import ledger
import misjudgment_review as review
from test_hr_job import document
from workflow_runner import Runner

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'普工.md'
        self.path.write_text(document(resume_words='组装', resume_negative='主管、经理'), encoding='utf-8')
        self.rules = hr_job.snapshot(self.path)
        self.facts = dict(keyword_text='做过组装，工作时主管过喷漆。', read_complete=True)

    def answer(self, req):
        return dict(request_id=req['request_id'], reviews=[dict(word='主管', verdict='unnecessary',
            quote='工作时主管过喷漆。', reason='全文无管理岗位经历，此处描述负责工序。')])

    def test_trigger(self):
        self.assertIsNotNone(review.request(self.rules, self.facts, 60))
        for facts in [dict(self.facts, read_complete=False), dict(self.facts, keyword_text='组装'),
                      dict(self.facts, keyword_text='主管'), dict(self.facts, evaluation_stage='list')]:
            self.assertIsNone(review.request(self.rules, facts, 60))
        self.rules['hr_job_config']['resume']['misjudgment_review'] = False
        self.assertIsNone(review.request(self.rules, self.facts, 60))

    def test_validation(self):
        req = review.request(self.rules, self.facts, 60)
        answer = self.answer(req)
        self.assertEqual(review.validate(answer, req)[0]['word'], '主管')
        changed = review.request(self.rules, dict(self.facts, keyword_text=self.facts['keyword_text']+'真实经历。'), 60)
        with self.assertRaises(ValueError): review.validate(answer, changed)
        answer['reviews'][0]['quote'] = '虚构经历'
        with self.assertRaises(ValueError): review.validate(answer, req)
        self.assertIsNone(review.request(self.rules, dict(self.facts, resume_evidence=dict(ocr_text='missing')), 60))

    def test_annotation_and_hash(self):
        self.path.write_text(document(list_negative='主管', resume_words='组装', resume_negative='主管、经理、生产主管'), encoding='utf-8')
        before = self.path.read_text(encoding='utf-8')
        digest = ledger.profile_hash(self.path)
        config = hr_job.parse(before)
        self.assertTrue(review.annotate(self.path, ['主管'], digest))
        text = self.path.read_text(encoding='utf-8')
        self.assertEqual(text.count(review.MARKER), before.count(review.MARKER)+1)
        self.assertIn('主管'+review.MARKER+'、经理、生产主管', text)
        self.assertEqual(hr_job.parse(text), config)
        self.assertEqual(ledger.profile_hash(self.path), digest)
        self.assertFalse(review.annotate(self.path, ['主管'], digest))
        self.assertTrue(list(self.path.parent.glob('.*.bak')))
        self.path.write_text(text.replace('组装', '包装'), encoding='utf-8')
        with self.assertRaises(ValueError): review.annotate(self.path, ['经理'], digest)

    def test_worker_threshold(self):
        rules = dict(mode='worker_resume', worker_policy_version=2, worker_keywords=['组装'],
            worker_deduction_version=1, worker_negative_keywords=['主管'], worker_negative_points=10, worker_min_score=60)
        self.assertIsNotNone(review.request(rules, self.facts, 60))
        rules['worker_min_score'] = 40
        self.assertIsNone(review.request(rules, self.facts, 40))

    def test_runner_handoff(self):
        runner = Runner.__new__(Runner)
        runner.db = sqlite3.connect(':memory:')
        self.addCleanup(runner.db.close)
        runner.db.execute('CREATE TABLE run_audit(run_id,at,event,detail)')
        runner.run, runner.phase, runner.folder = 'run', 'assess', self.path.parent
        runner.data = dict(candidate=dict(candidate_id='candidate', candidate_name='测试人'), visit_hash='visit', facts=self.facts)
        runner.status = lambda state=None: dict(state=state)
        runner.record_payload = lambda payload: runner.data.update(decision=payload['decision'])
        rules = dict(self.rules, ai_pros_cons=False)
        run = dict(evaluation_mode='resume', rule_snapshot=json.dumps(rules), min_score=60, profile_path=str(self.path), profile_hash=ledger.profile_hash(self.path))
        with patch('ledger.control_state', return_value='running'), patch('ledger.run_row', return_value=run):
            self.assertEqual(runner.step()['state'], 'needs_misjudgment_review')
            req = json.loads(Path(runner.data['request_file']).read_text(encoding='utf-8'))['evidence']
            Path(runner.data['response_file']).write_text(json.dumps(self.answer(req)), encoding='utf-8')
            runner.step()
        self.assertIn('主管'+review.MARKER, self.path.read_text(encoding='utf-8'))
        self.assertEqual(runner.data['decision'], 'skip')
        self.assertEqual(runner.phase, 'favorite')
        self.assertEqual(runner.db.execute('SELECT count(*) FROM run_audit').fetchone()[0], 1)

if __name__ == '__main__': unittest.main()
