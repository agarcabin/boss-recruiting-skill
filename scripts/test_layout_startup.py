import json, os, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
import page_layout

class LayoutStartupTests(unittest.TestCase):
    def exercise(self, fits):
        with tempfile.TemporaryDirectory() as tmp:
            binding=Path(tmp)/'binding.json'
            binding.write_text(json.dumps({'chat_title':'Test chat'}))
            db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
            adapter=Mock(db=db,run='test')
            adapter.query.side_effect=[{'state':'read','fits':value} for value in fits]
            def zoom(action='Read',percent=100,expected=None):
                return {'state':'read','percent':percent,'binding_id':'test'}
            with patch.dict(os.environ,{'BOSS_BROWSER_BINDING':str(binding)}), patch.object(page_layout,'ensure_sidebar_hidden',return_value={'state':'collapsed','chat_title':'Test chat'}) as sidebar, patch.object(page_layout,'query',side_effect=zoom) as query:
                try: page_layout.prepare(adapter)
                except page_layout.LayoutBlocked:
                    if any(fits):raise
                sidebar.assert_called_once_with('Test chat')
                self.assertIsNotNone(db.execute('SELECT value FROM settings WHERE key=?',('sidebar_check/test',)).fetchone())
                return [call.args[1] for call in query.call_args_list if call.args and call.args[0]=='Set']
    def test_reaches_fifty(self):self.assertEqual(self.exercise([False]*6),[90,80,70,60,50])
    def test_stops_when_fits(self):self.assertEqual(self.exercise([False,False,False,True]),[90,80,70])
    def test_no_zoom_if_fits(self):self.assertEqual(self.exercise([True]),[])
    def test_sidebar_failure_blocks_layout_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            binding=Path(tmp)/'binding.json';binding.write_text(json.dumps({'chat_title':'Test chat'}))
            adapter=Mock()
            with patch.dict(os.environ,{'BOSS_BROWSER_BINDING':str(binding)}),patch.object(page_layout,'ensure_sidebar_hidden',side_effect=page_layout.LayoutBlocked('failed')):
                with self.assertRaises(page_layout.LayoutBlocked):page_layout.prepare(adapter)
            adapter.query.assert_not_called()
    def test_start_direct_blocked_before_run_creation(self):
        import quick_start
        plan={'state':'ready_to_start','run':None,'chat_title':'Test chat'}
        with patch('sys.argv',['quick_start','--plan','fake.json','--start-direct']),patch('quick_start.startup_plan.load',return_value=plan),patch('quick_start.refresh_selected',return_value=plan),patch('page_layout.ensure_sidebar_hidden',side_effect=page_layout.LayoutBlocked('failed')),patch('quick_start.ledger.connect') as connect:
            with self.assertRaises(page_layout.LayoutBlocked):quick_start.main()
            connect.assert_not_called()
    def test_unconfirmed_receipt_rejected(self):
        with patch('page_layout.powershell_host.command',return_value=['fake']),patch('page_layout.subprocess.run',return_value=Mock(returncode=0,stdout=b'{"state":"unknown"}')):
            with self.assertRaises(page_layout.LayoutBlocked):page_layout.ensure_sidebar_hidden('Test chat')
    def test_unknown_control_is_not_reported_as_clipping(self):
        for reason in ('filter_control_not_found','filter_control_not_unique'):
            adapter=Mock()
            adapter.query.return_value={'state':'unknown','reason':reason}
            with self.assertRaisesRegex(page_layout.LayoutBlocked,'页面控件识别失败') as error:
                page_layout.read_layout(adapter)
            self.assertNotIn('请扩大窗口',str(error.exception))

    def test_filter_label_variants(self):
        import subprocess
        helper=Path(__file__).with_name('filter-control.ps1')
        command=". '"+str(helper)+"'; $yes=@('筛选','筛选·4','筛选 · 4','筛选（4）','筛选(4)','筛选4','筛选条件：4'); $no=@('筛选候选人','其他筛选·4','筛选·4更多'); foreach($label in $yes){if(!(Test-BossFilterLabel $label)){throw $label}}; foreach($label in $no){if(Test-BossFilterLabel $label){throw $label}}"
        result=subprocess.run(['pwsh','-NoProfile','-Command',command],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
