"""Shared local recruiting folders, including Windows redirected desktops."""
import os
from pathlib import Path


def desktop_dir():
    if os.environ.get('BOSS_DESKTOP_DIR'):
        return Path(os.environ['BOSS_DESKTOP_DIR']).expanduser()
    if os.name == 'nt':
        import winreg
        try:
            key = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                return Path(os.path.expandvars(winreg.QueryValueEx(handle, 'Desktop')[0]))
        except OSError:
            pass
    return Path.home() / 'Desktop'


def configs_dir():
    return desktop_dir() / '自动招呼' / '02 招呼配置'


def records_dir(root=None):
    root = Path(root) if root is not None else desktop_dir()
    if root.name == '01 招呼记录' and root.parent.name == '自动招呼':
        return root
    return root / '自动招呼' / '01 招呼记录'


def metadata_path(profile):
    profile = Path(profile)
    sidecar = profile.with_name('.' + profile.stem + '.project.json')
    if sidecar.is_file() or profile.resolve().is_relative_to(configs_dir().resolve()):
        return sidecar
    return profile.parent / 'project.json'


def relocate_report(path, root):
    path, root = Path(path), Path(root)
    try:
        relative = path.resolve().relative_to((root / '自动投递记录').resolve())
    except ValueError:
        return path
    return records_dir(root) / relative
