"""Shared daily report rows, success coloring and target-based estimates."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import ledger
from report_paths import profile_identity,report_path

CN_TZ=timezone(timedelta(hours=8))
GREEN='E2F0D9'
_workbook_cache={}


def rows(db,profile,at):
    if isinstance(at,str): at=datetime.fromisoformat(at)
    start=at.astimezone(CN_TZ).replace(hour=0,minute=0,second=0,microsecond=0)
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone()
    if not exists: return []
    data=db.execute('''SELECT a.*,r.profile_path,COALESCE(c.status,a.send_status) AS actual_send_status FROM assessments a
        JOIN runs r ON r.run_id=a.run_id LEFT JOIN candidates c ON c.candidate_hash=a.candidate_hash AND c.run_id=a.run_id
        WHERE julianday(a.started_at)>=julianday(?) AND julianday(a.started_at)<julianday(?)
        ORDER BY a.started_at,a.candidate_name''',(start.isoformat(),(start+timedelta(days=1)).isoformat())).fetchall()
    import report_store
    report_store.backfill(db)
    identity=report_store.for_profile(db,profile)['job']
    return [row for row in data if (db.execute('SELECT job FROM run_identity WHERE run_id=?',(row['run_id'],)).fetchone() or [None])[0]==identity]


def confirmed_sent(row):
    return row['actual_send_status']=='sent'


def rejection_counts(data):
    """Separate full-resume rejection from list misses and colleague skips."""
    rejected=set();coworker_skipped=set()
    for row in data:
        r=dict(row);key=(r['run_id'],r['candidate_hash'])
        if r.get('decision')!='skip':continue
        eligibility=json.loads(r.get('eligibility_json') or '{}')
        observation=json.loads(r.get('coworker_progress') or '{}')
        if eligibility.get('trigger')=='coworker_skip' or observation.get('action')=='skip' or observation.get('skip') is True:
            coworker_skipped.add(key);continue
        facts=json.loads(r.get('evaluation_input') or '{}')
        if (r.get('evaluation_mode')=='card' or facts.get('evaluation_stage')=='list' or facts.get('worker_stage')=='list'
                or facts.get('read_complete') is False or eligibility.get('trigger') in ('list_prefilter','score_incomplete','coworker_unknown')):
            continue
        if r.get('electronic_enabled') or facts.get('electronic_resume_enabled') is True:
            rejected.add(key)
    return dict(resume_rejected=len(rejected),coworker_skipped=len(coworker_skipped))


def projected_counts(db,profile,at):
    data=rows(db,profile,at)
    import report_store
    metrics=report_store.daily_summary(db,profile,at,data)
    return dict(viewed=metrics['viewed'],sent=metrics['sent'],pending=sum(bool(not row['report_written'] or (row['actual_send_status'] and row['send_status']!=row['actual_send_status'])) for row in data))


def overlay_counts(db,profile,at,data=None):
    """Completed decisions and confirmed resume opens for this job/Shanghai day."""
    import report_store
    data=rows(db,profile,at) if data is None else data
    start=datetime.fromisoformat(report_store.day(at)).replace(tzinfo=CN_TZ)
    finish=start+timedelta(days=1)
    job=report_store.for_profile(db,profile)['job']
    checks=db.execute("SELECT 1 FROM sqlite_master WHERE name='candidate_checks'").fetchone()
    # Earlier runs recorded the resume colleague check after confirmed opening,
    # before dedicated open timestamps/receipts were added. That receipt proves
    # a view, not complete reading or qualification; card checks do not count.
    receipt=(" OR EXISTS (SELECT 1 FROM candidate_checks c WHERE c.run_id=p.run_id "
             "AND c.candidate_hash=p.candidate_hash AND c.kind IN ('resume_opened','resume'))") if checks else ''
    viewed=db.execute('''SELECT COUNT(*) FROM candidate_progress p
        JOIN run_identity i ON i.run_id=p.run_id
        WHERE i.job=? AND julianday(p.started_at)>=julianday(?) AND julianday(p.started_at)<julianday(?)
        AND (p.electronic_opened_at IS NOT NULL'''+receipt+')',
        (job,start.isoformat(),finish.isoformat())).fetchone()[0]
    return dict(judged=len({(r['run_id'],r['candidate_hash']) for r in data}),resume_viewed=viewed,
                sent=sum(confirmed_sent(r) for r in data))


def append_overlay_counts(wb,db,profile,at,data):
    counts=overlay_counts(db,profile,at,data)
    import report_store
    started=report_store.daily_summary(db,profile,at,data)['viewed']
    ws=wb.create_sheet('_悬浮窗统计');ws.sheet_state='hidden'
    ws.append(['已判断','已查看','已招呼','已进入筛选'])
    ws.append([counts['judged'],counts['resume_viewed'],counts['sent'],started])


def workbook_counts(path,include_overlay=False):
    from openpyxl import load_workbook
    path=Path(path).resolve()
    before=path.stat();key=(before.st_mtime_ns,before.st_size,before.st_ino)
    cached=_workbook_cache.get(str(path))
    if cached and cached[0]==key:
        return dict(cached[1]) if include_overlay else {k:cached[1][k] for k in ('viewed','sent')}
    wb=load_workbook(path,read_only=False,data_only=True)
    try:
        ws=wb['候选人简报']; viewed=sent=0
        import re
        headline=re.search(r'共查看 (\d+) 人，打招呼了 (\d+) 人',str(ws['A1'].value or '')) or re.fullmatch(r'共查看 (\d+) 人，打招呼了 (\d+) 人',str(ws['A2'].value or ''))
        expanded=re.search(r'共判断 (\d+) 人.*?共查看 (\d+) 人.*?成功招呼 (\d+) 人',str(ws['A1'].value or ''))
        if expanded:
            # Preserve the old API's entered-candidate count separately from
            # the newly explicit confirmed-resume-view count.
            result=dict(viewed=int(expanded[1]),sent=int(expanded[3]))
        elif headline:
            result=dict(viewed=int(headline[1]),sent=int(headline[2]))
        else:
            for row in ws.iter_rows(min_row=2):
                if len(row)<2 or not row[1].value: continue
                viewed+=1
                if row[1].fill.fgColor.type=='rgb' and row[1].fill.fgColor.rgb[-6:].upper()==GREEN:
                    sent+=1
            result=dict(viewed=viewed,sent=sent)
        result.update(judged=int(expanded[1]) if expanded else None,resume_viewed=int(expanded[2]) if expanded else None)
        if '_悬浮窗统计' in wb.sheetnames:
            counters=list(wb['_悬浮窗统计'].values)
            if len(counters)>1:
                values=dict(zip(counters[0],counters[1]))
                result.update(judged=values['已判断'],resume_viewed=values['已查看'])
                if '已进入筛选' in values:result['viewed']=values['已进入筛选']
        after=path.stat()
        if key==(after.st_mtime_ns,after.st_size,after.st_ino):_workbook_cache[str(path)]=(key,result)
        return dict(result) if include_overlay else {k:result[k] for k in ('viewed','sent')}
    finally: wb.close()


def daily_counts(db,run,root,at=None):
    at=at or ledger.now()
    expected=projected_counts(db,run['profile_path'],at)
    import report_store
    path=report_store.destination(db,root,at.isoformat(),run['profile_path'])
    actual=dict(viewed=0,sent=0,judged=0,resume_viewed=0)
    error=None
    if path.is_file():
        try: actual=workbook_counts(path,include_overlay=True)
        except (OSError,ValueError,KeyError) as exc: error=str(exc)
    expected_overlay=overlay_counts(db,run['profile_path'],at)
    pending=bool(expected['pending'] or report_store.pending(db,at.isoformat(),run['profile_path']) or actual['viewed']!=expected['viewed'] or actual['sent']!=expected['sent'] or error or
                 actual['judged']!=expected_overlay['judged'] or actual['resume_viewed']!=expected_overlay['resume_viewed'])
    return dict(daily_viewed=actual['viewed'],daily_judged=actual['judged'],daily_resume_viewed=actual['resume_viewed'],
                daily_sent=actual['sent'],report_pending=pending,report_path=str(path))


def estimate(run,viewed,sent,average_seconds,elapsed):
    candidates=[]
    if average_seconds and viewed>0:
        candidates.append((max(0,run['max_views']-viewed)*average_seconds,'查看目标'))
    if sent>0 and elapsed>0:
        candidates.append((max(0,run['target']-sent)*elapsed/sent,'招呼目标'))
    if not candidates: return None,'估算中'
    seconds,basis=min(candidates)
    import math
    return math.ceil(seconds/60),basis
