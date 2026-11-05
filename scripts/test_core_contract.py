"""Public regressions use synthetic configuration and isolated local state only."""
import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import group_policy,hit_summary,report_store,run_admission,vault_crypto

class StartupMenuTests(unittest.TestCase):
    def projects(self):
        return [dict(company='SampleCompany',position='SampleRole',profile='sample.md',approval='approved')]
    def test_generic_and_menu_one_show_home(self):
        from quick_start import parse
        for prompt in ('开始打招呼','帮我打招呼','菜单1','菜单 1'):
            self.assertEqual(parse(prompt,self.projects())['state'],'menu')
    def test_menu_two_and_count_only_select_company(self):
        from quick_start import parse
        for prompt in ('菜单2','菜单 2','帮我打50个'):
            result=parse(prompt,self.projects())
            self.assertEqual((result['state'],result['selection_level']),('needs_selection','company'))
        self.assertEqual(parse('帮我打50个',self.projects())['target'],50)
    def test_unique_company_prefix_starts_with_requested_count(self):
        from quick_start import parse
        result=parse('帮我打Sample50个',self.projects())
        self.assertEqual((result['state'],result['target']),('ready_to_start',50))
        self.assertIn('start_direct_run',result['next_actions'])
        self.assertNotIn('wait_for_manual_filters_and_reply_1',result['next_actions'])

class GroupTests(unittest.TestCase):
    def rules(self):
        return dict(version=7,fulltext_groups=dict(a=['alpha','beta','gamma'],b=['one','two','three','4 年'],scoring='incremental',single_score=11,both_base=23,extra_points=3,cap=31,ascii_boundary=True))
    def test_distinct_group_count_and_cap(self):
        rules=self.rules()
        for text,score,allowed in [('',0,False),('alpha beta gamma',11,False),('one two three',11,False),('alpha one',23,True),('alpha alpha one one',23,True),('alpha beta one',26,True),('alpha beta gamma one two three',31,True)]:
            with self.subTest(text=text):
                result=group_policy.evaluate(rules,dict(keyword_text=text))
                self.assertEqual((result['score'],result['eligible']),(score,allowed))
    def test_full_text_and_word_boundaries(self):
        rules=self.rules()
        self.assertTrue(group_policy.evaluate(rules,dict(keyword_text='ALPHA\n引用：one'))['eligible'])
        self.assertFalse(group_policy.evaluate(rules,dict(keyword_text='alphabet one'))['eligible'])
        self.assertTrue(group_policy.evaluate(rules,dict(keyword_text='alpha 4年'))['eligible'])
        self.assertFalse(group_policy.evaluate(rules,dict(keyword_text='alpha 14年'))['eligible'])

class KeywordIncrementalTests(unittest.TestCase):
    def rules(self):
        return dict(version=7,policy='resume_special',fulltext_groups=dict(a=['alpha','beta','gamma'],b=['one','two'],scoring='keyword_incremental',single_score=60,both_base=70,extra_points=2,ascii_boundary=True),resume_special_experience_penalties=[dict(below_years=2,deduct=10)],resume_special_preference_penalty=True,preference_salary_threshold=50000,preference_deduction=10)
    def test_single_both_and_repeated_terms(self):
        import recruiting_rules
        for text,score,allowed in [('',0,False),('alpha',60,True),('one',60,True),('alpha beta',62,True),('alpha one',70,True),('alpha beta one',72,True),('alpha beta one two',74,True),('ALPHA alpha one ONE',70,True)]:
            with self.subTest(text=text):
                result=recruiting_rules.evaluate(self.rules(),dict(keyword_text=text,overall_score=100,hard_requirements=True),99)
                self.assertEqual((result['score'],result['eligible']),(score,allowed))
    def test_penalties_and_recalculation(self):
        import recruiting_rules,fast_assessment
        rules=self.rules();payload=dict(keyword_text='alpha one',related_experience_years=1,expected_salary=60000)
        result=recruiting_rules.evaluate(rules,payload,99)
        self.assertEqual((result['score'],result['experience_penalty'],result['preference_penalty'],result['eligible']),(50,10,10,True))
        self.assertEqual(recruiting_rules.evaluate(rules,fast_assessment.fill(payload,result),99)['score'],50)
    def test_no_hits_never_fall_back_to_manual_score(self):
        import recruiting_rules
        result=recruiting_rules.evaluate(self.rules(),dict(keyword_text='unrelated',overall_score=100,hard_requirements=True),70)
        self.assertEqual((result['score'],result['eligible']),(0,False))

class SummaryTests(unittest.TestCase):
    def test_legacy_and_malformed(self):
        self.assertEqual(hit_summary.visible([], ' 直接规则命中: [{"company":"SampleVendor","quote":"context"}]'),'命中词：SampleVendor')
        self.assertEqual(hit_summary.display('直接规则命中：[bad]'),'规则命中，历史证据待解析')
        self.assertEqual(hit_summary.display('实际普通评语'),'实际普通评语')
    def test_nested_unique(self):
        self.assertEqual(hit_summary.words(dict(hits=[dict(word='x'),dict(word='x'),dict(evidence=[dict(company='y')])])),['x','y'])

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.file=Path(self.temp.name)/'ledger.sqlite3'
        self.db=sqlite3.connect(self.file,isolation_level=None);self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE runs(run_id TEXT PRIMARY KEY,started_at TEXT,deadline_at TEXT,target INTEGER,profile_path TEXT,profile_hash TEXT,min_score INTEGER)')
        self.db.execute('CREATE TABLE run_control(run_id TEXT,state TEXT)')
    def legacy(self):
        self.db.execute("INSERT INTO runs(run_id,started_at,deadline_at,target,profile_path,profile_hash) VALUES ('old','','',1,'old','old')")
    def test_old_admission_blocked_during_and_after_install(self):
        with run_admission.maintenance(self.file,Path(self.temp.name)/'journal.json'):
            with self.assertRaisesRegex(sqlite3.IntegrityError,'installation_in_progress'):self.legacy()
        with self.assertRaisesRegex(sqlite3.IntegrityError,'reload_updated'):self.legacy()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM runs').fetchone()[0],0)
    def test_rollback_first_install_can_be_retried(self):
        with self.assertRaises(RuntimeError):
            with run_admission.maintenance(self.file,Path(self.temp.name)/'journal.json') as ticket:
                ticket['restored']=True
                raise RuntimeError('fixture failure')
        with run_admission.maintenance(self.file,Path(self.temp.name)/'journal2.json'):pass
        self.assertEqual(self.db.execute('SELECT maintenance FROM installation_admission').fetchone()[0],0)
    def test_install_activates_target_version_instead_of_loaded_old_module(self):
        with run_admission.maintenance(self.file,Path(self.temp.name)/'journal.json',build_id='9.9.9'):
            pass
        self.assertEqual(self.db.execute('SELECT build_id FROM installation_admission').fetchone()[0],'9.9.9')

class DestinationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=sqlite3.connect(self.root/'ledger.sqlite3',isolation_level=None);self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
    def profile(self,name,company,position):
        folder=self.root/name;folder.mkdir()
        path=folder/'profile.md'
        path.write_text('---\nschema: boss-greeting-profile/v1\ncompany: '+company+'\nposition: '+position+'\n---\n',encoding='utf-8')
        (folder/'project.json').write_text(json.dumps(dict(project_id=name)),encoding='utf-8')
        return path
    def test_root_conflict_and_delimiter_collision(self):
        a=self.profile('first','A-B','C');b=self.profile('second','A','B-C')
        first=report_store.destination(self.db,self.root/'one','2026-11-03T12:00:00+08:00',a)
        again=report_store.destination(self.db,self.root/'two','2026-11-03T12:00:00+08:00',a)
        other=report_store.destination(self.db,self.root/'one','2026-11-03T12:00:00+08:00',b)
        self.assertEqual(first,again);self.assertNotEqual(report_store.normalized(first),report_store.normalized(other))
    def test_registered_read_lock_is_pending(self):
        from openpyxl import Workbook
        p=self.profile('first','SampleCompany','SampleRole');stamp='2026-11-03T12:00:00+08:00'
        target=report_store.destination(self.db,self.root,stamp,p);target.parent.mkdir(parents=True)
        wb=Workbook();report_store.add_owner(wb,self.db,stamp,p);wb.save(target)
        with patch('openpyxl.load_workbook',side_effect=PermissionError('fixture read lock')):
            with self.assertRaises(PermissionError):
                with report_store.export(self.db,self.root,stamp,p):pass
        self.assertTrue(report_store.pending(self.db,stamp,p))

class CryptoTests(unittest.TestCase):
    def test_authenticated_wrapping_and_signature(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        from cryptography.exceptions import InvalidSignature
        import os
        key=os.urandom(32);plain=os.urandom(32);wrapped=vault_crypto.wrap(key,plain,b'fixture')
        self.assertEqual(vault_crypto.unwrap(key,wrapped,b'fixture'),plain)
        private=Ed25519PrivateKey.generate();secret=private.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())
        public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        signature=vault_crypto.sign(dict(value='fixture'),secret)
        vault_crypto.verify(dict(value='fixture'),signature,public)
        with self.assertRaises(InvalidSignature):vault_crypto.verify(dict(value='changed'),signature,public)

if __name__=='__main__':unittest.main()
