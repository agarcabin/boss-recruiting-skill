"""Isolated regressions for provenance, worker scoring, cooldown and shared quota."""
import contextlib, json, sqlite3, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import project_source, project_vault, recruiting_rules, short_view_wait, greeting_rate


class Worker149Tests(unittest.TestCase):
    def rules(self, count=24):
        return dict(mode='worker_resume', policy='worker', worker_policy_version=2,
                    worker_deduction_version=1, worker_negative_keywords=['服务员','厨师','前台','传菜','销售','经理','主管'],
                    worker_negative_points=10, worker_min_score=60,
                    worker_keywords=['词'+chr(0x4e00+i) for i in range(count)])

    def score(self, rules, text):
        return recruiting_rules.evaluate(rules, dict(keyword_text=text, read_complete=True, worker_stage='resume'), 99)

    def test_dedup_overlap_cap_and_floor(self):
        rules=self.rules()
        text='；'.join(rules['worker_keywords'])+'；做过销售经理；做过销售经理'
        result=self.score(rules,text)
        self.assertEqual((result['score_before_penalties'],result['score'],result['keyword_penalty']),(100,80,20))
        self.assertEqual(len(result['negative_hits']),2)
        result=self.score(rules,'词一；服务员；厨师；前台；传菜；销售；经理；主管')
        self.assertEqual(result['score'],0)
        self.assertFalse(result['eligible'])

    def test_thresholds_and_no_positive_fallback(self):
        for count,negative,score,eligible in [(1,'',60,True),(1,'销售',50,False),(6,'销售',60,True),(21,'销售',90,True),(20,'销售',88,True)]:
            rules=self.rules(count)
            result=self.score(rules,'；'.join(rules['worker_keywords'])+'；'+negative)
            self.assertEqual((result['score'],result['eligible']),(score,eligible))
        self.assertFalse(self.score(self.rules(),'销售经理')['eligible'])
        # Scores from the current +2/-10 formula are even; explicit minimum tests cover boundary comparison.
        rules=self.rules(1);rules['worker_min_score']=61
        self.assertFalse(self.score(rules,'词一')['eligible'])
        rules['worker_min_score']=59
        self.assertTrue(self.score(rules,'词一')['eligible'])

    def test_exclusions_list_and_legacy_snapshot(self):
        rules=self.rules()
        self.assertEqual(self.score(rules,'词一；没有做过销售；招聘信息要求经理')['score'],60)
        result=recruiting_rules.worker_match(rules,dict(worker_stage='list',raw_text='词一；销售经理'))
        self.assertEqual((result['score'],result['keyword_penalty'],result['eligible']),(60,0,True))
        old=dict(rules);old.pop('worker_deduction_version')
        self.assertEqual(self.score(old,'词一；销售经理')['score'],60)
        self.assertFalse(recruiting_rules.evaluate(rules,dict(worker_stage='resume',read_complete=False,keyword_text='词一'),60)['eligible'])


class Quota149Tests(unittest.TestCase):
    def test_window_persistence_and_upgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'quota.sqlite3'
            at=datetime(2026,11,9,tzinfo=timezone.utc)
            with contextlib.closing(sqlite3.connect(file)) as db:
                db.row_factory=sqlite3.Row
                db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
                for i in range(10):self.assertEqual(greeting_rate.claim(db,str(i),at)['state'],'ready')
                self.assertTrue(greeting_rate.claim(db,'0',at)['reused'])
                db.commit()
            with contextlib.closing(sqlite3.connect(file)) as db:
                db.row_factory=sqlite3.Row
                self.assertEqual(greeting_rate.status(db,at+timedelta(seconds=499))['retry_after_seconds'],1)
                self.assertEqual(greeting_rate.claim(db,'other-job',at+timedelta(seconds=499))['state'],'rate_limited')
                self.assertEqual(greeting_rate.claim(db,'other-job',at+timedelta(seconds=500))['used'],1)
                db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(dict(started_at=at.isoformat(),used=10)),greeting_rate.KEY))
                self.assertEqual(greeting_rate.status(db,at+timedelta(seconds=450))['retry_after_seconds'],50)

    def test_only_recent_coworker_skip_is_exempt(self):
        result=dict(skip=True,reason='coworker_within_or_exactly_7_days')
        self.assertTrue(short_view_wait.coworker_exempt(dict(coworker_skip_wait_exempt=True),result,'skip'))
        self.assertFalse(short_view_wait.coworker_exempt({},result,'skip'))
        self.assertFalse(short_view_wait.coworker_exempt(dict(coworker_skip_wait_exempt=True),result,'review'))
        self.assertFalse(short_view_wait.coworker_exempt(dict(coworker_skip_wait_exempt=True),dict(skip=False,reason='all_coworker_contacts_older_than_7_days'),'skip'))


class Source149Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.name='profiles/Company/job/profile.md'
        self.meta_name='profiles/Company/job/project.json'
        self.profile=self.root/self.name;self.profile.parent.mkdir(parents=True)
        self.meta=dict(origin='bundle',project_id='job',profile='profile.md',company='Company',position='Role',updated_at='old')
        self.files={self.name:b'original',self.meta_name:json.dumps(self.meta).encode()}
        self.profile.write_bytes(b'original')
        (self.root/self.meta_name).write_bytes(self.files[self.meta_name])

    def test_three_labels_and_timestamp_ignored(self):
        meta=dict(self.meta,updated_at='new')
        source=project_source.classify(self.profile,meta,self.files,self.root)
        self.assertEqual(project_source.display('Role',source),'Role ☁️')
        self.profile.write_bytes(b'changed')
        self.assertEqual(project_source.classify(self.profile,meta,self.files,self.root)['kind'],'local')
        own=dict(origin='user',project_id='own')
        self.assertEqual(project_source.classify(self.profile,own,self.files,self.root)['kind'],'self')
        self.assertEqual(project_source.copy_provenance(self.meta)['provenance']['kind'],'local')

    def test_preserve_changed_bundle_and_migrate_source(self):
        self.profile.write_bytes(b'local edit')
        incoming={self.name:b'new cloud',self.meta_name:self.files[self.meta_name]}
        with patch.object(project_source,'baseline',return_value=self.files):
            result=project_vault.preserve_user_projects(incoming,self.root)
        self.assertNotIn(self.name,result)
        migration=json.loads(result[self.meta_name])
        self.assertEqual((migration['origin'],migration['provenance']['kind']),('user','local'))
        (self.root/self.meta_name).write_bytes(result[self.meta_name])
        with patch.object(project_source,'baseline',return_value=incoming):
            self.assertEqual(project_vault.preserve_user_projects(incoming,self.root),{})

    def test_unchanged_cloud_updates_and_identity_collision_rejected(self):
        with patch.object(project_source,'baseline',return_value=self.files):
            self.assertEqual(project_vault.preserve_user_projects(self.files,self.root),self.files)
        self.profile.write_bytes(b'local edit')
        incoming=dict(self.files);incoming[self.meta_name]=json.dumps(dict(self.meta,project_id='other')).encode()
        with patch.object(project_source,'baseline',return_value=self.files):
            with self.assertRaises(ValueError):project_vault.preserve_user_projects(incoming,self.root)


if __name__=='__main__':unittest.main()
