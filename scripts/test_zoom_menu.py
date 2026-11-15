"""Exercise actual PowerShell menu cleanup with synthetic probes and no GUI input."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import page_layout
import powershell_host
from windows_process import hidden_options,decode_output


class ZoomMenuTests(unittest.TestCase):
    def run_probe(self,body):
        with tempfile.TemporaryDirectory(prefix='zoom-menu-test-') as tmp:
            script=Path(tmp)/'test.ps1'
            helper=Path(__file__).with_name('page-zoom-menu.ps1').as_posix().replace("'","''")
            script.write_text("$ErrorActionPreference='Stop'\n. '"+helper+"'\n"+body,encoding='utf-8')
            result=subprocess.run(powershell_host.command(script),capture_output=True,timeout=10,**hidden_options())
            self.assertEqual(result.returncode,0,decode_output(result.stderr))

    def test_menu_already_open_is_closed_and_verified(self):
        self.run_probe('''
$state=@{open=$true;visible=$true;calls=0}
Close-PageZoomMenu -DelayMs 0 -Probe {
 @{expanded=$state.open;menu_visible=$state.visible;collapse={ $state.calls++;$state.open=$false;$state.visible=$false }}
}
if($state.calls -ne 1 -or $state.visible){throw 'menu_was_not_closed'}
''')

    def test_closed_pattern_does_not_hide_still_visible_menu(self):
        self.run_probe('''
$state=@{visible=$true;calls=0}
Close-PageZoomMenu -DelayMs 0 -Probe {
 @{expanded=$false;menu_visible=$state.visible;collapse={ $state.calls++;if($state.calls -eq 2){$state.visible=$false} }}
}
if($state.calls -ne 2){throw 'visible_menu_was_ignored'}
''')

    def test_stale_pattern_is_resolved_again(self):
        self.run_probe('''
$state=@{visible=$true;calls=0;probes=0}
Close-PageZoomMenu -DelayMs 0 -Probe {
 $state.probes++
 @{expanded=$state.visible;menu_visible=$state.visible;collapse={ $state.calls++;if($state.calls -eq 1){throw 'element_not_available'};$state.visible=$false }}
}
if($state.calls -ne 2 -or $state.probes -lt 3){throw 'stale_pattern_not_refreshed'}
''')

    def test_failure_is_reported_instead_of_silently_ignored(self):
        self.run_probe('''
$failed=$false
try {
 Close-PageZoomMenu -Attempts 2 -DelayMs 0 -Probe { @{expanded=$true;menu_visible=$true;collapse={}} }
}catch{$failed=$_.Exception.Message -like 'page_zoom_menu_not_closed*'}
if(!$failed){throw 'cleanup_failure_was_hidden'}
''')

    def test_binding_change_never_collapses_another_chat_menu(self):
        self.run_probe('''
$failed=$false
try {
 Close-PageZoomMenu -DelayMs 0 -Probe {throw 'zoom_binding_changed'}
}catch{$failed=$_.Exception.Message -eq 'zoom_binding_changed'}
if(!$failed){throw 'binding_change_was_ignored'}
''')

    def test_python_rejects_zoom_success_when_menu_is_still_open(self):
        response=subprocess.CompletedProcess([],0,stdout=json.dumps(dict(state='read',percent=90,menu_closed=False)).encode())
        with patch('page_layout.subprocess.run',return_value=response):
            with self.assertRaisesRegex(page_layout.LayoutBlocked,'缩放菜单未能关闭'):
                page_layout.query('Set',90,'synthetic')


if __name__=='__main__':unittest.main()
