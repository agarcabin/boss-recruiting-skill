"""Conservatively archive recognized old workbooks after complete record coverage."""
import workspace_paths
import argparse,hashlib,json,os,sqlite3,uuid
from zipfile import BadZipFile
from pathlib import Path
from openpyxl import load_workbook
import ledger,report_store,local_mutex,hit_summary,project_vault
from vault_crypto import atomic,canonical

def records(path):
    wb=load_workbook(path,read_only=True,data_only=False)
    try:
        if '详细信息' not in wb:raise ValueError('legacy_details_missing')
        rows=iter(wb['详细信息'].iter_rows(values_only=True));headers=next(rows)
        result={}
        for values in rows:
            if not any(v is not None for v in values):continue
            row=dict(zip(headers,values))
            key=tuple(row.get(k) for k in ('运行编号','候选人标识哈希','开始时间'))
            if not all(key) or key in result:raise ValueError('legacy_identity_ambiguous')
            result[key]=row
        run_ids=set()
        if '运行结果' in wb:
            sheet=wb['运行结果']
            if sheet.cell(1,1).value=='运行编号':run_ids={r[0] for r in sheet.iter_rows(min_row=2,values_only=True) if r[0]}
        return result,run_ids
    finally:wb.close()

def migrate(db,root,apply=False):
    report_store.backfill(db)
    canonical_rows={};canonical_runs=set();canonical_paths=set();candidates=set()
    for row in db.execute('SELECT path,pending FROM report_destinations'):
        path=Path(row['path']);canonical_paths.add(report_store.normalized(path))
        if row['pending'] or not path.is_file():continue
        try:
            rows,runs=records(path);canonical_rows.update(rows);canonical_runs.update(runs)
        except (OSError,ValueError,BadZipFile):continue
    for row in db.execute('SELECT started_at,report_path FROM runs'):
        if row['report_path']:
            path=Path(row['report_path'])
            if path.is_file():candidates.add(path)
        stamp=ledger.parse_time(row['started_at']).astimezone(report_store.ZONE)
        for folder in (Path(root)/'自动投递记录'/stamp.date().isoformat(),Path(root)/'自动投递记录'/f'{stamp.month}月{stamp.day}日'):
            if folder.is_dir() and not folder.is_symlink() and not getattr(folder,'is_junction',lambda:False)():candidates.update(folder.glob('*-投递记录*.xlsx'))
    outcomes=[]
    for path in sorted(candidates):
        key=report_store.normalized(path)
        if key in canonical_paths:continue
        entry=dict(path=str(path),state='kept')
        try:
            with local_mutex.locked('report-target:'+key):
                before=path.read_bytes();digest=hashlib.sha256(before).hexdigest()
                rows,runs=records(path)
                if not rows and not runs:raise ValueError('empty_legacy_not_confirmed')
                if not runs.issubset(canonical_runs):raise ValueError('legacy_run_not_covered')
                for identity,row in rows.items():
                    target=canonical_rows.get(identity)
                    if target is None:raise ValueError('legacy_record_not_covered')
                    for header,value in row.items():
                        if header in ('列表依据','电子简历依据'):value=hit_summary.display(value or '')
                        expected=target.get(header)
                        if ('' if value is None else value)!=('' if expected is None else expected):raise ValueError('legacy_content_differs')
                entry.update(state='covered',records=len(rows),sha256=digest)
                if apply:
                    backup=project_vault.state_dir()/'updates/report-archive'/(uuid.uuid4().hex+'-'+path.name+'.bak')
                    atomic(backup,before)
                    if hashlib.sha256(backup.read_bytes()).hexdigest()!=digest or path.read_bytes()!=before:raise ValueError('legacy_changed_during_archive')
                    atomic(backup.with_suffix('.json'),canonical(dict(original=str(path),sha256=digest)))
                    # Only this individually verified file is removed; no recursive cleanup.
                    path.unlink();entry.update(state='archived',backup=str(backup))
        except (OSError,ValueError,KeyError,BadZipFile) as exc:entry['reason']=str(exc)
        outcomes.append(entry)
    return outcomes

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB);p.add_argument('--root',type=Path,default=workspace_paths.desktop_dir());p.add_argument('--apply',action='store_true');a=p.parse_args()
    with ledger.connect(a.db) as db:result=migrate(db,a.root,a.apply)
    print(json.dumps(dict(state='complete',items=result),ensure_ascii=False))
if __name__=='__main__':main()
