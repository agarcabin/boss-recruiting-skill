import codecs
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import powershell_host


class PowerShellHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'unicode.ps1'
        self.path.write_text("Write-Output '中文'", encoding='utf-8')
        p = patch('powershell_host.Path.home', return_value=Path(self.temp.name))
        p.start(); self.addCleanup(p.stop)

    def test_prefers_pwsh_and_preserves_argument_boundaries(self):
        with patch('powershell_host.shutil.which', return_value='pwsh'):
            command = powershell_host.command(self.path, '-Name', 'two words')
        self.assertEqual(command[0], 'pwsh')
        self.assertEqual(command[-2:], ['-Name', 'two words'])

    def test_unsafe_ps5_encoding_is_rejected_before_launch(self):
        with patch('powershell_host.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'pwsh_required_for_utf8'):
                powershell_host.command(self.path)

    def test_ps5_can_read_bom_script(self):
        self.path.write_bytes(codecs.BOM_UTF8 + self.path.read_bytes())
        with patch('powershell_host.shutil.which', side_effect=lambda name: 'powershell.exe' if name == 'powershell.exe' else None):
            self.assertEqual(powershell_host.command(self.path)[0], 'powershell.exe')


if __name__ == '__main__':
    unittest.main()
