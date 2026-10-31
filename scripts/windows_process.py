"""Keep background console helpers invisible, including under pythonw.exe."""
import os
import subprocess


def hidden_options():
    if os.name != 'nt':
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return dict(creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startup)
