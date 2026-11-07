"""Local project vault. A failed or skipped unlock leaves user projects usable."""
import argparse,base64,copy,hashlib,json,os,re,shutil,sys,tempfile,uuid,zlib
from pathlib import Path,PurePosixPath
import vault_crypto as crypto
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[1]
_cache={}
MAX_BYTES=16*1024*1024
UPGRADE_LABEL=b'recruiting-installed-before-1.3.0/v1'

try:sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError,OSError):pass


def upgrade_key(value,old_root,new_root):
    """One-time 1.3.0 compatibility grant for an existing older installation."""
    import skill_update
    old_root=Path(old_root);new_root=Path(new_root)
    if not (old_root/'SKILL.md').is_file():return None
    try:
        old=skill_update.version_key(skill_update.installed_version(old_root))
        new=skill_update.version_key(skill_update.installed_version(new_root))
    except ValueError:return None
    if not ((0,0,0)<old<(1,3,0) and new==(1,3,0)):return None
    grant=value.get('upgrade_130')
    if not grant:return None
    return crypto.unwrap(crypto.legacy_key(UPGRADE_LABEL,crypto.raw(grant['salt'])),grant,value['key_id'].encode())


def resolve_key(value,root=None,password=None,allow_legacy=False,extra=(),upgrade_from=None):
    saved=read_trust().get(value['key_id'])
    if saved:
        try:
            key=crypto.raw(saved);decode(value,key)
            return key,'trusted'
        except (ValueError,InvalidTag):pass
    if upgrade_from is not None:
        key=upgrade_key(value,upgrade_from,root)
        if key is not None:
            decode(value,key)
            return key,'upgrade_130'
    if allow_legacy:
        for material in legacy_materials(root,extra):
            for item in value.get('legacy',[]):
                try:
                    key=crypto.unwrap(crypto.legacy_key(material,crypto.raw(item['salt'])),item,value['key_id'].encode())
                    decode(value,key)
                    return key,'legacy'
                except (ValueError,InvalidTag):pass
    if password is not None:
        item=value['password']
        try:
            key=crypto.unwrap(crypto.password_key(password,crypto.raw(item['salt'])),item,value['key_id'].encode())
            decode(value,key)
            return key,'password'
        except (ValueError,InvalidTag):return None,'incorrect_password'
    return None,'password_required'

def state_dir():
    return Path(os.environ.get('BOSS_STATE_DIR',str(Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'Codex/recruiting-greetings')))
def vault_path(root=None):return (Path(root) if root else ROOT)/'references/project-vault.json'
def trust_path():return state_dir()/'trust'/'projects.dpapi'
def public_key(root=None):
    from publisher_pin import PUBLIC_KEY_B64
    actual=json.loads(((Path(root) if root else ROOT)/'references/publisher-key.json').read_text(encoding='utf-8'))['public_key']
    if actual!=PUBLIC_KEY_B64:raise ValueError('publisher_key_changed')
    return crypto.raw(PUBLIC_KEY_B64)
def envelope(root=None):
    path=vault_path(root)
    if path.stat().st_size>MAX_BYTES:raise ValueError('vault_too_large')
    value=json.loads(path.read_text(encoding='utf-8'))
    signature=value.pop('signature')
    crypto.verify(value,signature,public_key(root))
    if value.get('schema')!='recruiting-project-vault/v1' or not re.fullmatch('[0-9a-f]{32}',value['key_id']):raise ValueError('invalid_vault_schema')
    return value

def read_trust():
    try:return json.loads(crypto.unprotect(trust_path().read_bytes()).decode('utf-8'))
    except (OSError,ValueError,RuntimeError):return {}
def save_trust(key_id,key):
    value=read_trust();value[key_id]=crypto.b64(key)
    crypto.atomic(trust_path(),crypto.protect(crypto.canonical(value)))
def decode(value,key):
    cipher=crypto.raw(value['ciphertext']);nonce=crypto.raw(value['nonce'])
    if len(nonce)!=12 or len(cipher)>MAX_BYTES:raise ValueError('invalid_vault_size')
    packed=AESGCM(key).decrypt(nonce,cipher,value['key_id'].encode())
    decoder=zlib.decompressobj();plain=decoder.decompress(packed,MAX_BYTES+1)
    if len(plain)>MAX_BYTES or decoder.unconsumed_tail or not decoder.eof:raise ValueError('invalid_vault_plaintext_size')
    data=json.loads(plain.decode('utf-8'))
    if data.get('schema')!='recruiting-private-projects/v1':raise ValueError('invalid_private_schema')
    return data
def load(root=None):
    path=vault_path(root)
    if not path.is_file():return None
    trust=trust_path()
    stamp=(str(path.resolve()),path.stat().st_mtime_ns,path.stat().st_size,str(trust),trust.stat().st_mtime_ns if trust.exists() else None)
    if stamp in _cache:return copy.deepcopy(_cache[stamp])
    value=envelope(root);key=read_trust().get(value['key_id'])
    if not key:return None
    data=decode(value,crypto.raw(key));_cache.clear();_cache[stamp]=data
    return copy.deepcopy(data)
def normalize(value):
    try:data=load()
    except Exception:data=None
    aliases=data.get('aliases',{}) if data else {}
    def visit(item,parent=None):
        if isinstance(item,dict):return {aliases.get(k,k):visit(v,k) for k,v in item.items()}
        if isinstance(item,list):return [visit(v,'list_item') for v in item]
        if isinstance(item,str):return aliases.get(item,item) if parent in (None,'policy','trigger_policy') else item
        return item
    return visit(value)
def rule_config(fallback):
    try:data=load()
    except Exception:data=None
    if data:return normalize(data['rules'])
    value=json.loads(Path(fallback).read_text(encoding='utf-8-sig'))
    return value

def rule_value(rules,key,default=0):
    if key in rules:return rules[key]
    try:
        data=load()
        if data:return normalize(data.get('legacy_defaults',{})).get(key,default)
    except Exception:pass
    path=ROOT/'references/recruiting-rules.json'
    try:return json.loads(path.read_text(encoding='utf-8')).get('legacy_defaults',{}).get(key,default)
    except (OSError,ValueError):return default

def legacy_materials(root=None,extra=()):
    root=Path(root) if root else ROOT
    yielded=set()
    candidates=[Path(x) for x in extra]+[root/'SKILL.md']
    if (root/'profiles').is_dir():candidates+=list((root/'profiles').rglob('*.md'))
    backups=state_dir()/'updates/backups'
    if backups.is_dir():candidates+=list(backups.glob('*/SKILL.md'))
    for path in candidates:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>2*1024*1024:continue
        value=path.read_bytes();digest=hashlib.sha256(value).digest()
        if digest not in yielded:yielded.add(digest);yield value

def safe_files(data):
    result={}
    for name,encoded in data.get('files',{}).items():
        path=PurePosixPath(name)
        if len(path.parts)<2 or path.parts[0]!='profiles' or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:raise ValueError('private_file_unsafe_path')
        if path.suffix not in ('.md','.json') or any(p.rstrip(' .')!=p or p in ('','.','..') for p in path.parts):raise ValueError('private_file_type')
        if any(re.fullmatch(r'(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',p) for p in path.parts):raise ValueError('private_reserved_path')
        content=crypto.raw(encoded)
        if len(content)>2*1024*1024:raise ValueError('private_file_too_large')
        result[name]=content
    return result

def preserve_user_projects(files,root,collision_error='private_project_user_collision'):
    """A full snapshot may seed user projects; upgrades keep their local edits."""
    root=Path(root).resolve();preserved=set()
    for name in files:
        path=root/name
        if not path.resolve().is_relative_to(root):raise ValueError('private_path_escape')
        for parent in (path,*path.parents):
            if parent==root.parent:break
            if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():raise ValueError('private_local_link')
        meta=path if path.name=='project.json' else path.parent/'project.json'
        if not meta.is_file():continue
        current=json.loads(meta.read_text(encoding='utf-8-sig'))
        if current.get('origin')!='user':continue
        incoming=files.get(meta.relative_to(root).as_posix())
        snapshot=json.loads(incoming.decode('utf-8-sig')) if incoming else {}
        if snapshot.get('origin')!='user' or not current.get('project_id') or current['project_id']!=snapshot.get('project_id'):
            raise ValueError(collision_error)
        preserved.add(meta.parent.relative_to(root).as_posix())
    return {name:content for name,content in files.items() if str(PurePosixPath(name).parent) not in preserved}


def apply(data,root=None,backup=None,ticket=None):
    root=Path(root) if root else ROOT;files=preserve_user_projects(safe_files(data),root)
    # Installed project snapshots remain at their original paths for historical runs.
    backup=Path(backup) if backup else state_dir()/'updates/vault-backups'/uuid.uuid4().hex
    backup.mkdir(parents=True,exist_ok=True)
    touched=[];old={}
    try:
        for name,content in files.items():
            path=root/name
            for parent in (path,*path.parents):
                if parent==root.parent:break
                if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():raise ValueError('private_local_link')
            # Never replace a self-created project with a bundled project.
            meta=path if path.name=='project.json' else path.parent/'project.json'
            if meta.is_file():
                current=json.loads(meta.read_text(encoding='utf-8-sig'))
                if current.get('origin')=='user':raise ValueError('private_project_user_collision')
            old[name]=path.read_bytes() if path.is_file() else None
            if old[name] is not None:crypto.atomic(backup/name,old[name])
        record=dict(root=str(root.resolve()),database=str((state_dir()/'ledger.sqlite3').resolve()),files={name:dict(existed=value is not None,sha256=hashlib.sha256(value).hexdigest() if value is not None else None) for name,value in old.items()},new_runtime=False,state='prepared')
        if ticket:record.update(had_guard=ticket['had_guard'],previous=ticket['previous'])
        crypto.atomic(backup/'installation.json',crypto.canonical(record))
        crypto.atomic(backup/'restore.json',crypto.canonical({name:value is not None for name,value in old.items()}))
        for name,content in files.items():
            crypto.atomic(root/name,content);touched.append(name)
    except BaseException as exc:
        for name in reversed(touched):
            if old[name] is None:(root/name).unlink(missing_ok=True)
            else:crypto.atomic(root/name,old[name])
        exc.vault_restored=True
        raise
    crypto.atomic(state_dir()/'trust'/'applied.json',crypto.canonical(dict(root=str(root.resolve()),vault_sha256=hashlib.sha256(vault_path(root).read_bytes()).hexdigest())))
    return len(files)

def unlock(root=None,password=None,allow_legacy=False,extra=(),apply_files=True,upgrade_from=None):
    root=Path(root) if root else ROOT
    if not vault_path(root).is_file():return dict(state='development_source')
    value=envelope(root)
    key,source=resolve_key(value,root,password,allow_legacy,extra,upgrade_from)
    if key is None:
        return dict(state='locked',reason=source,hint='你是谁？',message='密码错误，项目未解密。' if source=='incorrect_password' else '请选择创新招聘组项目（已加密）并输入密码。')
    data=decode(value,key)
    if apply_files:
        import run_admission
        backup=state_dir()/'updates/vault-backups'/uuid.uuid4().hex
        with run_admission.maintenance(state_dir()/'ledger.sqlite3',backup/'admission.json') as ticket:
            try:
                crypto.atomic(backup/'installation.json',crypto.canonical(dict(root=str(root.resolve()),database=str((state_dir()/'ledger.sqlite3').resolve()),files={},had_guard=ticket['had_guard'],previous=ticket['previous'])))
                apply(data,root,backup,ticket)
                save_trust(value['key_id'],key)
            except BaseException as exc:
                if getattr(exc,'vault_restored',False):ticket['restored']=True
                elif (backup/'installation.json').is_file():
                    from install_engine import restore
                    restore(root,backup,json.loads((backup/'installation.json').read_text(encoding='utf-8')));ticket['restored']=True
                raise
    else:save_trust(value['key_id'],key)
    _cache.clear()
    return dict(state='unlocked',source=source,key_id=value['key_id'])


def migrate_installed_upgrade(root=None):
    """Older updaters activate the new code before it can interpret the grant."""
    root=Path(root) if root else ROOT
    if not vault_path(root).is_file() or load(root) is not None:return None
    import skill_update
    if skill_update.version_key(skill_update.installed_version(root))!=(1,3,0):return None
    records=[]
    for file in (state_dir()/'updates/backups').glob('*/installation.json'):
        try:
            record=json.loads(file.read_text(encoding='utf-8'))
            if Path(record['root']).resolve()==root.resolve():
                records.append((file.stat().st_mtime_ns,file,record))
        except (OSError,ValueError,KeyError):continue
    if not records:return None
    _,file,record=max(records,key=lambda item:(item[0],str(item[1])))
    info=record.get('files',{}).get('SKILL.md',{})
    # A newer fresh install or incomplete/rolled-back update cancels older receipts.
    if record.get('state')!='complete' or not info.get('existed'):return None
    previous=file.parent/'SKILL.md'
    if not previous.is_file() or hashlib.sha256(previous.read_bytes()).hexdigest()!=info.get('sha256'):return None
    if upgrade_key(envelope(root),file.parent,root) is None:return None
    return unlock(root,upgrade_from=file.parent)

def readable(profile):
    profile=Path(profile);meta=profile.parent/'project.json'
    try:metadata=json.loads(meta.read_text(encoding='utf-8-sig')) if meta.is_file() else {}
    except (OSError,ValueError):return False
    if metadata.get('origin')=='bundle' and vault_path().is_file():
        try:
            if load() is None:return False
        except Exception:return False
    return True

def selectable(profile):
    if not readable(profile):return False
    meta=Path(profile).parent/'project.json'
    try:metadata=json.loads(meta.read_text(encoding='utf-8-sig')) if meta.is_file() else {}
    except (OSError,ValueError):return False
    retired=rule_config(ROOT/'references/recruiting-rules.json').get('retired_project_ids',[])
    return metadata.get('active') is not False and not metadata.get('retired') and metadata.get('project_id') not in retired

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['status','unlock'])
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--prompt',action='store_true')
    parser.add_argument('--password-stdin',action='store_true');parser.add_argument('--legacy-file',type=Path,action='append',default=[])
    parser.add_argument('--password-prompt',action='store_true')
    args=parser.parse_args()
    try:
        migrate_installed_upgrade(args.root)
        result=dict(state='unlocked' if load(args.root) else 'locked') if args.command=='status' else unlock(args.root)
        if result['state']=='locked' and args.command=='unlock':
            password=None
            if args.password_stdin:password=sys.stdin.readline().rstrip('\r\n')
            elif args.password_prompt:
                import getpass
                password=getpass.getpass('项目数据解密（提示：你是谁？；留空跳过）：') or None
            elif args.prompt:
                import tkinter as tk
                from tkinter import simpledialog
                window=tk.Tk();window.withdraw()
                try:password=simpledialog.askstring('项目数据解密','需要解密项目数据。密码提示：你是谁？\n输入密码，或取消以跳过。',show='*',parent=window)
                finally:window.destroy()
            if password is not None:result=unlock(args.root,password,False)
            else:result=dict(state='locked',reason='skipped',hint='你是谁？')
        print(json.dumps(result,ensure_ascii=False))
    except Exception as exc:
        print(json.dumps(dict(state='error',reason=str(exc)),ensure_ascii=False));raise SystemExit(1)
if __name__=='__main__':main()
