import csv
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import Workbook,load_workbook
import card_layout
import csv_report
import minimum_view_wait
import resume_highlight
import candidate_checks
import coworker_progress
import page_layout


class ReleaseTests(unittest.TestCase):
    def test_unusable_layout_pauses_the_persistent_run(self):
        import argparse,contextlib,io
        from unittest.mock import Mock
        import ledger
        from workflow_runner import Runner
        from test_hr_job import document
        with contextlib.ExitStack() as stack:
            tmp=stack.enter_context(tempfile.TemporaryDirectory());root=Path(tmp)
            profile=root/'Company'/'job.md';profile.parent.mkdir()
            profile.write_text(document(resume_words='组装'),encoding='utf-8')
            with patch.object(ledger,'PROFILE_ROOT',root):
                db=ledger.connect(root/'ledger.sqlite');stack.callback(db.close)
                with contextlib.redirect_stdout(io.StringIO()):ledger.start(db,argparse.Namespace(profile=profile,target=2,max_views=4,min_score=60))
            runner=Runner.__new__(Runner);runner.db=db;runner.run=db.execute('SELECT run_id FROM runs').fetchone()[0]
            runner.phase='select';runner.data={};runner.save=Mock()
            runner.status=lambda state=None:dict(state=state,error=runner.data.get('error'))
            runner.step=Mock(side_effect=page_layout.LayoutBlocked('控件裁切'))
            result=runner.advance()
            self.assertEqual(result['state'],'paused')
            self.assertEqual(ledger.control_state(db,runner.run),'paused')
            self.assertIn('控件裁切',result['error'])

    def test_zoom_prepare_checks_actual_layout_and_records_rollback(self):
        from unittest.mock import Mock
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;self.addCleanup(db.close)
        db.execute('CREATE TABLE settings(key PRIMARY KEY,value)')
        adapter=Mock(db=db,run='live-probe')
        adapter.query.side_effect=[dict(state='read',fits=False),dict(state='read',fits=True)]
        with patch('page_layout.query',side_effect=[dict(state='read',percent=100,binding_id='bound'),dict(state='read',percent=90)]) as query:
            page_layout.prepare(adapter)
        self.assertEqual(query.call_args_list[-1].args,('Set',90,'bound'))
        record=json.loads(db.execute('SELECT value FROM settings').fetchone()[0])
        self.assertEqual((record['original'],record['last']),(100,90))
        adapter.query.side_effect=[dict(state='read',fits=False)]
        with patch('page_layout.query',side_effect=[dict(state='read',percent=90,binding_id='bound'),dict(state='unsupported',percent=80)]):
            with self.assertRaisesRegex(ValueError,'无法确认'):page_layout.prepare(adapter)
        record=json.loads(db.execute('SELECT value FROM settings').fetchone()[0])
        self.assertEqual(record['last'],80)

    def test_zoom_restore_preserves_user_change(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;self.addCleanup(db.close)
        db.execute('CREATE TABLE settings(key PRIMARY KEY,value)')
        record=dict(original=100,last=80,binding_id='bound',restored=False)
        db.execute('INSERT INTO settings VALUES (?,?)',('boss_zoom/r',json.dumps(record)))
        with patch('page_layout.query',return_value=dict(state='read',percent=90)) as query:
            self.assertEqual(page_layout.restore(db,'r'),'user_changed_zoom_preserved')
            query.assert_called_once_with(expected='bound')
        db.execute('UPDATE settings SET value=?',(json.dumps(record),))
        with patch('page_layout.query',side_effect=[dict(state='read',percent=80),dict(state='read',percent=100)]) as query:
            self.assertEqual(page_layout.restore(db,'r'),'restored')
            self.assertEqual(query.call_args_list[-1].args,('Set',100,'bound'))

    def test_relative_dates_do_not_drift_on_recheck(self):
        observed='2026-11-12T10:00:00+08:00'
        data=dict(state='records',evidence='昨天联系',observed_at=observed,records=['昨天'],records_complete=True)
        self.assertTrue(coworker_progress.evaluate_for_rules(data,dict(coworker_notice_policy=1),datetime.fromisoformat(observed))['skip'])
        later=datetime.fromisoformat('2026-11-22T10:00:00+08:00')
        result=coworker_progress.evaluate_for_rules(data,dict(coworker_notice_policy=1),later)
        self.assertTrue(result['may_continue']);self.assertFalse(result.get('notice_required',False))

    def test_coworker_notice_is_required_and_bound_to_observation(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row;self.addCleanup(db.close)
        run=dict(generation=1,rule_snapshot=json.dumps(dict(coworker_notice_policy=1,mode='resume')))
        observation=dict(state='unavailable',evidence='record list unreadable')
        with patch('ledger.run_row',return_value=run),patch('ledger.run_candidate_hash',return_value='visit'):
            self.assertFalse(candidate_checks.evaluate_resume(db,'r','c',observation)['may_continue'])
            notice=candidate_checks.notice_id(db,'r','c',observation)
            with self.assertRaises(ValueError):candidate_checks.acknowledge_notice(db,'r','c',observation,dict(notice_id=notice,displayed=False))
            candidate_checks.acknowledge_notice(db,'r','c',observation,dict(notice_id=notice,displayed=True))
            self.assertTrue(candidate_checks.evaluate_resume(db,'r','c',observation)['may_continue'])
            self.assertFalse(candidate_checks.evaluate_resume(db,'r','c',dict(observation,evidence='changed'))['may_continue'])
            run['generation']=2
            self.assertFalse(candidate_checks.evaluate_resume(db,'r','c',observation)['may_continue'])

    def test_recent_known_contact_always_wins(self):
        now=datetime.now(timezone.utc)
        result=coworker_progress.evaluate_for_rules(dict(state='unavailable',records=[now.isoformat()]),dict(coworker_notice_policy=1),now)
        self.assertTrue(result['skip'])
        self.assertFalse(result['may_continue'])
        observed='2026-11-12T10:00:00+08:00'
        result=coworker_progress.evaluate_for_rules(dict(state='records',evidence='昨天联系',observed_at=observed,
            records=['昨天'],records_complete=True),dict(coworker_notice_policy=1),datetime.fromisoformat(observed))
        self.assertTrue(result['skip'])
        unknown=coworker_progress.evaluate_for_rules(dict(state='records',evidence='11-11联系',observed_at=observed,
            records=['11-11'],records_complete=True),dict(coworker_notice_policy=1),datetime.fromisoformat(observed))
        self.assertTrue(unknown['notice_required'])

    def test_notice_survives_recording_and_reservation_recheck(self):
        import argparse,contextlib,io,shutil
        import ledger,candidate_log,recruiting_rules
        from test_hr_job import document
        with contextlib.ExitStack() as stack:
            tmp=stack.enter_context(tempfile.TemporaryDirectory());root=Path(tmp)
            profile=root/'Company'/'job.md';profile.parent.mkdir()
            profile.write_text(document(resume_words='组装'),encoding='utf-8')
            with patch.object(ledger,'PROFILE_ROOT',root):
                db=ledger.connect(root/'ledger.sqlite');stack.callback(db.close)
                with contextlib.redirect_stdout(io.StringIO()):ledger.start(db,argparse.Namespace(profile=profile,target=2,max_views=4,min_score=60))
            run=db.execute('SELECT * FROM runs').fetchone();rid=run['run_id'];cid='candidate'
            candidate_log.table(db)
            ledger.ensure_candidate(db,rid,cid)
            observation=dict(state='unavailable',evidence='record list unreadable',observed_at=datetime.now(timezone.utc).isoformat())
            self.assertFalse(candidate_checks.record(db,rid,cid,observation)['may_continue'])
            notice=candidate_checks.notice_id(db,rid,cid,observation)
            candidate_checks.acknowledge_notice(db,rid,cid,observation,dict(notice_id=notice,displayed=True))
            payload=dict(candidate_id=cid,candidate_name='虚构候选人',keyword_text='有组装经历',read_complete=True,
                decision='greet',overall_score=60,electronic_resume_enabled=True,electronic=dict(score=60,evidence='组装经历'),
                hard_requirements=False,pros='有组装经历',cons='其他信息待核实',coworker_progress=observation)
            with patch('csv_report.setup_viewer',side_effect=lambda template,target,specs,configure=None:shutil.copy2(template,target)),contextlib.redirect_stdout(io.StringIO()):
                candidate_log.record(db,argparse.Namespace(run=rid,output_root=root),payload)
            stored=json.loads(db.execute('SELECT coworker_progress FROM assessments').fetchone()[0])
            self.assertEqual(stored,observation)
            self.assertTrue(candidate_checks.evaluate_resume(db,rid,cid,stored)['may_continue'])
            output=io.StringIO()
            with contextlib.redirect_stdout(output):ledger.reserve(db,argparse.Namespace(run=rid,candidate_id=cid))
            self.assertEqual(json.loads(output.getvalue())['state'],'ready')

    def test_migration_exact_token_and_annotations(self):
        import migrate_worker1410
        from test_hr_job import document
        import hr_job
        text=document(list_negative='主管、销售',resume_negative='主管（🔴建议删除）、生产主管、经理')
        changed=migrate_worker1410.changed(text)
        data=hr_job.parse(changed)
        self.assertEqual(data['list']['negative'],['销售'])
        self.assertEqual(data['resume']['negative'],['生产主管','经理'])

    def test_per_resume_wait_not_average_and_restart(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        self.addCleanup(db.close)
        cfg=dict(average_seconds=30,rest_seconds=0)
        self.assertEqual(minimum_view_wait.plan(db,'r','a',12,cfg,12)['retry_after_seconds'],18)
        self.assertEqual(minimum_view_wait.plan(db,'r','a',99,cfg,20)['retry_after_seconds'],10)
        self.assertEqual(minimum_view_wait.plan(db,'r','a',99,cfg,30)['retry_after_seconds'],0)
        self.assertEqual(minimum_view_wait.plan(db,'r','b',35,cfg,65)['retry_after_seconds'],0)
        self.assertEqual(minimum_view_wait.plan(db,'r','c',12,cfg,77)['retry_after_seconds'],18)

    def test_two_columns_and_rebuilt_runtime(self):
        def c(r,x,y):return dict(card_runtime=r,summary='同名同摘要',bounds=dict(x=x,y=y),scroll_percent=0)
        cards=[c('c',0,200),c('b',400,0),c('a',0,0)]
        self.assertEqual([c['card_runtime'] for c in card_layout.ordered(cards)],['a','b','c'])
        self.assertEqual(card_layout.choose(cards,[card_layout.receipt(cards[2])])['card_runtime'],'b')
        replacement=dict(cards[2],card_runtime='new')
        self.assertEqual(card_layout.choose([replacement,cards[1]],[card_layout.receipt(cards[2])])['card_runtime'],'b')

    def test_character_geometry_and_negation(self):
        ocr=dict(lines=[dict(text='组装主管',characters=[dict(text=t,score=.99,box=[i*20,0,i*20+20,30]) for i,t in enumerate('组装主管')])])
        located,missing=resume_highlight.geometry(ocr,[dict(word='主管',start=2,end=4,negative=True)])
        self.assertEqual(located[0]['boxes'],[[40,0,80,30]])
        self.assertFalse(missing)
        self.assertFalse(resume_highlight.spans('没有做过主管',[dict(word='主管',quote='没有做过主管')]))
        ocr['lines'][0]['characters'][2]['score']=.1
        self.assertTrue(resume_highlight.geometry(ocr,[dict(word='主管',start=2,end=4,negative=True)])[1])

    def test_atomic_csv_failure_preserves_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data.csv';path.write_text('previous',encoding='utf-8')
            with patch('csv_report.os.replace',side_effect=PermissionError),patch('csv_report.time.sleep'):
                with self.assertRaises(PermissionError):csv_report.atomic_csv(path,['列'],[['新值']])
            self.assertEqual(path.read_text(encoding='utf-8'),'previous')
            self.assertEqual(len(list(Path(tmp).iterdir())),1)

    def test_export_and_viewer_migration_recovery(self):
        import argparse,contextlib,io,shutil
        import ledger,candidate_log,report_store
        from test_hr_job import document
        with contextlib.ExitStack() as stack:
            tmp=stack.enter_context(tempfile.TemporaryDirectory())
            root=Path(tmp);profile=root/'Company'/'job.md';profile.parent.mkdir()
            profile.write_text(document(resume_words='组装'),encoding='utf-8')
            with patch.object(ledger,'PROFILE_ROOT',root):
                db=ledger.connect(root/'ledger.sqlite');stack.callback(db.close)
                with contextlib.redirect_stdout(io.StringIO()):
                    ledger.start(db,argparse.Namespace(profile=profile,target=2,max_views=4,min_score=60))
            run=db.execute('SELECT * FROM runs').fetchone();stamp=run['started_at']
            candidate_log.table(db);report_store.backfill(db)
            original=report_store.destination(db,root,stamp,profile)
            candidate_log._render_workbook(db,root,stamp,profile_path=profile,_destination=original)
            before=original.read_bytes()
            def failed(*args):raise ValueError('synthetic Excel not ready')
            candidate_log.workbook  # Public entry dispatches to this exporter.
            with self.assertRaisesRegex(ValueError,'CSV已更新'):
                csv_report.export(db,root,stamp,profile,configure=failed)
            state=db.execute('SELECT * FROM report_sync').fetchone()
            target=Path(state['viewer_path'])
            self.assertEqual((state['data_pending'],state['viewer_pending']),(0,1))
            self.assertTrue(list(Path(state['data_dir']).glob('*.csv')))
            self.assertEqual(report_store.destination(db,root,stamp,profile),original)
            self.assertEqual(original.read_bytes(),before)
            def configured(template,target,specs):shutil.copy2(template,target)
            self.assertEqual(csv_report.export(db,root,stamp,profile,configure=configured),target)
            self.assertEqual(report_store.destination(db,root,stamp,profile),target)
            self.assertEqual(db.execute('SELECT viewer_pending FROM report_sync').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM report_path_aliases').fetchone()[0],1)
            after=target.read_bytes()
            csv_report.export(db,root,stamp,profile,configure=failed)
            self.assertEqual(target.read_bytes(),after)
            self.assertEqual(original.read_bytes(),before)


class ExcelIntegration(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('RUN_EXCEL_QA')=='1','explicit isolated Excel integration')
    def test_actual_connections_and_first_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);wb=Workbook();ws=wb.active;ws.title='候选人简报'
            ws.append(['测试统计']);ws.append(['录入时间','候选人','综合分','判定','判断时长','优点','缺点','命中词','触发方式','招呼结果','查看简历','原图'])
            ws.append(['10:00','虚构测试人',60,'简历不合格','12秒','','','组装','','skipped','未保存','未保存'])
            template=folder/'template.xlsx';wb.save(template)
            specs=csv_report.datasets(wb,folder,'first','2026-11-12T10:00:00+08:00')
            target=folder/'viewer.xlsx'
            csv_report.setup_viewer(template,target,specs)
            with __import__('zipfile').ZipFile(target) as z:
                self.assertIn('xl/connections.xml',z.namelist())
            read=load_workbook(target,data_only=True)
            self.assertEqual(read['候选人简报']['B3'].value,'虚构测试人')
            self.assertEqual(read['数据刷新']['B2'].value,'已刷新至同一批次')
            read.close()
            if os.environ.get('RUN_EXCEL_TIMER_QA')=='1':
                import subprocess,time,powershell_host
                from windows_process import hidden_options
                ready=folder/'ready';result=folder/'result.json'
                with subprocess.Popen(powershell_host.command(Path(__file__).with_name('qa-excel-refresh.ps1'),
                        '-Workbook',target,'-Ready',ready,'-Result',result),stdout=subprocess.PIPE,stderr=subprocess.PIPE,**hidden_options()) as child:
                    try:
                        deadline=time.monotonic()+175
                        while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.2)
                        self.assertTrue(ready.exists())
                        for n,name in enumerate(('第二批虚构记录','第三批虚构记录'),2):
                            ws['B3']=name
                            ws.append(['10:01','新增虚构记录'+str(n),60,'待复核','12秒','','','组装','','skipped','未保存','未保存'])
                            csv_report.datasets(wb,folder,str(n),'2026-11-12T10:00:00+08:00')
                            while time.monotonic()<deadline:
                                if result.exists():
                                    data=json.loads(result.read_text(encoding='utf-8-sig'))
                                    if name in data.get('seen',[]):break
                                if child.poll() is not None:self.fail('Excel QA ended before '+name)
                                time.sleep(.4)
                            else:self.fail('timed refresh did not show '+name)
                        out,err=child.communicate(timeout=12)
                        self.assertEqual(child.returncode,0,err.decode('utf-8',errors='replace'))
                        data=json.loads(result.read_text(encoding='utf-8-sig'))
                        self.assertEqual(data['state'],'verified')
                        self.assertEqual(data['rows'],3)
                        self.assertGreater(data['conditions'],0)
                        self.assertIn('HYPERLINK',data['formula'])
                    finally:
                        if child.poll() is None:child.kill();child.communicate()


if __name__=='__main__':unittest.main()
