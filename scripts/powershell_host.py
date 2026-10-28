"""Choose a Unicode-safe PowerShell host without rewriting scripts or launching UI."""
import codecs
import shutil
from pathlib import Path


def command(script, *args):
    script = Path(script).resolve(strict=True)
    if script.suffix.casefold() != '.ps1':
        raise ValueError('powershell_script_required')
    host = shutil.which('pwsh')
    if not host:
        bundled = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
        if bundled.is_file():
            host = str(bundled)
    if not host:
        data = script.read_bytes()
        if not data.startswith(codecs.BOM_UTF8) and not data.isascii():
            raise ValueError('pwsh_required_for_utf8_script: install/use PowerShell 7; no UI action dispatched')
        host = shutil.which('powershell.exe')
    if not host:
        raise ValueError('powershell_host_missing')
    return [host, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-File', str(script), *map(str, args)]
