"""Immutable local run identity and one owned destination per job/Shanghai day."""
import contextlib,hashlib,json,os,sqlite3,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
import local_mutex

ZONE=timezone(timedelta(hours=8))

def day(stamp):
    if isinstance(stamp,str):stamp=datetime.fromisoformat(stamp)
    return stamp.astimezone(ZONE).date().isoformat()

def db_path(db):
    return db.execute('PRAGMA database_list').fetchone()[2] or ':memory:'+str(id(db))

def schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS run_identity(run_id TEXT PRIMARY KEY,job TEXT NOT NULL,company TEXT NOT NULL,position TEXT NOT NULL,profile TEXT NOT NULL,mode TEXT NOT NULL,origin TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS report_destinations(day TEXT NOT NULL,job TEXT NOT NULL,path TEXT NOT NULL,path_key TEXT NOT NULL UNIQUE,pending INTEGER NOT NULL DEFAULT 1,error TEXT,PRIMARY KEY(day,job))')
    db.execute('CREATE TABLE IF NOT EXISTS report_local_state(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    db.execute("INSERT OR IGNORE INTO report_local_state VALUES ('owner',?)",(uuid.uuid4().hex,))

def owner(db):
    schema(db)
    return db.execute("SELECT value FROM report_local_state WHERE key='owner'").fetchone()[0]

def from_profile(profile,fields=None):
    import ledger
    path=Path(profile).resolve()
    fields=fields or ledger.profile_check(path)[2]
    if not fields.get('company') or not fields.get('position'):raise ValueError('report_identity_unavailable')
    try:meta=json.loads((path.parent/'project.json').read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):meta={}
    namespace=fields.get('candidate_namespace') or meta.get('candidate_namespace') or meta.get('project_id') or fields['company']+'\0'+fields['position']
    return dict(job=hashlib.sha256(namespace.encode()).hexdigest(),company=fields['company'],position=fields['position'],
                profile=str(path),mode=fields.get('evaluation_mode',meta.get('evaluation_mode','resume')),origin=meta.get('origin','user'))

def capture(db,run_id,profile,fields=None):
    schema(db)
    if db.execute('SELECT 1 FROM run_identity WHERE run_id=?',(run_id,)).fetchone():return
    data=from_profile(profile,fields)
    db.execute('INSERT OR IGNORE INTO run_identity VALUES (?,?,?,?,?,?,?)',(run_id,*(data[k] for k in ('job','company','position','profile','mode','origin'))))

def backfill(db):
    schema(db)
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='runs'").fetchone()
    if not exists:return
    for row in db.execute('SELECT run_id,profile_path FROM runs WHERE run_id NOT IN (SELECT run_id FROM run_identity)').fetchall():
        try:capture(db,row[0],row[1])
        except (OSError,ValueError):pass

def for_run(db,run_id):
    schema(db)
    row=db.execute('SELECT * FROM run_identity WHERE run_id=?',(run_id,)).fetchone()
    if row:return dict(row)
    run=db.execute('SELECT profile_path FROM runs WHERE run_id=?',(run_id,)).fetchone()
    if not run:raise ValueError('report_run_missing')
    capture(db,run_id,run[0])
    return dict(db.execute('SELECT * FROM run_identity WHERE run_id=?',(run_id,)).fetchone())

def for_profile(db,profile):
    schema(db)
    value=str(Path(profile).resolve())
    row=db.execute('SELECT * FROM run_identity WHERE profile=? COLLATE NOCASE LIMIT 1',(value,)).fetchone()
    if row:return dict(row)
    return from_profile(profile)

def normalized(path):
    path=Path(path).absolute()
    for parent in (path,*path.parents):
        if parent.is_symlink() or getattr(parent,'is_junction',lambda:False)():raise ValueError('report_link_path_forbidden')
    return os.path.normpath(str(path.resolve())).replace('\\','/').rstrip(' .').casefold()

def owned(path,expected,unknown_allowed=False):
    if not path.exists():return True
    from openpyxl import load_workbook
    try:
        wb=load_workbook(path,read_only=True,data_only=True)
        try:
            if '_report_owner' not in wb:return False
            values=[wb['_report_owner'].cell(1,i).value for i in range(1,4)]
            return values==list(expected)
        finally:wb.close()
    except OSError:
        if unknown_allowed:return False
        raise
    except (ValueError,KeyError):return False

def destination(db,root,stamp,profile):
    schema(db);identity=for_profile(db,profile);date=day(stamp);job=identity['job']
    row=db.execute('SELECT path FROM report_destinations WHERE day=? AND job=?',(date,job)).fetchone()
    if row:return Path(row[0])
    from report_paths import filename_component
    folder=Path(root).resolve()/'自动投递记录'/date
    prefix=filename_component(identity['company'])+'-'+filename_component(identity['position'])+'-投递记录-'
    own=owner(db)
    started=not db.in_transaction
    if started:db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT path FROM report_destinations WHERE day=? AND job=?',(date,job)).fetchone()
        if row:return Path(row[0])
        for suffix in (job[:10],job[:20],job,job+'-'+own):
            path=folder/(prefix+suffix+'.xlsx');key=normalized(path)
            if db.execute('SELECT 1 FROM report_destinations WHERE path_key=?',(key,)).fetchone():continue
            if not owned(path,(own,date,job),unknown_allowed=True):continue
            db.execute('INSERT INTO report_destinations(day,job,path,path_key) VALUES (?,?,?,?)',(date,job,str(path),key))
            return path
        raise ValueError('report_destination_collision')
    finally:
        if started:db.commit()

@contextlib.contextmanager
def export(db,root,stamp,profile):
    identity=for_profile(db,profile);date=day(stamp)
    with local_mutex.locked('report:'+db_path(db)+':'+identity['job']+':'+date):
        path=destination(db,root,stamp,profile)
        with local_mutex.locked('report-target:'+normalized(path)):
            try:
                if not owned(path,(owner(db),date,identity['job'])):raise ValueError('report_owner_conflict')
                yield path
                db.execute('UPDATE report_destinations SET pending=0,error=NULL WHERE day=? AND job=?',(date,identity['job']))
            except Exception as exc:
                db.execute('UPDATE report_destinations SET pending=1,error=? WHERE day=? AND job=?',(str(exc),date,identity['job']))
                raise

def add_owner(wb,db,stamp,profile):
    ws=wb.create_sheet('_report_owner');ws.sheet_state='veryHidden'
    ws.append([owner(db),day(stamp),for_profile(db,profile)['job']])

def append_results(wb,db,stamp,profile,rows):
    job=for_profile(db,profile)['job'];date=day(stamp)
    ids={r['run_id'] for r in rows}
    for row in db.execute('SELECT r.run_id,r.started_at FROM runs r JOIN run_identity i ON i.run_id=r.run_id WHERE i.job=?',(job,)):
        if day(row['started_at'])==date:ids.add(row['run_id'])
    for row in db.execute('SELECT p.run_id,p.started_at FROM candidate_progress p JOIN run_identity i ON i.run_id=p.run_id WHERE i.job=?',(job,)):
        if day(row['started_at'])==date:ids.add(row['run_id'])
    ws=wb.create_sheet('运行结果');ws.append(['运行编号','启动时间','状态','停止原因','本日查看','本日已核验招呼','Codex中断结果','未完成候选标识','未完成说明'])
    for rid in sorted(ids):
        row=db.execute('SELECT r.*,c.state FROM runs r LEFT JOIN run_control c ON c.run_id=r.run_id WHERE r.run_id=?',(rid,)).fetchone()
        values=[r for r in rows if r['run_id']==rid]
        progress=[dict(r) for r in db.execute('SELECT * FROM candidate_progress WHERE run_id=?',(rid,)) if day(r['started_at'])==date]
        unfinished=[r['candidate_hash'] for r in progress if not r['finished_at']]
        ws.append([rid,row['started_at'],row['state'],row['stop_reason'] if 'stop_reason' in row.keys() else '',len(progress),sum(r['actual_send_status']=='sent' for r in values),row['interrupt_status'] if 'interrupt_status' in row.keys() else '未核验','、'.join(unfinished),'interrupted；未完成，不伪造判定或离开时间' if unfinished else ''])
    for column in 'ABCDEFGHI':ws.column_dimensions[column].width=30

def pending(db,stamp,profile):
    row=db.execute('SELECT pending FROM report_destinations WHERE day=? AND job=?',(day(stamp),for_profile(db,profile)['job'])).fetchone()
    return bool(row and row[0])


def daily_summary(db, profile, stamp, rows, at=None):
    """One job/day, including opened cards that have no final assessment yet."""
    import ledger
    identity = for_profile(db, profile)
    date = day(stamp)
    start = datetime.fromisoformat(date).replace(tzinfo=ZONE)
    finish = start + timedelta(days=1)
    current = at or ledger.now()
    viewed = {(r['run_id'], r['candidate_hash']) for r in rows}
    for row in db.execute('''SELECT p.* FROM candidate_progress p
            JOIN run_identity i ON i.run_id=p.run_id WHERE i.job=?''', (identity['job'],)):
        if day(row['started_at']) == date:
            viewed.add((row['run_id'], row['candidate_hash']))
    elapsed = 0
    unavailable = False
    for row in db.execute('''SELECT r.run_id,r.started_at,c.state,c.updated_at,c.paused_at,c.paused_seconds
            FROM runs r JOIN run_identity i ON i.run_id=r.run_id
            LEFT JOIN run_control c ON c.run_id=r.run_id WHERE i.job=?''', (identity['job'],)):
        begun = datetime.fromisoformat(row['started_at'])
        end = datetime.fromisoformat(row['updated_at']) if row['state'] == 'stopped' else current
        left, right = max(start, begun), min(finish, end)
        if right <= left:
            continue
        paused = int(row['paused_seconds'] or 0)
        if row['state'] == 'paused':
            pause_start = datetime.fromisoformat(row['paused_at'] or row['updated_at'])
            paused += max(0, int((end - pause_start).total_seconds()))
        if paused and (begun < start or end > finish):
            # Old ledgers store only the cumulative pause length, not its day.
            unavailable = True
        else:
            elapsed += max(0, int((right-left).total_seconds())-paused)
    import daily_metrics
    counts=daily_metrics.overlay_counts(db,profile,stamp,rows)
    outcomes=daily_metrics.rejection_counts(rows)
    denominator=counts['resume_viewed']
    rate=(outcomes['coworker_skipped']/denominator
          if denominator and outcomes['coworker_skipped']<=denominator else None)
    return dict(viewed=len(viewed),**counts,**outcomes,coworker_skip_rate=rate,
                elapsed_seconds=None if unavailable else elapsed, **identity)


def add_summary_header(ws, db, profile, stamp, rows, at=None):
    import ledger, skill_update
    from openpyxl.styles import Alignment, Font, PatternFill
    current = at or ledger.now()
    metrics = daily_summary(db, profile, stamp, rows, current)
    seconds = metrics['elapsed_seconds']
    duration = (f'{seconds//3600} 小时 {seconds%3600//60} 分钟 {seconds%60} 秒'
                if seconds is not None else '暂无（跨日暂停记录不足）')
    speed = (f"{seconds/metrics['judged']:.2f} 秒/人"
             if seconds is not None and metrics['judged'] else '暂无')
    version = skill_update.installed_version(Path(__file__).resolve().parents[1])
    ws.insert_rows(1, 1)
    for cells in ws.iter_rows(min_row=2):
        for cell in cells:
            if cell.hyperlink:
                cell.hyperlink.ref = cell.coordinate
    rate=metrics['coworker_skip_rate']
    probability=f'{rate:.2%}' if rate is not None else '暂无'
    texts = [f"目标企业及岗位：{metrics['company']} {metrics['position']}",
             f"共判断 {metrics['judged']} 人",f"共查看 {metrics['resume_viewed']} 人",
             f"成功招呼 {metrics['sent']} 人",f"简历不合格 {metrics['resume_rejected']} 人",
             f"同事跳过 {metrics['coworker_skipped']} 人",f'同事跳过概率 {probability}',
             f'总用时 {duration}',f'平均速度 {speed}',
             f"skill版本：v{version}",f"更新时间：{current.astimezone(ZONE):%Y-%m-%d %H:%M:%S}"]
    ws.merge_cells(start_row=1,start_column=1,end_row=1,end_column=ws.max_column)
    cell=ws.cell(1,1,' ｜ '.join(texts))
    cell.alignment=Alignment(vertical='center',wrap_text=False,shrink_to_fit=True)
    cell.font=Font(name='微软雅黑',size=11,bold=True,color='FFFFFF')
    cell.fill=PatternFill('solid',fgColor='26496A')
    ws.row_dimensions[1].height=24
    ws.freeze_panes='C3'
    ws.auto_filter.ref=f'A2:{ws.cell(ws.max_row,ws.max_column).coordinate}'
    ws.print_title_rows='1:2'
    return metrics
