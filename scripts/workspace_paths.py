"""Shared local recruiting folders, including Windows redirected desktops."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


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


def skill_root():
    """Return the currently executing skill directory."""
    return Path(__file__).resolve().parents[1]


def project_metadata_dir():
    """Private project metadata storage, outside the HR-facing desktop folder."""
    configured = os.environ.get('BOSS_PROJECT_METADATA_DIR')
    if configured:
        return Path(configured).expanduser()
    return skill_root() / 'runtime' / 'project-metadata'


def _is_live_profile(profile):
    profile = Path(profile)
    try:
        return profile.resolve().is_relative_to(configs_dir().resolve())
    except ValueError:
        return False


def legacy_metadata_path(profile):
    profile = Path(profile)
    return profile.with_name('.' + profile.stem + '.project.json')


def metadata_path(profile):
    profile = Path(profile)
    if _is_live_profile(profile):
        digest = hashlib.sha256(str(profile.resolve()).casefold().encode('utf-8')).hexdigest()
        return project_metadata_dir() / (digest + '.json')
    legacy = legacy_metadata_path(profile)
    if legacy.is_file():
        return legacy
    return profile.parent / 'project.json'


def migrate_metadata(profile):
    """Move one legacy desktop sidecar into the private skill metadata directory."""
    profile = Path(profile)
    target = metadata_path(profile)
    if not _is_live_profile(profile):
        return target
    legacy = legacy_metadata_path(profile)
    if legacy.is_file() and not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
        if target.read_bytes() != legacy.read_bytes():
            target.unlink(missing_ok=True)
            raise OSError('project_metadata_migration_verification_failed')
    if legacy.is_file():
        if target.is_file() and target.read_bytes() != legacy.read_bytes():
            conflict = target.with_name(target.stem + '.legacy-' + hashlib.sha256(legacy.read_bytes()).hexdigest()[:12] + '.json')
            shutil.copy2(legacy, conflict)
        legacy.unlink()
    return target


def migrate_desktop_metadata():
    """Move all recognized project sidecars out of the HR-facing configuration folder."""
    root = configs_dir()
    moved = []
    if not root.is_dir():
        return moved
    for legacy in root.rglob('*.project.json'):
        if not legacy.is_file() or not legacy.name.startswith('.'):
            continue
        stem = legacy.name[1:-len('.project.json')]
        profile = legacy.with_name(stem + '.md')
        if profile.is_file():
            target = migrate_metadata(profile)
        else:
            target = project_metadata_dir() / ('orphan-' + hashlib.sha256(str(legacy.resolve()).encode('utf-8')).hexdigest() + '.json')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy, target)
            if target.read_bytes() != legacy.read_bytes():
                target.unlink(missing_ok=True)
                raise OSError('project_metadata_migration_verification_failed')
            legacy.unlink()
        moved.append(dict(source=str(legacy), target=str(target)))
    return moved


def ensure_desktop_layout():
    """Create the two HR-facing folders and a readable job template on first install."""
    root = desktop_dir() / '自动招呼'
    records = root / '01 招呼记录'
    configs = root / '02 招呼配置'
    records.mkdir(parents=True, exist_ok=True)
    configs.mkdir(parents=True, exist_ok=True)
    template = configs / '岗位填写模板.md'
    source = skill_root() / 'docs' / 'HR-JOB-TEMPLATE.md'
    if not template.exists() and source.is_file():
        shutil.copyfile(source, template)
    migrated = migrate_desktop_metadata()
    return dict(root=str(root), records=str(records), configs=str(configs),
                template=str(template), migrated_metadata=migrated)


def relocate_report(path, root):
    path, root = Path(path), Path(root)
    try:
        relative = path.resolve().relative_to((root / '自动投递记录').resolve())
    except ValueError:
        return path
    return records_dir(root) / relative


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('ensure-layout',))
    args = parser.parse_args()
    if args.command == 'ensure-layout':
        print(json.dumps(ensure_desktop_layout(), ensure_ascii=False))


if __name__ == '__main__':
    main()
