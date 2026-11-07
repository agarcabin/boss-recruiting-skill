"""Recoverable filesystem installation coordinated with database run admission."""
import contextlib,json,os,shutil,sqlite3,tempfile,uuid
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
import project_vault,run_admission,report_store
from vault_crypto import atomic,canonical

def filesystem_path(path):
    value=str(Path(path).resolve())
    if os.name=='nt' and not value.startswith('\\\\?\\'):
        return '\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value
    return value

def target(root,name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:raise ValueError('install_unsafe_path')
    dest=root/name
    if not dest.resolve().is_relative_to(root):raise ValueError('install_path_escape')
    for parent in (dest,*dest.parents):
        if parent==root.parent:break
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():raise ValueError('install_local_link')
    return dest

def restore(root,backup,record):
    import hashlib
    for name,info in record['files'].items():
        path=target(root,name)
        if info['existed']:
            data=(backup/name).read_bytes()
            if hashlib.sha256(data).hexdigest()!=info['sha256']:raise ValueError('restore_backup_hash_mismatch')
            atomic(path,data)
        else:path.unlink(missing_ok=True)
    if record.get('trust_changed'):
        trust=project_vault.trust_path()
        if record.get('trust_existed'):
            data=(backup/'trust-before.dpapi').read_bytes()
            if hashlib.sha256(data).hexdigest()!=record['trust_sha256']:raise ValueError('restore_trust_hash_mismatch')
            atomic(trust,data)
        else:trust.unlink(missing_ok=True)
        project_vault._cache.clear()
    if record.get('new_runtime'):
        runtime=root/'runtime/win-x64/python'
        if not runtime.resolve().is_relative_to(root) or runtime.resolve()==root:raise ValueError('unsafe_runtime_restore')
        if runtime.exists():shutil.rmtree(filesystem_path(runtime))

def install(root,files,backups,database=None,runtime_source=None):
    import skill_update,hashlib
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    database=Path(database) if database else project_vault.state_dir()/'ledger.sqlite3'
    backup=Path(backups)/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]);backup.mkdir(parents=True)
    for name in files:
        if name!=skill_update.MANIFEST and not skill_update.managed_name(name):raise ValueError('release_unsafe_path')
        target(root,name)
    with tempfile.TemporaryDirectory(prefix='.verified-release-',dir=root.parent) as stage_dir:
        stage=Path(stage_dir)
        for name,data in files.items():atomic(stage/name,data)
        record=dict(root=str(root),database=str(database.resolve()),files={},new_runtime=False,state='prepared')
        atomic(backup/'installation.json',canonical(record))
        activated_build=json.loads(files[skill_update.MANIFEST])['version']
        with run_admission.maintenance(database,backup/'admission.json',build_id=activated_build) as ticket:
            record['had_guard']=ticket['had_guard'];record['previous']=ticket['previous']
            activation_started=False
            try:
                private={};key=None;value=None
                if project_vault.vault_path(stage).is_file():
                    value=project_vault.envelope(stage)
                    key,_=project_vault.resolve_key(value,stage,upgrade_from=root)
                    if key is not None:private=project_vault.safe_files(project_vault.decode(value,key))
                for name in private:
                    target(root,name)
                private=project_vault.preserve_user_projects(private,root,'user_project_collision_install_aborted')
                combined={**files,**private}
                atomic(backup/'installation.json',canonical(record))
                # Freeze original identities before any project file changes.
                with contextlib.closing(sqlite3.connect(database,isolation_level=None)) as db:
                    db.row_factory=sqlite3.Row;report_store.backfill(db)
                for name in combined:
                    path=target(root,name);existed=path.is_file()
                    info=dict(existed=existed,sha256=None)
                    if existed:
                        data=path.read_bytes();atomic(backup/name,data);info['sha256']=hashlib.sha256(data).hexdigest()
                    record['files'][name]=info
                atomic(backup/'restore.json',canonical({k:v['existed'] for k,v in record['files'].items()}))
                atomic(backup/'installation.json',canonical(record))
                activation_started=True
                for name in sorted(set(combined)-{'SKILL.md'})+['SKILL.md']:
                    if name in combined:atomic(target(root,name),combined[name])
                if runtime_source and not (root/'runtime/win-x64/python/python.exe').is_file():
                    source=Path(runtime_source).resolve()
                    if not (source/'python.exe').is_file():raise ValueError('runtime_source_missing')
                    record['new_runtime']=True;atomic(backup/'installation.json',canonical(record))
                    shutil.copytree(filesystem_path(source),filesystem_path(root/'runtime/win-x64/python'),dirs_exist_ok=False,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
                if key is not None:
                    trust=project_vault.trust_path()
                    record['trust_existed']=trust.is_file()
                    if trust.is_file():
                        data=trust.read_bytes();atomic(backup/'trust-before.dpapi',data)
                        record['trust_sha256']=hashlib.sha256(data).hexdigest()
                    record['trust_changed']=True
                    atomic(backup/'installation.json',canonical(record))
                    project_vault.save_trust(value['key_id'],key)
                    project_vault._cache.clear()
                record['state']='files_activated';atomic(backup/'installation.json',canonical(record))
            except BaseException:
                if activation_started:restore(root,backup,record)
                ticket['restored']=True
                record['state']='rolled_back';atomic(backup/'installation.json',canonical(record))
                raise
        record['state']='complete'
        try:atomic(backup/'installation.json',canonical(record))
        except OSError:pass
    return backup

def recover(root,backup):
    root=Path(root).resolve();backup=Path(backup).resolve()
    journal=backup/'admission.json'
    admission=json.loads(journal.read_text(encoding='utf-8'))
    record=json.loads((backup/'installation.json').read_text(encoding='utf-8')) if (backup/'installation.json').is_file() else dict(root=str(root),database=admission['database'],files={})
    for key in ('had_guard','previous'):
        if key not in record:record[key]=admission[key]
    if Path(record['root']).resolve()!=root:raise ValueError('restore_root_mismatch')
    database=Path(record['database'])
    import local_mutex
    with local_mutex.locked('install-admission:'+str(database.resolve()).casefold()):
        with contextlib.closing(sqlite3.connect(database,isolation_level=None)) as db:
            db.row_factory=sqlite3.Row
            has=db.execute("SELECT 1 FROM sqlite_master WHERE name='installation_admission'").fetchone()
            state=db.execute('SELECT * FROM installation_admission WHERE id=1').fetchone() if has else None
            if state and not state['maintenance']:
                return dict(state='already_active',version=state['build_id'])
            if not state:return dict(state='already_restored')
            if Path(state['journal']).resolve()!=journal.resolve():raise ValueError('restore_journal_mismatch')
            restore(root,backup,record)
            run_admission.restore_guard(db,record)
            atomic(backup/'installation.json',canonical({**record,'state':'recovered'}))
    return dict(state='recovered',backup=str(backup))
