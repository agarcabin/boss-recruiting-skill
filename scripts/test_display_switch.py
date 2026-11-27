"""Display routing, binding failures, passive overlay placement and capture visibility."""
import contextlib
import ctypes
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import display_switch
import foreground_activity
import progress_window
import powershell_host
import launch_progress
import virtual_display


PRIMARY=dict(handle=1,device='primary',primary=True,bounds=(0,0,1920,1080),work=(0,0,1920,1040))
SECONDARY=dict(handle=2,device='secondary',primary=False,bounds=(-1920,0,0,1080),work=(-1920,0,0,1080))


class DisplayRoutingTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
        self.addCleanup(self.db.close)
        self.native=Mock()
        self.native.window_pid.return_value=42
        self.native.monitors.return_value=[PRIMARY,SECONDARY]
        self.binding=dict(state='bound',hwnd=123,process_id=42,binding_id='binding')

    def toggle(self):
        with patch.object(display_switch,'bound_window',return_value=self.binding),patch.object(display_switch.run_safety,'action_lock',return_value=contextlib.nullcontext()):
            return display_switch.toggle(self.db,'run',self.native)

    def test_primary_to_secondary_and_back(self):
        self.native.monitor_for_window.side_effect=[1,2,2,1]
        self.assertEqual(self.toggle()['display'],'副屏')
        self.assertEqual(self.toggle()['display'],'主屏')
        self.assertEqual([call.args for call in self.native.move.call_args_list],[(123,SECONDARY['work']),(123,PRIMARY['work'])])

    def test_destination_label_and_color_follow_real_window_location(self):
        with patch.object(display_switch,'saved_binding',return_value=(None,self.binding)):
            self.native.monitor_for_window.return_value=1
            self.assertEqual(display_switch.button_state(self.db,'run',self.native),dict(label='副屏',color='yellow'))
            self.native.monitor_for_window.return_value=2
            self.assertEqual(display_switch.button_state(self.db,'run',self.native),dict(label='主屏',color='green'))
            self.native.monitor_for_window.return_value=1
            self.assertEqual(display_switch.button_state(self.db,'run',self.native),dict(label='副屏',color='yellow'))

    def test_secondary_is_remembered_in_multi_monitor_setup(self):
        third={**SECONDARY,'handle':3,'device':'third'}
        self.native.monitors.return_value=[PRIMARY,SECONDARY,third]
        self.native.monitor_for_window.side_effect=[3,1,1,3]
        self.assertEqual(self.toggle()['display'],'主屏')
        # A manually selected secondary must be used on the next outward switch.
        self.assertEqual(self.toggle()['device'],'third')

    def test_single_monitor_starts_virtual_secondary(self):
        virtual={**SECONDARY,'handle':3,'device':'virtual','bounds':(1920,0,3840,1080),'work':(1920,0,3840,1080)}
        self.native.monitors.return_value=[PRIMARY]
        self.native.monitors.side_effect=[[PRIMARY],[PRIMARY,virtual]]
        self.native.monitor_for_window.side_effect=[1,3]
        with patch.object(virtual_display,'physical_monitors',return_value=[PRIMARY]), \
                patch.object(virtual_display,'ensure',return_value=dict(state='started',device='virtual',monitor=virtual)) as ensure:
            result=self.toggle()
        ensure.assert_called_once()
        self.assertEqual(result['display'],'副屏')
        self.assertEqual(result['device'],'virtual')
        self.assertEqual(self.native.move.call_args.args,(123,virtual['work']))

    def test_stale_window_pid_is_rejected(self):
        self.native.window_pid.return_value=99
        with self.assertRaisesRegex(ValueError,'已改变'):
            self.toggle()
        self.native.move.assert_not_called()

    def test_move_must_be_verified(self):
        self.native.monitor_for_window.side_effect=[1,1]
        with self.assertRaisesRegex(ValueError,'尚未确认'):
            self.toggle()

    def test_binding_from_another_run_cannot_be_used(self):
        with self.assertRaisesRegex(ValueError,'尚未绑定'):
            display_switch.bound_window(self.db,'other')

    def test_binding_file_replaced_is_rejected_before_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'binding.json'
            path.write_text(json.dumps(dict(browser_target='codex_iab',hwnd=123,chat_title='sample',binding_id='first')))
            display_switch.remember_binding(self.db,'run',path)
            path.write_text(json.dumps(dict(binding_id='replacement')))
            with patch.object(display_switch.subprocess,'run') as probe:
                with self.assertRaisesRegex(ValueError,'绑定已改变'):
                    display_switch.bound_window(self.db,'run')
                probe.assert_not_called()

    def test_live_binding_probe_failure_is_not_bypassed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'binding.json'
            path.write_text(json.dumps(dict(browser_target='codex_iab',hwnd=123,chat_title='sample',binding_id='first')))
            display_switch.remember_binding(self.db,'run',path)
            with patch.object(display_switch.subprocess,'run',return_value=Mock(returncode=1,stderr=b'codex_iab_chat_changed')):
                with self.assertRaisesRegex(ValueError,'无法核验'):
                    display_switch.bound_window(self.db,'run')

    def test_capture_does_not_require_foreground_but_physical_input_does(self):
        for command in (['pwsh','resume_capture.ps1'],['pwsh','capture-card.ps1'],['pwsh','guarded-uia-action.ps1','-Action','Invoke']):
            self.assertIsNone(foreground_activity.requirement(command))
            with patch.object(foreground_activity,'require_input_foreground') as focus:
                with foreground_activity.track(self.db,'run',command):pass
                focus.assert_not_called()
        self.assertIsNotNone(foreground_activity.requirement(['pwsh','guarded-uia-action.ps1','-Action','Key']))

    def test_overlay_keeps_primary_coordinates_when_secondary_is_left(self):
        status,buttons=Mock(),Mock()
        status.winfo_width.return_value=710
        buttons.winfo_width.return_value=400
        self.native.api.GetWindowRect.return_value=True
        with patch.object(progress_window,'_top_level_handle',side_effect=[11,22,11,22]):
            progress_window.pin_overlay_to_primary(status,buttons,self.native)
        calls=self.native.api.SetWindowPos.call_args_list
        self.assertEqual([call.args[2:4] for call in calls],[(405,6),(1115,6)])
        for call in calls:
            self.assertTrue(call.args[-1] & progress_window.SWP_NOACTIVATE)

    def test_four_buttons_fit_panel_at_different_scales(self):
        for scale in (1,1.25,1.5,2):
            geometry=progress_window.button_geometry(scale)
            self.assertEqual(len(geometry['widths']),4)
            right=geometry['x']+sum(geometry['widths'])+geometry['gap']*3
            self.assertLessEqual(right,round(progress_window.BUTTON_WIDTH/scale))
            self.assertLessEqual(geometry['y']+geometry['height'],round(progress_window.PANEL_HEIGHT/scale))

    def test_detached_launch_keeps_implicit_startup_windows_hidden(self):
        with patch.object(launch_progress.subprocess,'Popen') as start:
            launch_progress.launch_process(['pythonw.exe','overlay.py'])
        options=start.call_args.kwargs
        self.assertTrue(options['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW)
        self.assertEqual(options['startupinfo'].wShowWindow,0)
        self.assertTrue(options['creationflags'] & subprocess.CREATE_BREAKAWAY_FROM_JOB)

    def test_legacy_maximize_probe_never_changes_the_window(self):
        with patch.object(progress_window,'find_codex_window',return_value=123), \
                patch.object(progress_window.ctypes.windll.user32,'IsZoomed',return_value=False), \
                patch.object(progress_window.ctypes.windll.user32,'ShowWindowAsync') as show:
            self.assertEqual(progress_window.ensure_codex_maximized(),(True,False))
        show.assert_not_called()

    def test_windows_overlay_factory_does_not_initialize_tk(self):
        with patch.object(progress_window,'NativeRoot',return_value=Mock()) as native, \
                patch.object(progress_window.tk,'Tk',side_effect=AssertionError('Tk startup must not run')):
            self.assertIs(progress_window.create_overlay_root(),native.return_value)


@unittest.skipUnless(os.name=='nt','Windows native visibility checks')
class NativeVisibilityTests(unittest.TestCase):
    def test_windows_compiles_visibility_guard_and_rejects_missing_window(self):
        source=Path(__file__).with_name('capture-visibility.ps1')
        script=". '"+str(source).replace("'","''")+"'; [BossCaptureVisibility]::Check([IntPtr]::Zero,0,0,100,100)"
        command=powershell_host.command(source)
        command=command[:command.index('-File')]+['-Command',script]
        result=subprocess.run(command,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode('utf-8',errors='replace'))
        self.assertIn('capture_window_not_visible',result.stdout.decode('utf-8-sig'))


if __name__=='__main__':unittest.main()
