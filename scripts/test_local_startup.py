import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hr_job
import ledger
import local_catalog
import project_registry
import quick_start
import workspace_paths


TEMPLATE = (Path(__file__).resolve().parents[1]/'docs/HR-JOB-TEMPLATE.md').read_text(encoding='utf-8')


class LocalStartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        environment = patch.dict(os.environ, {'BOSS_DESKTOP_DIR': str(self.root), 'BOSS_STATE_DIR': str(self.root/'state')})
        environment.start()
        self.addCleanup(environment.stop)
        self.configs = workspace_paths.configs_dir()
        self.configs.mkdir(parents=True)
        self.db = self.root/'not-created.sqlite'

    def job(self, company, position, **meta):
        path = self.configs/company/(position+'.md')
        path.parent.mkdir(exist_ok=True)
        path.write_text(TEMPLATE.replace('{{岗位名称}}',position),encoding='utf-8')
        if meta:
            workspace_paths.metadata_path(path).write_text(json.dumps(meta),encoding='utf-8')
        return path

    def plan(self, prompt):
        return quick_start.prepare(prompt,self.db)

    def test_each_entry_reads_added_renamed_and_removed_files(self):
        self.assertEqual(self.plan('帮我打仓管50个')['state'],'menu')
        path = self.job('01 企业甲','仓管')
        direct = self.plan('帮我打仓管50个')
        self.assertEqual((direct['state'], direct['target']),('ready_to_start',50))
        path.write_text(TEMPLATE.replace('{{岗位名称}}','仓储管理员'),encoding='utf-8')
        self.assertEqual(self.plan('企业甲')['position'],'仓储管理员')
        path.unlink()
        self.assertEqual(self.plan('企业甲')['state'],'menu')

    def test_menu_two_lists_empty_company_folders_and_ignores_root_template(self):
        self.job('01 企业甲','仓管')
        (self.configs/'02 企业乙').mkdir()
        (self.configs/'岗位填写模板.md').write_text(TEMPLATE,encoding='utf-8')
        for prompt in ('2','菜单2','查看所有'):
            plan=self.plan(prompt)
            self.assertEqual(plan['state'],'needs_selection')
            self.assertEqual(plan['project_count'],2)
            self.assertEqual(plan['position_count'],1)
            self.assertEqual([c['position_count'] for c in plan['companies']],[1,0])
        self.assertEqual(len(project_registry.project_listing()['companies']),2)

    def test_home_keeps_six_actions_and_requested_quantity(self):
        self.job('企业甲','仓管')
        for prompt in ('开始打招呼','帮我打不存在企业50个','帮我打50个'):
            plan=self.plan(prompt)
            self.assertEqual(plan['state'],'menu')
            self.assertEqual(len(plan['menu_items']),6)
            self.assertIn('本地企业',plan['menu_items'][1])
            if '50' in prompt:self.assertEqual(plan['target'],50)
        self.assertFalse(self.db.exists())

    def test_unknown_company_and_numeric_folder_prefix_do_not_match(self):
        self.job('50 企业甲','仓管')
        self.assertEqual(self.plan('帮我打50个')['state'],'menu')
        self.assertEqual(self.plan('帮我打企业乙50个')['state'],'menu')

    def test_matching_intersects_company_and_position(self):
        first=self.job('甲企业','仓管')
        self.job('乙企业','仓管')
        self.job('乙企业','会计')
        self.assertEqual(self.plan('仓管')['state'],'needs_selection')
        self.assertEqual(self.plan('甲企业仓管')['profile'],str(first.resolve()))
        self.assertEqual(self.plan('甲企业会计')['state'],'menu')
        self.assertEqual(self.plan('乙企业')['selection_level'],'position')

    def test_company_prefix_and_parenthetical_job_alias(self):
        path=self.job('01 示例甲集团','巡检（普工）')
        self.job('02 示例甲集团分厂','ExampleEntity58')
        self.assertEqual(self.plan('帮我打示例甲巡检50个')['profile'],str(path.resolve()))

    def test_malformed_retired_and_hidden_entries_never_start(self):
        path=self.job('企业甲','仓管')
        path.write_text('# 仓管\n\n未填写模板',encoding='utf-8')
        self.job('企业乙','会计',active=False)
        self.job('_备份','旧岗位')
        plan=self.plan('仓管')
        self.assertEqual(plan['state'],'menu')
        self.assertEqual(plan['position_count'],0)
        self.assertEqual(len(plan['config_errors']),1)

    def test_continue_uses_live_job_and_missing_job_returns_menu(self):
        path=self.job('企业甲','仓管')
        latest=dict(profile_path=str(path.resolve()),run_id='old-run',run_state='stopped',resumable=False)
        with patch('project_registry.latest_run_readonly',return_value=latest):
            self.assertEqual(self.plan('1')['state'],'ready_to_start')
            latest.update(run_state='paused',resumable=True)
            plan=self.plan('1')
            self.assertEqual((plan['state'],plan['run_id']),('ready_to_resume','old-run'))
            path.unlink()
            self.assertEqual(self.plan('1')['state'],'menu')

    def test_menu_one_is_home_and_create_update_test_exit_are_routed(self):
        self.assertEqual(self.plan('菜单1')['state'],'menu')
        for choice, action in [('3','create_local_project'),('4','show_update_menu'),('5','test_environment'),('6','exit_greetings')]:
            self.assertEqual(self.plan(choice)['next_actions'],[action])

    def test_saved_plan_is_rechecked_and_removed_job_does_not_start(self):
        path=self.job('企业甲','仓管')
        plan=self.plan('企业甲50个')
        path.unlink()
        result=quick_start.refresh_selected(plan,self.db)
        self.assertEqual(result['state'],'menu')
        self.assertFalse(self.db.exists())

    def test_start_compiles_current_markdown_and_uses_sidecar_identity(self):
        path=self.job('企业甲','仓管',project_id='warehouse-local',candidate_namespace='stable-record-id')
        self.assertEqual(project_registry.read_project(path)['project_id'],'warehouse-local')
        plan=self.plan('企业甲')
        self.assertEqual(quick_start.refresh_selected(plan,self.db)['state'],'ready_to_start')
        db=ledger.connect(self.root/'test.sqlite')
        self.addCleanup(db.close)
        from argparse import Namespace
        captured=io.StringIO()
        with contextlib.redirect_stdout(captured):
            ledger.start(db,Namespace(profile=path,target=1,max_views=2,min_score=70))
        self.assertEqual(json.loads(captured.getvalue())['state'],'started')
        rules=json.loads(db.execute('SELECT rule_snapshot FROM runs').fetchone()[0])
        self.assertEqual(rules['namespace'],'stable-record-id')
        self.assertEqual(rules['hr_job_config'],hr_job.parse(path.read_text(encoding='utf-8')))

    def test_cli_reads_live_folder_instead_of_bundled_profiles(self):
        self.job('01 本地企业','本地岗位')
        result=io.StringIO()
        with patch('sys.argv',['quick_start.py','--prompt','查看所有','--db',str(self.db)]),contextlib.redirect_stdout(result):
            quick_start.main()
        self.assertEqual(json.loads(result.getvalue())['companies'][0]['company'],'本地企业')


if __name__=='__main__':unittest.main()
