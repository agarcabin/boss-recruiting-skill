"""Atomic CSV exports and a once-configured, independently refreshing viewer."""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid
import zipfile
import local_mutex
import report_store
import powershell_host
from windows_process import hidden_options


def enabled(db, profile, stamp):
    job=report_store.for_profile(db,profile)['job']
    for row in db.execute('SELECT r.rule_snapshot,r.started_at FROM runs r JOIN run_identity i ON r.run_id=i.run_id WHERE i.job=?',(job,)):
        if report_store.day(row['started_at'])==report_store.day(stamp) and json.loads(row['rule_snapshot'] or '{}').get('csv_reports'):
            return True
    return False


def schema(db):
    report_store.schema(db)
    db.execute('''CREATE TABLE IF NOT EXISTS report_sync(
        day TEXT,job TEXT,data_dir TEXT,viewer_path TEXT,data_pending INTEGER DEFAULT 1,
        viewer_pending INTEGER DEFAULT 1,batch TEXT,data_error TEXT,viewer_error TEXT,
        PRIMARY KEY(day,job))''')
    db.execute('CREATE TABLE IF NOT EXISTS report_path_aliases(path_key TEXT PRIMARY KEY,day TEXT,job TEXT,path TEXT)')
    if 'attempted_at' not in {r[1] for r in db.execute('PRAGMA table_info(report_sync)')}:
        db.execute('ALTER TABLE report_sync ADD COLUMN attempted_at REAL')


def atomic_csv(path, headers, rows):
    fd,temp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(headers);writer.writerows(rows)
            stream.flush();os.fsync(stream.fileno())
        for attempt in range(3):
            try:os.replace(temp,path);return
            except PermissionError:
                if attempt==2:raise
                time.sleep(.1*(attempt+1))
    finally:
        if os.path.exists(temp):os.unlink(temp)


def datasets(workbook, folder, batch, now):
    specs=[]
    # Keep the merged human-readable top summary independently refreshable.
    summary=workbook['候选人简报'].cell(1,1).value
    name='_刷新汇总'
    atomic_csv(folder/(name+'.csv'),['汇总文本','__批次','__源更新时间'],[[summary,batch,now]])
    specs.append(dict(sheet=name,file=str(folder/(name+'.csv')),row=1,hidden=True,columns=['汇总文本','__批次','__源更新时间'],types=['text']*3))
    for sheet in workbook:
        if sheet.title=='_report_owner':continue
        header_row=2 if sheet.title=='候选人简报' else 1
        cells=list(sheet.iter_rows(min_row=header_row))
        headers=[str(c.value or '字段'+str(i+1)) for i,c in enumerate(cells[0])]
        rows=[]
        numeric={i for i,h in enumerate(headers) if h in ('综合分','列表分','电子简历分','附件简历分','判断时长（秒）','本日查看','本日已核验招呼')}
        for row in cells[1:]:
            values=[]
            for i,c in enumerate(row):
                value=c.hyperlink.target if c.hyperlink else c.value
                if isinstance(value,(int,float)) and not isinstance(value,bool):numeric.add(i)
                values.append('' if value is None else value)
            rows.append(values+[batch,now])
        links={}
        if sheet.title=='候选人简报':
            for i,h in enumerate(headers):
                if h in ('查看简历','查看名片','原图'):
                    links[h]='__路径_'+h;headers[i]=links[h]
        headers+=['__批次','__源更新时间']
        if not rows:rows=[['']*(len(headers)-2)+[batch,now]]
        filename=folder/(sheet.title+'.csv')
        atomic_csv(filename,headers,rows)
        specs.append(dict(sheet=sheet.title,file=str(filename),row=header_row,
            hidden=sheet.sheet_state!='visible',columns=headers,
            types=['number' if i in numeric else 'text' for i in range(len(headers))],links=links))
    return specs


def setup_viewer(template, target, specs, configure=None):
    if configure:return configure(template,target,specs)
    config=template.with_suffix('.json')
    config.write_text(json.dumps(dict(template=str(template),target=str(target),tables=specs),ensure_ascii=False),encoding='utf-8')
    try:
        done=subprocess.run(powershell_host.command(Path(__file__).with_name('excel-csv-viewer.ps1'),'-Config',config),
            capture_output=True,text=True,encoding='utf-8-sig',errors='replace',timeout=90,**hidden_options())
        if done.returncode:raise ValueError('excel_viewer_setup_failed: '+done.stderr[-1200:])
        response=json.loads(done.stdout)
        if response.get('state')!='verified':raise ValueError('excel_viewer_not_verified')
        with zipfile.ZipFile(target) as z:
            if len([n for n in z.namelist() if n.startswith('xl/queryTables/queryTable') and n.endswith('.xml')]) < len(specs):
                raise ValueError('excel_viewer_connections_missing')
    finally:config.unlink(missing_ok=True)


def export(db,root,stamp,profile,configure=None):
    import candidate_log
    schema(db);identity=report_store.for_profile(db,profile);day=report_store.day(stamp);job=identity['job']
    with local_mutex.locked('report:'+report_store.db_path(db)+':'+job+':'+day):
        original=report_store.destination(db,root,stamp,profile)
        state=db.execute('SELECT * FROM report_sync WHERE day=? AND job=?',(day,job)).fetchone()
        if state is None:
            target=original.with_name(original.stem+'-v1.4.10.xlsx') if original.exists() else original
            folder=original.with_suffix('.data');folder.mkdir(parents=True,exist_ok=True)
            db.execute('INSERT INTO report_sync(day,job,data_dir,viewer_path) VALUES (?,?,?,?)',(day,job,str(folder),str(target)))
            state=db.execute('SELECT * FROM report_sync WHERE day=? AND job=?',(day,job)).fetchone()
        folder=Path(state['data_dir']);target=Path(state['viewer_path']);folder.mkdir(parents=True,exist_ok=True)
        if db.in_transaction:raise ValueError('report_requires_committed_candidate_data')
        snapshot=sqlite3.connect(':memory:');snapshot.row_factory=sqlite3.Row
        db.backup(snapshot)
        workbook=None
        try:
            workbook=candidate_log._render_workbook(snapshot,root,stamp,profile_path=profile,_destination=target,_return_workbook=True)
            batch=uuid.uuid4().hex;now=datetime.now(timezone.utc).isoformat()
            specs=datasets(workbook,folder,batch,now)
            db.execute('UPDATE report_sync SET data_pending=0,data_error=NULL,batch=? WHERE day=? AND job=?',(batch,day,job))
        except (OSError,ValueError) as exc:
            db.execute('UPDATE report_sync SET data_pending=1,data_error=? WHERE day=? AND job=?',(str(exc),day,job))
            db.execute('UPDATE report_destinations SET pending=1,error=? WHERE day=? AND job=?',(str(exc),day,job))
            raise
        finally:snapshot.close()
        try:
            if state['viewer_pending'] or not target.is_file():
                if configure is None and state['attempted_at'] and time.time()-state['attempted_at']<60:
                    raise ValueError('展示配置尚未完成，CSV继续更新；请检查Excel安装及查询权限，程序稍后重试。')
                db.execute('UPDATE report_sync SET attempted_at=? WHERE day=? AND job=?',(time.time(),day,job))
                if original.exists() and original!=target:
                    if not report_store.owned(original,(report_store.owner(db),day,job)):raise ValueError('old_report_owner_conflict')
                    backup=folder/'旧版备份'/original.name
                    backup.parent.mkdir(exist_ok=True)
                    if not backup.exists():shutil.copy2(original,backup)
                if target.exists() and not report_store.owned(target,(report_store.owner(db),day,job)):
                    raise ValueError('viewer_owner_conflict')
                fd,temp=tempfile.mkstemp(prefix='.viewer-',suffix='.xlsx',dir=folder);os.close(fd)
                try:
                    workbook.save(temp)
                    setup_viewer(Path(temp),target,specs,configure)
                finally:Path(temp).unlink(missing_ok=True)
                # Do not change canonical ownership until the viewer is verified.
                db.execute('SAVEPOINT viewer_migrate')
                try:
                    if original!=target:
                        db.execute('INSERT OR IGNORE INTO report_path_aliases VALUES (?,?,?,?)',(report_store.normalized(original),day,job,str(original)))
                    db.execute('UPDATE report_destinations SET path=?,path_key=? WHERE day=? AND job=?',(str(target),report_store.normalized(target),day,job))
                    db.execute('UPDATE report_sync SET viewer_pending=0,viewer_error=NULL WHERE day=? AND job=?',(day,job))
                    db.execute('RELEASE viewer_migrate')
                except Exception:
                    db.execute('ROLLBACK TO viewer_migrate');db.execute('RELEASE viewer_migrate');raise
            db.execute('UPDATE report_destinations SET pending=0,error=NULL WHERE day=? AND job=?',(day,job))
        except (OSError,ValueError,subprocess.SubprocessError,sqlite3.Error) as exc:
            db.execute('UPDATE report_sync SET viewer_pending=1,viewer_error=? WHERE day=? AND job=?',(str(exc),day,job))
            db.execute('UPDATE report_destinations SET pending=1,error=? WHERE day=? AND job=?',('CSV已更新；Excel展示表待配置：'+str(exc),day,job))
            raise ValueError('CSV已更新；Excel展示表待配置：'+str(exc)) from exc
        finally:
            if workbook is not None:workbook.close()
        return target
