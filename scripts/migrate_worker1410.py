"""Backed-up, exact-token migration. Apply only while recruiting is idle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import hr_job
import workspace_paths


def changed(text):
    pattern=r'(^### +2\.\s*减分词库[^\n]*\n)([\s\S]*?)(?=^#{1,3} |\Z)'
    def section(match):
        lines=[]
        for line in match[2].splitlines(keepends=True):
            if line.lstrip().startswith(('>','#','<!--')):
                lines.append(line);continue
            ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
            content=line[:-len(ending)] if ending else line
            tokens=re.split(r'([、，,；;])',content)
            keep=[i for i in range(0,len(tokens),2) if hr_job.words(tokens[i])!=['主管']]
            if len(keep)==(len(tokens)+1)//2:lines.append(line);continue
            values=[]
            for i in keep:
                if values:values.append(tokens[i-1] if i else '、')
                values.append(tokens[i])
            lines.append(''.join(values)+ending)
        return match[1]+''.join(lines)
    return re.sub(pattern,section,text,flags=re.M)


def migrate(root, apply=False, db=None):
    import local_mutex
    import run_admission
    if apply and db is None:raise ValueError('migration_requires_idle_database')
    outcome=[]
    lock=run_admission.key(db) if db is not None else 'worker-migration-preview'
    with local_mutex.locked(lock):
        if apply:run_admission.assert_idle(db)
        for folder in Path(root).iterdir():
            if not folder.is_dir() or folder.is_symlink() or getattr(folder,'is_junction',lambda:False)():continue
            for profile in folder.glob('*.md'):
                if profile.is_symlink():continue
                meta_path=workspace_paths.metadata_path(profile)
                try:meta=json.loads(meta_path.read_text(encoding='utf-8-sig'))
                except (OSError,ValueError):
                    outcome.append(dict(profile=str(profile),state='unclassified'));continue
                if meta.get('trigger_policy')!='worker' and meta.get('evaluation_mode')!='worker_resume' and (meta.get('rules') or {}).get('policy')!='worker':continue
                original=profile.read_bytes();text=original.decode('utf-8-sig')
                if not hr_job.is_hr(text):
                    outcome.append(dict(profile=str(profile),state='legacy_uses_updated_default'));continue
                replacement=changed(text)
                before=hr_job.parse(text);after=hr_job.parse(replacement)
                # Only the exact negative token may differ.
                for stage in ('list','resume'):
                    before[stage]['negative']=[w for w in before[stage]['negative'] if w!='主管']
                if before!=after:raise ValueError('worker_migration_changed_unrelated_rule')
                entry=dict(profile=str(profile),state='unchanged' if text==replacement else 'ready')
                if apply and text!=replacement:
                    digest=hashlib.sha256(original).hexdigest()[:16]
                    backup=profile.with_name('.'+profile.name+'.1410-'+digest+'.bak')
                    if not backup.exists():
                        with backup.open('xb') as stream:stream.write(original)
                    fd,temp=tempfile.mkstemp(prefix='.'+profile.name,dir=folder)
                    try:
                        data=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+replacement.encode('utf-8')
                        with os.fdopen(fd,'wb') as stream:stream.write(data)
                        if profile.read_bytes()!=original:raise ValueError('worker_profile_changed_during_migration')
                        os.replace(temp,profile)
                    finally:
                        if os.path.exists(temp):os.unlink(temp)
                    entry.update(state='migrated',backup=str(backup))
                outcome.append(entry)
    return outcome


if __name__=='__main__':
    import ledger
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=workspace_paths.configs_dir())
    p.add_argument('--apply',action='store_true');p.add_argument('--db',type=Path)
    a=p.parse_args()
    if a.apply and not a.db:p.error('--apply requires --db')
    if a.db:
        with ledger.connect(a.db) as db:result=migrate(a.root,a.apply,db)
    else:result=migrate(a.root)
    print(json.dumps(result,ensure_ascii=False))
