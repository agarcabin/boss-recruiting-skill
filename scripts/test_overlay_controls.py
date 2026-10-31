"""Overlay speed, phase timing, strict favorite threshold and model interruption."""
import contextlib
import json
import os
import subprocess
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import ledger,progress_window,stop_controller,ui_features,windows_process,workflow_runner
from test_relaxed_controls import RelaxedControlsTests,call
from test_flow_optimizations import FakeAdapter


class OverlayControlsTests(unittest.TestCase):
    setUp=RelaxedControlsTests.setUp
    start=RelaxedControlsTests.start
    payload=RelaxedControlsTests.payload
    record=RelaxedControlsTests.record

    def test_average_samples_only_view_count_changes_and_survives_reopen(self):
        average=progress_window.viewing_average
        self.assertIsNone(average(self.db,self.run,0,20))
        self.assertEqual(average(self.db,self.run,1,30),30)
        self.assertEqual(average(self.db,self.run,1,90),30)
        with contextlib.closing(ledger.connect(self.root/'ledger.db')) as other:
            self.assertEqual(average(other,self.run,1,99),30)
        self.assertEqual(average(self.db,self.run,2,101),50.5)

    def test_speed_uses_current_run_views_and_active_time(self):
        base=ledger.parse_time(ledger.run_row(self.db,self.run)['started_at'])
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=30)):
            call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-one')
            data=progress_window.snapshot(self.db,self.run,self.root)
            self.assertEqual(data['viewing_average_seconds'],30)
            call(ledger.control,self.db,run=self.run,action='pause')
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=90)):
            self.assertEqual(progress_window.snapshot(self.db,self.run,self.root)['viewing_average_seconds'],30)
            call(ledger.control,self.db,run=self.run,action='resume')
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=100)):
            call(ledger.candidate_finish,self.db,run=self.run,candidate_id='candidate-one')
            call(ledger.candidate_begin,self.db,run=self.run,candidate_id='candidate-two')
            self.assertEqual(progress_window.snapshot(self.db,self.run,self.root)['viewing_average_seconds'],20)

    def test_open_name_visible_before_candidate_is_registered_and_stage_resets(self):
        base=ledger.parse_time(ledger.run_row(self.db,self.run)['started_at'])
        adapter=FakeAdapter([dict(candidate_id='candidate-one',candidate_name='王先生')])
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=10)):
            runner=workflow_runner.Runner(self.db,self.run,adapter,self.root)
            runner.step();runner.save()
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=15)):
            self.assertEqual(progress_window.snapshot(self.db,self.run,self.root)['current_step'],'正在打开电子简历 - 王先生 - 5 秒')
            runner.phase='assess';runner.save()
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=18)):
            self.assertEqual(progress_window.snapshot(self.db,self.run,self.root)['current_step'],'正在分析电子简历 - 王先生 - 3 秒')
            call(ledger.control,self.db,run=self.run,action='pause')
        with patch.object(ledger,'now',return_value=base+timedelta(seconds=80)):
            call(ledger.control,self.db,run=self.run,action='resume')
            self.assertIn('王先生 - 3 秒',progress_window.snapshot(self.db,self.run,self.root)['current_step'])

    def test_strict_favorite_boundary_independent_of_sent_status(self):
        self.record(overall_score=95,electronic=dict(score=95,evidence='实际简历评分95'))
        digest=ledger.run_candidate_hash(self.db,self.run,'candidate-one')
        for score in (0,80,89,90):
            self.db.execute('UPDATE assessments SET overall_score=?',(score,))
            reader=Mock();click=Mock()
            result=ui_features.favorite(self.db,self.run,'candidate-one',reader=reader,click=click)
            self.assertEqual(result['state'],'not_applicable')
            reader.assert_not_called();click.assert_not_called()
        self.db.execute('UPDATE assessments SET overall_score=91')
        reader=Mock(side_effect=[dict(state='unsaved',target={}),dict(state='saved')]);click=Mock()
        self.assertEqual(ui_features.favorite(self.db,self.run,'candidate-one',reader=reader,click=click)['state'],'saved')
        click.assert_called_once()
        self.assertTrue(ui_features.favorite_eligible(self.db,self.run,digest))

    def test_low_scored_success_does_not_open_resume_for_favorite(self):
        self.record(overall_score=80)
        from workflow_windows import WindowsAdapter
        adapter=WindowsAdapter(self.db,self.run,self.root)
        adapter.invoke=Mock()
        self.assertEqual(adapter.favorite(dict(candidate_id='candidate-one',open_target={}), 'card')['state'],'not_applicable')
        adapter.invoke.assert_not_called()

    def test_pause_interrupts_model_and_resume_requires_chat(self):
        window=progress_window.ProgressWindow.__new__(progress_window.ProgressWindow)
        window.db_path=self.root/'ledger.db';window.run_id=self.run;window.demo=False
        window.read=Mock(return_value=dict(state='running'));window.change=Mock()
        def immediate(target,daemon):return SimpleNamespace(start=target)
        with patch.object(progress_window.threading,'Thread',side_effect=immediate),patch.object(stop_controller,'interrupt_run') as interrupt:
            window.pause_or_resume()
            window.change.assert_called_once_with('pause');interrupt.assert_called_once()
            window.read.return_value=dict(state='paused')
            window.pause_or_resume()
            self.assertEqual(window.change.call_count,1)

    def test_interrupt_records_success_and_binding_failure(self):
        with patch.object(stop_controller,'bind_run',return_value=dict(kind='uia')),patch.object(stop_controller,'binding_action',return_value=dict(state='interrupted')) as action:
            self.assertEqual(stop_controller.interrupt_run(self.db,self.run),'interrupted')
            action.assert_called_once_with(dict(kind='uia'),True)
        with patch.object(stop_controller,'bind_run',side_effect=RuntimeError('wrong chat')):
            self.assertIn('failed: wrong chat',stop_controller.interrupt_run(self.db,self.run))
            self.assertIn('wrong chat',ledger.run_row(self.db,self.run)['interrupt_status'])

    def test_custom_title_is_retained_after_failed_initial_bind(self):
        with patch.object(stop_controller.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr=b'not visible')) as execute:
            for title in ('自定义招聘聊天',None):
                with self.assertRaisesRegex(RuntimeError,'not visible'):
                    stop_controller.bind_run(self.db,self.run,title)
            self.assertIn('自定义招聘聊天',execute.call_args.args[0])

    def test_stale_workflow_gets_phase_clock_without_resetting_new_clocks(self):
        runner=workflow_runner.Runner(self.db,self.run,FakeAdapter([]),self.root)
        runner.data.pop('phase_started_elapsed');runner.save()
        first=runner.data['phase_started_elapsed']
        with patch.object(ledger,'active_elapsed_seconds',return_value=999):
            runner.save()
            self.assertEqual(runner.data['phase_started_elapsed'],first)

    def test_end_interrupts_before_final_report_even_without_prior_binding(self):
        import run_safety
        run_safety.request_stop(self.db,self.run,'manual_stop')
        events=[]
        def interrupt(db,run):
            events.append('interrupt');db.execute("UPDATE runs SET interrupt_status='interrupted' WHERE run_id=?",(run,))
        def report(*args):events.append('report');return self.root/'final.xlsx'
        with patch.object(stop_controller,'interrupt_run',side_effect=interrupt),patch.object(stop_controller,'final_report',side_effect=report):
            stop_controller.finalize(self.db,self.run,self.root,opener=lambda _:None)
        self.assertEqual(events,['interrupt','report'])


class HiddenProcessTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows process flags')
    def test_background_python_has_no_console_and_output_is_preserved(self):
        code='import ctypes; print(bool(ctypes.windll.kernel32.GetConsoleWindow()))'
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True,**windows_process.hidden_options())
        self.assertEqual(result.stdout.strip(),'False')

    @unittest.skipUnless(os.name=='nt','Windows process flags')
    def test_powershell_and_nested_python_also_have_no_console(self):
        import powershell_host
        command=powershell_host.command(Path(__file__).with_name('app-server-stop.ps1'))[:1]
        code='import ctypes; print(bool(ctypes.windll.kernel32.GetConsoleWindow()))'
        ps="& '"+sys.executable.replace("'","''")+"' -c '"+code+"'"
        result=subprocess.run(command+['-NoProfile','-Command',ps],capture_output=True,text=True,check=True,**windows_process.hidden_options())
        self.assertEqual(result.stdout.strip(),'False')


if __name__=='__main__':unittest.main()
