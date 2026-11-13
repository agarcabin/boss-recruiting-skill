"""Build, check and install GitHub Releases without replacing local recruiting data."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import uuid
from windows_process import hidden_options
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'release-manifest.json'
SOURCE = 'update-source.json'
TOP_FILES = {'SKILL.md', 'CHANGELOG.md', 'README.md', SOURCE}
MANAGED_DIRS = {'scripts', 'references', 'agents', 'docs'}
SUFFIXES = {'.py', '.ps1', '.md', '.json', '.yaml', '.yml', '.txt'}
LIMIT = 32 * 1024 * 1024


def version_key(value: str) -> tuple[int, int, int]:
    value = value.removeprefix('v')
    if re.fullmatch(r'\d+\.\d+\.\d+', value):
        return tuple(map(int, value.split('.')))
    if re.fullmatch(r'\d+\.\d{2}', value):
        major, fraction = value.split('.')
        return int(major), int(fraction[0]), int(fraction[1])
    raise ValueError('invalid_release_version')


def installed_version(root: Path) -> str:
    text = (root / 'SKILL.md').read_text(encoding='utf-8-sig')
    match = re.search(r'(?m)^  version: ["\']?([0-9.]+)["\']?\s*$', text)
    if not match:
        raise ValueError('skill_version_missing')
    version_key(match[1])
    return match[1]


def source(root: Path) -> dict:
    config = json.loads((root / SOURCE).read_text(encoding='utf-8-sig'))
    if config.get('schema') != 'boss-skill-update/v1' or not re.fullmatch(
            r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', config.get('repository', '')):
        raise ValueError('github_update_source_missing')
    return config


def managed_name(name: str) -> bool:
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or name != path.as_posix():
        return False
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in path.parts):
        return False
    if any(re.fullmatch(r'(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p) for p in path.parts):
        return False
    if len(path.parts) > 1 and path.parts[0] == 'profiles':
        return False
    return name in TOP_FILES or (len(path.parts) > 1 and path.parts[0] in MANAGED_DIRS
                                and path.suffix in SUFFIXES and '__pycache__' not in path.parts)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(root,output,legacy_dir=None,public_root=None,include_user_projects=False):
    import release_builder
    public_root=public_root or Path(output)/('source-'+uuid.uuid4().hex[:8])
    return release_builder.build(root,output,public_root,legacy_dir,include_user_projects)



def verify_archive(data,signature,root=None):
    import project_vault
    from vault_crypto import raw
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if isinstance(signature,bytes):signature=json.loads(signature.decode('utf-8'))
    if signature.get('algorithm')!='Ed25519':raise ValueError('release_signature_algorithm')
    from cryptography.exceptions import InvalidSignature
    try:Ed25519PublicKey.from_public_bytes(project_vault.public_key(root)).verify(raw(signature['signature']),data)
    except InvalidSignature as exc:raise ValueError('release_signature_invalid') from exc

def fetch(url: str, limit: int = LIMIT) -> bytes:
    import update_transport
    if not update_transport.allowed_url(url):
        raise ValueError('unexpected_download_host')
    req = Request(url, headers={'User-Agent': 'boss-recruiting-skill-updater',
                               'Accept': 'application/vnd.github+json'})
    with urlopen(req, timeout=12) as response:
        if not update_transport.allowed_url(response.geturl()):
            raise ValueError('unexpected_download_host')
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('release_download_too_large')
    return data


def github_cli(args: list[str]) -> bytes:
    executable = shutil.which('gh')
    if not executable:
        raise ValueError('github_cli_required_run_gh_auth_login')
    env = os.environ.copy()
    command = [executable, *args]
    result = subprocess.run(command, capture_output=True, timeout=60, env=env, **hidden_options())
    # An expired environment token can shadow a valid OS-keyring login.
    if result.returncode and any(env.get(k) for k in ('GH_TOKEN', 'GITHUB_TOKEN')):
        error = result.stderr.decode('utf-8', errors='replace').lower()
        if any(word in error for word in ('401', 'bad credentials', 'invalid', 'authentication')):
            for key in ('GH_TOKEN', 'GITHUB_TOKEN'):
                env.pop(key, None)
            result = subprocess.run(command, capture_output=True, timeout=60, env=env, **hidden_options())
    if result.returncode:
        raise ValueError('github_cli_error: ' + result.stderr.decode('utf-8', errors='replace')[-1600:])
    return result.stdout


def check(root: Path) -> dict:
    config = source(root)
    local = installed_version(root)
    if not config.get('private'):
        import update_transport
        return update_transport.check(root,config,local)
    try:
        if config.get('private'):
            release = json.loads(github_cli(['api', f"repos/{config['repository']}/releases/latest"]))
        else:
            release = json.loads(fetch(f"https://api.github.com/repos/{config['repository']}/releases/latest", 2*1024*1024))
    except HTTPError as exc:
        if exc.code == 404:
            return dict(state='no_release', current_version=local, repository=config['repository'])
        raise
    except ValueError as exc:
        if str(exc).startswith('github_cli_error:') and 'HTTP 404' in str(exc):
            return dict(state='no_release', current_version=local, repository=config['repository'])
        raise
    return release_result(config,local,release)


def release_result(config, local, release):
    if not isinstance(release,dict):
        raise ValueError('invalid_release_response')
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('stable_release_required')
    version = release['tag_name'].removeprefix('v')
    newer = version_key(version) > version_key(local)
    result = dict(state='update_available' if newer else 'up_to_date', current_version=local,
                  latest_version=version, release_tag=release['tag_name'],
                  repository=config['repository'], release_url=release['html_url'])
    if newer:
        names = [f'boss-recruiting-{version}.zip', f'boss-recruiting-{version}.zip.sha256',f'boss-recruiting-{version}.zip.sig']
        assets = {a['name']: a for a in release.get('assets', [])}
        urls = []
        for name in names:
            asset = assets.get(name)
            if not asset or asset.get('size', 0) > LIMIT:
                raise ValueError('release_asset_missing_or_too_large')
            url = asset['browser_download_url']
            expected = f"https://github.com/{config['repository']}/releases/download/{quote(release['tag_name'], safe='')}/{name}"
            if url != expected:
                raise ValueError('release_asset_source_mismatch')
            urls.append(url)
        result.update(archive_url=urls[0], checksum_url=urls[1],signature_url=urls[2])
    return result


def download(root: Path, release: dict) -> tuple[bytes, str]:
    if source(root).get('private'):
        with tempfile.TemporaryDirectory(prefix='boss-release-download-') as folder:
            name = f"boss-recruiting-{release['latest_version']}.zip"
            github_cli(['release', 'download', release['release_tag'], '--repo', release['repository'],
                        '--dir', folder, '--pattern', name, '--pattern', name + '.sha256','--pattern',name+'.sig'])
            archive, checksum = Path(folder) / name, Path(folder) / (name + '.sha256')
            if archive.stat().st_size > LIMIT or checksum.stat().st_size > 4096:
                raise ValueError('release_download_too_large')
            verify_archive(archive.read_bytes(),(Path(folder)/(name+'.sig')).read_bytes(),root)
            return archive.read_bytes(), checksum.read_text(encoding='ascii')
    import update_transport
    return update_transport.download(root,release)


def unpack(data: bytes, expected_version: str, repository: str) -> dict[str, bytes]:
    if len(data) > LIMIT:
        raise ValueError('release_download_too_large')
    with ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        if len(entries) > 500 or sum(i.file_size for i in entries) > LIMIT:
            raise ValueError('release_expanded_too_large')
        files = {}
        seen = set()
        for entry in entries:
            name = entry.filename
            if name.casefold() in seen or entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                raise ValueError('release_duplicate_or_symlink')
            if name != MANIFEST and not managed_name(name):
                raise ValueError('release_unsafe_path')
            seen.add(name.casefold())
            files[name] = z.read(entry)
    if MANIFEST not in files:
        raise ValueError('release_manifest_missing')
    manifest = json.loads(files[MANIFEST].decode('utf-8'))
    if (manifest.get('schema') != 'boss-skill-release/v1' or manifest.get('version') != expected_version
            or manifest.get('repository') != repository):
        raise ValueError('release_manifest_identity_mismatch')
    hashes = manifest.get('files')
    if not isinstance(hashes, dict) or set(hashes) != set(files) - {MANIFEST}:
        raise ValueError('release_manifest_file_mismatch')
    if any(digest(files[name]) != value for name, value in hashes.items()):
        raise ValueError('release_file_checksum_mismatch')
    if not {'SKILL.md', SOURCE, 'scripts/skill_update.py'} <= set(files):
        raise ValueError('release_required_files_missing')
    config = json.loads(files[SOURCE].decode('utf-8'))
    if config.get('repository') != repository or config.get('schema') != 'boss-skill-update/v1':
        raise ValueError('release_update_source_changed')
    match = re.search(rb'(?m)^  version: ["\']?([0-9.]+)["\']?\s*$', files['SKILL.md'])
    if not match or match[1].decode() != expected_version:
        raise ValueError('release_skill_version_mismatch')
    return files


def assert_idle(database):
    import run_admission
    if not Path(database).is_file():return
    with sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True) as db:
        run_admission.assert_idle(db)



def state_dir() -> Path:
    return Path(os.environ['BOSS_STATE_DIR']) if os.environ.get('BOSS_STATE_DIR') else Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local' / 'share'))) / 'Codex' / 'recruiting-greetings'


@contextlib.contextmanager
def update_lock(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / 'install.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        lock.unlink()


def install(root,files,backups,database=None,runtime_source=None):
    import install_engine
    return install_engine.install(root,files,backups,database,runtime_source)



def update(root: Path, backups: Path | None = None, database: Path | None = None) -> dict:
    result = check(root)
    if result['state'] != 'update_available':
        return result
    with update_lock((backups or state_dir() / 'updates' / 'backups').parent):
        assert_idle(database or state_dir() / 'ledger.sqlite3')
        data, checksum_text = download(root, result)
        checksum = checksum_text.strip().split()
        if not checksum or not re.fullmatch(r'[a-fA-F0-9]{64}', checksum[0]) or digest(data) != checksum[0].lower():
            raise ValueError('release_archive_checksum_mismatch')
        files = unpack(data, result['latest_version'], result['repository'])
        assert_idle(database or state_dir() / 'ledger.sqlite3')
        if installed_version(root) != result['current_version']:
            raise ValueError('local_version_changed_during_update')
        backup = install(root, files, backups or state_dir() / 'updates' / 'backups',database=database)
    return dict(state='updated', previous_version=result['current_version'], version=installed_version(root),
                backup=str(backup), release_url=result['release_url'], reload_skill=True,
                update_route=result.get('update_route'),download_route=result.get('download_route'),
                route_failures=result.get('route_failures',[]),download_route_failures=result.get('download_route_failures',[]))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('check', 'update', 'build','install-local','recover'))
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--output', type=Path)
    p.add_argument('--public-root',type=Path);p.add_argument('--legacy-dir',type=Path)
    p.add_argument('--include-user-projects',action='store_true',help='Explicitly include self-created projects in the encrypted snapshot.')
    p.add_argument('--archive',type=Path);p.add_argument('--signature',type=Path);p.add_argument('--runtime-source',type=Path);p.add_argument('--backup',type=Path)
    args = p.parse_args()
    try:
        if args.action == 'build':
            if not args.output:
                p.error('build requires --output')
            result = build(args.root,args.output,args.legacy_dir,args.public_root,args.include_user_projects)
        elif args.action=='install-local':
            if not args.archive or not args.signature:raise ValueError('archive_and_signature_required')
            data=args.archive.read_bytes();verify_archive(data,args.signature.read_bytes(),ROOT)
            files=unpack(data,installed_version(ROOT),source(ROOT)['repository'])
            with update_lock(state_dir()/'updates'):
                backup=install(args.root,files,state_dir()/'updates/backups',runtime_source=args.runtime_source)
            result=dict(state='installed',version=installed_version(args.root),backup=str(backup))
        elif args.action=='recover':
            import install_engine
            if not args.backup:raise ValueError('backup_required')
            result=install_engine.recover(args.root,args.backup)
        else:
            result = check(args.root) if args.action == 'check' else update(args.root)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps(dict(state='error', error=str(exc)), ensure_ascii=False))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
