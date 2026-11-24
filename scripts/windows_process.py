"""Keep background console helpers invisible, including under pythonw.exe."""
import os
import subprocess


def decode_output(value):
    """Decode after binary pipe collection; never fail a subprocess reader thread."""
    if value is None:return ''
    if isinstance(value,str):return value
    if value.startswith((b'\xff\xfe',b'\xfe\xff')):
        return value.decode('utf-16',errors='replace')
    for encoding in ('utf-8-sig','gb18030'):
        try:return value.decode(encoding)
        except UnicodeDecodeError:pass
    return value.decode('utf-8-sig',errors='replace')


def hidden_options():
    if os.name != 'nt':
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return dict(creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startup)
