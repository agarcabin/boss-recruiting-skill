"""Updater acceptance tests using local packages and mocked GitHub responses."""
from datetime import datetime, timedelta, timezone
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from zipfile import ZipFile, ZIP_DEFLATED

import skill_update as updater


class SkillUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.local = self.base / 'local'
        self.remote = self.base / 'remote'
        self.repository = 'owner/recruiting'
        for root, version in ((self.local, '1.0.0'), (self.remote, '1.01')):
            (root / 'scripts').mkdir(parents=True)
            (root / 'SKILL.md').write_text(f'---\nmetadata:\n  version: "{version}"\n---\n', encoding='utf-8')
            (root / updater.SOURCE).write_text(json.dumps(dict(schema='boss-skill-update/v1', repository=self.repository)), encoding='utf-8')
            (root / 'scripts' / 'skill_update.py').write_text('release code ' + version, encoding='utf-8')
        result = updater.build(self.remote, self.base / 'packages')
        self.archive = Path(result['archive']).read_bytes()
        self.checksum = Path(result['checksum']).read_bytes()
        prefix = f'https://github.com/{self.repository}/releases/download/v1.01/'
        self.archive_url = prefix + 'boss-recruiting-1.01.zip'
        self.checksum_url = self.archive_url + '.sha256'
        self.release = dict(tag_name='v1.01', draft=False, prerelease=False,
            html_url=f'https://github.com/{self.repository}/releases/tag/v1.01', assets=[
                dict(name='boss-recruiting-1.01.zip', size=len(self.archive), browser_download_url=self.archive_url),
                dict(name='boss-recruiting-1.01.zip.sha256', size=len(self.checksum), browser_download_url=self.checksum_url)])
        self.db = self.base / 'ledger.sqlite3'

    def fetch(self, url, limit=updater.LIMIT):
        if url.endswith('/releases/latest'):
            return json.dumps(self.release).encode()
        return {self.archive_url: self.archive, self.checksum_url: self.checksum}[url]

    def test_version_comparison_supports_reset_and_decimal_increments(self):
        self.assertLess(updater.version_key('1.0.0'), updater.version_key('1.01'))
        self.assertLess(updater.version_key('1.09'), updater.version_key('1.10'))
        self.assertEqual(updater.version_key('v1.10'), updater.version_key('1.1.0'))
        for bad in ('../1.0.0', '1.0.0-beta', 'latest', '1.1'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                updater.version_key(bad)

    def test_package_excludes_profiles_runtime_credentials_and_generated_files(self):
        for name in ('profiles/private.md', 'runtime/python.exe', 'scripts/__pycache__/x.pyc', '.env'):
            path = self.remote / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('local-only', encoding='utf-8')
        result = updater.build(self.remote, self.base / 'other-packages')
        with ZipFile(result['archive']) as archive:
            self.assertTrue(all(updater.managed_name(n) or n == updater.MANIFEST for n in archive.namelist()))
            self.assertNotIn('profiles/private.md', archive.namelist())

    def test_available_same_older_and_no_release(self):
        with patch.object(updater, 'fetch', side_effect=self.fetch):
            self.assertEqual(updater.check(self.local)['state'], 'update_available')
            self.assertEqual(updater.check(self.remote)['state'], 'up_to_date')
            self.release['tag_name'] = 'v0.99'
            self.assertEqual(updater.check(self.local)['state'], 'up_to_date')
        with patch.object(updater, 'fetch', side_effect=HTTPError('https://api.github.com', 404, '', {}, None)):
            self.assertEqual(updater.check(self.local)['state'], 'no_release')

    def test_update_installs_new_code_preserves_local_data_and_backups_old_code(self):
        preserved = {}
        for name in ('profiles/approved.md', 'runtime/python.exe', '.git/config', 'local-notes.md'):
            path = self.local / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('local-only ' + name, encoding='utf-8')
            preserved[path] = path.read_bytes()
        with patch.object(updater, 'fetch', side_effect=self.fetch):
            result = updater.update(self.local, self.base / 'backups', self.db)
        self.assertEqual(result['state'], 'updated')
        self.assertEqual(updater.installed_version(self.local), '1.01')
        self.assertEqual(updater.installed_version(Path(result['backup'])), '1.0.0')
        for path, content in preserved.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse(self.db.exists())

    def test_bad_checksum_does_not_modify_installation(self):
        before = (self.local / 'SKILL.md').read_bytes()
        self.checksum = b'0' * 64
        with patch.object(updater, 'fetch', side_effect=self.fetch), self.assertRaisesRegex(ValueError, 'checksum'):
            updater.update(self.local, self.base / 'backups', self.db)
        self.assertEqual((self.local / 'SKILL.md').read_bytes(), before)

    def test_private_repository_check_and_download_use_github_cli(self):
        for root in (self.local, self.remote):
            (root / updater.SOURCE).write_text(json.dumps(dict(schema='boss-skill-update/v1',
                repository=self.repository,private=True)),encoding='utf-8')
        built=updater.build(self.remote,self.base/'private-packages')
        self.archive=Path(built['archive']).read_bytes()
        self.checksum=Path(built['checksum']).read_bytes()
        def cli(args):
            if args[0]=='api':
                return json.dumps(self.release).encode()
            self.assertEqual(args[:3],['release','download','v1.01'])
            folder=Path(args[args.index('--dir')+1])
            (folder/'boss-recruiting-1.01.zip').write_bytes(self.archive)
            (folder/'boss-recruiting-1.01.zip.sha256').write_bytes(self.checksum)
            return b''
        with patch.object(updater,'github_cli',side_effect=cli) as command, patch.object(updater,'fetch') as public:
            result=updater.update(self.local,self.base/'backups',self.db)
        self.assertEqual(result['state'],'updated')
        self.assertEqual(command.call_count,2)
        public.assert_not_called()

    def test_expired_environment_token_falls_back_to_keyring_without_exposing_token(self):
        failures=[subprocess.CompletedProcess([],1,b'',b'gh: Bad credentials (HTTP 401)'),
                  subprocess.CompletedProcess([],0,b'{"ok":true}',b'')]
        with patch.dict(updater.os.environ,{'GITHUB_TOKEN':'invalid-test-token'}), \
             patch.object(updater.shutil,'which',return_value='gh.exe'), \
             patch.object(updater.subprocess,'run',side_effect=failures) as run:
            self.assertEqual(updater.github_cli(['api','repos/owner/recruiting/releases/latest']),b'{"ok":true}')
            self.assertNotIn('GITHUB_TOKEN',run.call_args.kwargs['env'])

    def test_private_repository_without_release_is_reported_without_installation(self):
        (self.local/updater.SOURCE).write_text(json.dumps(dict(schema='boss-skill-update/v1',
            repository=self.repository,private=True)),encoding='utf-8')
        with patch.object(updater,'github_cli',side_effect=ValueError('github_cli_error: gh: Not Found (HTTP 404)')):
            self.assertEqual(updater.update(self.local,self.base/'backups',self.db)['state'],'no_release')

    def repack(self, extra=None, change=None):
        with ZipFile(io.BytesIO(self.archive)) as archive:
            files = {n: archive.read(n) for n in archive.namelist()}
        if extra:
            files.update(extra)
        if change:
            change(files)
        output = io.BytesIO()
        with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return output.getvalue()

    def test_unsafe_archive_paths_and_local_profile_overwrite_are_rejected(self):
        for name in ('../outside.py', '/outside.py', 'scripts/../../outside.py',
                     'scripts\\outside.py', 'profiles/approved.md', 'runtime/python.exe', 'scripts/CON'):
            with self.subTest(name=name):
                self.assertFalse(updater.managed_name(name))
                # ZipFile normalizes Windows backslashes on write; a normalized
                # added file must still fail the exact manifest file list check.
                with self.assertRaises(ValueError):
                    updater.unpack(self.repack({name: b'bad'}), '1.01', self.repository)

    def test_manifest_mismatch_and_tampered_file_are_rejected(self):
        tampered = self.repack(change=lambda files: files.update({'scripts/skill_update.py': b'tampered'}))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            updater.unpack(tampered, '1.01', self.repository)
        with self.assertRaisesRegex(ValueError, 'identity'):
            updater.unpack(self.archive, '1.02', self.repository)

    def test_foreign_asset_urls_and_missing_checksum_are_rejected(self):
        self.release['assets'][0]['browser_download_url'] = 'https://example.com/file.zip'
        with patch.object(updater, 'fetch', side_effect=self.fetch), self.assertRaisesRegex(ValueError, 'source_mismatch'):
            updater.check(self.local)
        self.release['assets'] = []
        with patch.object(updater, 'fetch', side_effect=self.fetch), self.assertRaisesRegex(ValueError, 'asset_missing'):
            updater.check(self.local)

    def test_live_or_paused_recruiting_run_blocks_installation_without_touching_db(self):
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            db.execute('CREATE TABLE runs(run_id TEXT,deadline_at TEXT)')
            db.execute('CREATE TABLE run_control(run_id TEXT,state TEXT)')
            db.execute('INSERT INTO runs VALUES (?,?)', ('live', (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()))
            db.execute('INSERT INTO run_control VALUES (?,?)', ('live', 'paused'))
            db.commit()
        before = self.db.read_bytes()
        with patch.object(updater, 'fetch', side_effect=self.fetch), self.assertRaisesRegex(ValueError, 'active_recruiting'):
            updater.update(self.local, self.base / 'backups', self.db)
        self.assertEqual(updater.installed_version(self.local), '1.0.0')
        self.assertEqual(self.db.read_bytes(), before)

    def test_partial_install_failure_restores_previously_replaced_files(self):
        files = updater.unpack(self.archive, '1.01', self.repository)
        before = {p.relative_to(self.local): p.read_bytes() for p in self.local.rglob('*') if p.is_file()}
        replace = updater.os.replace
        count = 0
        def fail_second(src, dst):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('simulated locked file')
            return replace(src, dst)
        with patch.object(updater.os, 'replace', side_effect=fail_second), self.assertRaisesRegex(OSError, 'locked'):
            updater.install(self.local, files, self.base / 'backups')
        after = {p.relative_to(self.local): p.read_bytes() for p in self.local.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
