"""Synthetic image and shutdown checks; no BOSS actions or real Excel launches."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from PIL import Image,ImageColor,ImageDraw
import ledger
import progress_window
import resume_highlight
import run_safety
import stop_controller
import test_capture_control as fixtures


class HighlightTests(unittest.TestCase):
    def test_group_hits_use_distinct_colors(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'resume.png';data=source.with_suffix('.json')
            Image.new('RGB',(80,40),'white').save(source)
            text='AB'
            ocr=dict(lines=[dict(text=text,characters=[dict(text=t,score=.99,box=[10+i*25,5,30+i*25,30]) for i,t in enumerate(text)])])
            data.write_text(json.dumps(ocr),encoding='utf-8')
            result=dict(hits=[dict(word='A',group='A',quote='A'),dict(word='B',group='B',quote='B')],negative_hits=[])
            marked=Path(resume_highlight.create(dict(image=str(source),ocr_json=str(data)),result))
            with Image.open(marked) as rendered:
                self.assertEqual(rendered.getpixel((10,5)),ImageColor.getrgb('#39FF14'))
                self.assertEqual(rendered.getpixel((35,5)),ImageColor.getrgb('#00FFFF'))

    def test_fluorescent_spans_keep_text_and_source_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'resume.png';data=source.with_suffix('.json')
            image=Image.new('RGB',(200,80),'white')
            ImageDraw.Draw(image).rectangle((17,17,19,19),fill='black')
            image.save(source)
            text='HIRE SALES'
            ocr=dict(lines=[dict(text=text,characters=[dict(text=t,score=.99,
                box=[10+i*15,10,25+i*15,35]) for i,t in enumerate(text)])])
            data.write_text(json.dumps(ocr),encoding='utf-8')
            before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,data)]
            result=dict(hits=[dict(word='HIRE',quote=text)],negative_hits=[dict(word='SALES',quote=text)])
            marked=Path(resume_highlight.create(dict(image=str(source),ocr_json=str(data)),result))
            with Image.open(marked) as rendered:
                self.assertEqual(rendered.getpixel((10,10)),ImageColor.getrgb('#39FF14'))
                self.assertEqual(rendered.getpixel((85,10)),ImageColor.getrgb('#FF3131'))
                self.assertNotEqual(rendered.getpixel((30,20)),(255,255,255))
                self.assertLessEqual(max(rendered.getpixel((18,18))),64)
                self.assertEqual(rendered.getpixel((180,60)),(255,255,255))
            self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,data)])
            meta=json.loads(marked.with_suffix('.json').read_text(encoding='utf-8'))
            self.assertEqual(len(meta['located']),2)
            self.assertFalse(meta['unlocated'])

    def test_negative_fluorescent_border_wins_on_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'resume.png';data=source.with_suffix('.json')
            Image.new('RGB',(60,60),'white').save(source)
            data.write_text(json.dumps(dict(lines=[dict(text='A',characters=[
                dict(text='A',score=.99,box=[10,10,30,30])])])),encoding='utf-8')
            hit=dict(word='A',quote='A')
            target=resume_highlight.create(dict(image=str(source),ocr_json=str(data)),dict(hits=[hit],negative_hits=[hit]))
            with Image.open(target) as rendered:
                self.assertEqual(rendered.getpixel((10,10)),ImageColor.getrgb('#FF3131'))


class FinishWindowTests(unittest.TestCase):
    def setUp(self):
        self.window=progress_window.ProgressWindow.__new__(progress_window.ProgressWindow)
        self.window.root=Mock();self.window.demo=True;self.window.wake=Mock()
        self.window.status_canvas=Mock();self.window.button_canvas=Mock()
        self.window.state_dot=1;self.window.state_item=2;self.window.detail_item=3
        self.window.button_rects=[4,5,6];self.window.button_texts=[7,8,9]
        self.window.db_path=Path('synthetic.sqlite');self.window.run_id='synthetic'
        self.window.output_root=Path('synthetic-reports');self.window.timer='refresh-timer'
        self.window.terminating=True

    def test_close_status_is_immediate_and_repeated_click_is_ignored(self):
        self.window.terminating=False
        with patch('progress_window.threading.Thread') as worker,patch('progress_window.messagebox.askyesno') as ask:
            self.window.begin_termination('manual_stop')
            self.window.stop()
            self.assertEqual(worker.call_count,1)
            self.assertFalse(any(self.window.button_enabled))
            self.window.status_canvas.itemconfigure.assert_any_call(2,text='正在关闭……')
            self.window.root.after_cancel.assert_called_once_with('refresh-timer')
            self.window.root.destroy.assert_not_called()
            self.window.open_report()
            self.window.pause_or_resume()
            self.window.refresh()
            ask.assert_not_called()

    def test_pending_shutdown_does_not_ask_or_open_excel(self):
        self.window.termination_result=None
        with patch('progress_window.messagebox.askyesno') as ask,patch('progress_window.os.startfile') as open_file:
            self.window.finish_termination()
            ask.assert_not_called();open_file.assert_not_called()
            self.window.root.destroy.assert_not_called()
            self.window.root.after.assert_called_once_with(100,self.window.finish_termination)

    def test_yes_opens_once_and_no_does_not_open(self):
        for answer in (True,False):
            with self.subTest(answer=answer):
                self.window.root.reset_mock()
                self.window.termination_result=(Path('report.xlsx'),None)
                events=[]
                with patch('progress_window.messagebox.askyesno',side_effect=lambda *a,**k:events.append('ask') or answer) as ask,patch(
                    'progress_window.os.startfile',side_effect=lambda p:events.append('open')) as open_file:
                    self.window.root.destroy.side_effect=lambda:events.append('closed')
                    self.window.finish_termination()
                    ask.assert_called_once()
                    self.assertEqual(open_file.call_count,int(answer))
                    self.assertEqual(events,['ask','open','closed'] if answer else ['ask','closed'])

    def test_failure_stays_red_and_allows_retry_without_excel_prompt(self):
        self.window.termination_result=(None,'synthetic write failure')
        with patch('progress_window.messagebox.showerror') as error,patch('progress_window.messagebox.askyesno') as ask:
            self.window.finish_termination()
            error.assert_called_once();ask.assert_not_called()
            self.window.root.destroy.assert_not_called()
            self.assertFalse(self.window.terminating)
            self.assertTrue(self.window.button_enabled[1])
            self.window.status_canvas.itemconfigure.assert_any_call(1,fill=progress_window.SIGNAL_COLORS['red'])

    def test_pending_report_and_launch_failure_are_explained(self):
        for report in (None,Path('report.xlsx')):
            with self.subTest(report=report):
                self.window.termination_result=(report,None)
                with patch('progress_window.messagebox.askyesno',return_value=True),patch(
                    'progress_window.messagebox.showinfo') as info,patch('progress_window.messagebox.showerror') as error,patch(
                    'progress_window.os.startfile',side_effect=OSError('synthetic Excel unavailable')) as open_file:
                    self.window.finish_termination()
                    if report:
                        open_file.assert_called_once();error.assert_called_once();info.assert_not_called()
                    else:
                        open_file.assert_not_called();info.assert_called_once();error.assert_not_called()


class BackgroundFinalizeTests(unittest.TestCase):
    def setUp(self):fixtures.CaptureControlTests.setUp(self)

    def test_background_finalize_cannot_open_excel_before_user_choice(self):
        report=self.root/'report.xlsx';report.write_bytes(b'synthetic')
        run_safety.request_stop(self.db,self.run,'manual_stop')
        with patch('stop_controller.final_report',return_value=report),patch('page_layout.restore'),patch(
            'stop_controller.report_status',return_value=dict(report_pending=False)),patch('stop_controller.os.startfile') as open_file:
            result=stop_controller.finalize(self.db,self.run,self.root,interrupt=False)
            self.assertEqual(result,report)
            self.assertIsNotNone(ledger.run_row(self.db,self.run)['finalized_at'])
            open_file.assert_not_called()


if __name__=='__main__':unittest.main()
