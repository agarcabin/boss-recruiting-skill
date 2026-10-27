"""Cross-process dispatch/stop exclusion, late-write fencing and message attempts."""
from __future__ import annotations
import argparse
import contextlib
import ctypes
import functools
import hashlib
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

def migrate(db):
    columns={r[1] for r in db.execute('PRAGMA table_info(runs)')}
    additions={'candidate_namespace':'TEXT','evaluation_mode':"TEXT NOT NULL DEFAULT 'resume'",
        'rule_snapshot':"TEXT NOT NULL DEFAULT '{}'",'generation':'INTEGER NOT NULL DEFAULT 0',
        'stop_reason':'TEXT','stop_binding':'TEXT','finalized_at':'TEXT','finalizer_owner':'TEXT',
        'finalizer_claimed_at':'TEXT','report_path':'TEXT','interrupt_status':'TEXT'}
    for name,kind in additions.items():
        if name not in columns: db.execute(f'ALTER TABLE runs ADD COLUMN {name} {kind}')
    db.executescript('''CREATE TABLE IF NOT EXISTS message_attempts (
        token TEXT PRIMARY KEY, run_id TEXT NOT NULL, candidate_hash TEXT NOT NULL,
        message_index INTEGER NOT NULL CHECK(message_index BETWEEN 1 AND 3),
        status TEXT NOT NULL, generation INTEGER NOT NULL, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, UNIQUE(run_id,candidate_hash,message_index));
        CREATE TABLE IF NOT EXISTS run_audit (id INTEGER PRIMARY KEY,run_id TEXT NOT NULL,
        at TEXT NOT NULL,event TEXT NOT NULL,detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS run_helpers (run_id TEXT NOT NULL,pid INTEGER NOT NULL,
        created_at REAL NOT NULL, PRIMARY KEY(run_id,pid));''')

def db_path(db):
    return str(Path(db.execute('PRAGMA database_list').fetchone()[2]).resolve())

@contextlib.contextmanager
def action_lock(db, timeout=5):
    """Same named mutex is held by the final physical action and stop writer."""
    name='Local\\CodexRecruiting_'+hashlib.sha256(db_path(db).casefold().encode()).hexdigest()[:24]
    if os.name=='nt':
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateMutexW.argtypes=(ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR)
        kernel.CreateMutexW.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
        kernel.ReleaseMutex.argtypes=(wintypes.HANDLE,)
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
        handle=kernel.CreateMutexW(None,False,name)
        if not handle: raise OSError(ctypes.get_last_error(),'CreateMutex')
        acquired=kernel.WaitForSingleObject(handle,int(timeout*1000)) in (0,0x80)
        try:
            if not acquired: raise TimeoutError('recruiting_action_lock_timeout')
            yield
        finally:
            if acquired: kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)
    else:
        import fcntl
        with open(db_path(db)+'.action.lock','a') as lock:
            until=time.monotonic()+timeout
            while True:
                try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); break
                except BlockingIOError:
                    if time.monotonic()>=until: raise TimeoutError('recruiting_action_lock_timeout')
                    time.sleep(.02)
            try: yield
            finally: fcntl.flock(lock,fcntl.LOCK_UN)

def ensure_writable(db,run_id,generation=None):
    import ledger
    run=ledger.run_row(db,run_id)
    if run['finalized_at'] or run['stop_reason'] or ledger.control_state(db,run_id)=='stopped':
        raise ValueError('run_stopped_or_finalized')
    if generation is not None and generation!=run['generation']: raise ValueError('stale_run_generation')
    return run

def fenced(fn):
    @functools.wraps(fn)
    def wrapped(db,args,*a,**kw):
        run_id=getattr(args,'run',None)
        if not run_id and getattr(args,'token',None):
            row=db.execute('SELECT run_id FROM candidates WHERE token=?',(args.token,)).fetchone()
            run_id=row[0] if row else None
        with action_lock(db):
            if run_id:
                try:
                    run=ensure_writable(db,run_id,getattr(args,'generation',None))
                    if run['evaluation_mode']=='card' and fn.__name__ in ('archive','archive_resume','missing','missing_resume'):
                        raise ValueError('resume_archive_not_applicable_for_card')
                except ValueError as exc:
                    import ledger
                    db.execute('INSERT INTO run_audit(run_id,at,event,detail) VALUES (?,?,?,?)',
                        (run_id,ledger.iso(ledger.now()),'blocked_write',json.dumps({'command':fn.__name__,'reason':str(exc)})))
                    raise
            return fn(db,args,*a,**kw)
    return wrapped

def quantity_reason(db,run_id):
    import ledger
    run=ledger.run_row(db,run_id)
    if db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'",(run_id,)).fetchone()[0]>=run['target']:
        return 'run_target_reached'
    if ledger.rolling_count(db,ledger.now())>=ledger.MAX_ROLLING_SENDS: return 'rolling_limit_reached'
    if db.execute('SELECT COUNT(*) FROM candidate_progress WHERE run_id=?',(run_id,)).fetchone()[0]>=ledger.MAX_RUN_VIEWS:
        return 'run_view_limit_reached'
    return None

def process_birth(pid,terminate=False,expected=None):
    """Creation-time checked helper termination, without an optional psutil runtime."""
    if pid==os.getpid() and terminate: raise ValueError('cannot_terminate_controller')
    if os.name!='nt':
        birth=float(Path(f'/proc/{pid}/stat').read_text().split()[21])
        if terminate and birth==expected:
            import signal
            os.kill(pid,signal.SIGTERM)
        return birth
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetProcessTimes.argtypes=(wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p)
    kernel.TerminateProcess.argtypes=(wintypes.HANDLE,wintypes.UINT)
    kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    handle=kernel.OpenProcess(0x1000|0x100000|(1 if terminate else 0),False,pid)
    if not handle: raise ProcessLookupError(pid)
    try:
        times=[ctypes.c_uint64() for _ in range(4)]
        if not kernel.GetProcessTimes(handle,*[ctypes.byref(x) for x in times]): raise OSError('GetProcessTimes')
        birth=times[0].value/10000000
        if terminate:
            if expected is None or abs(birth-expected)>.0001: raise ValueError('helper_pid_reused')
            if not kernel.TerminateProcess(handle,1): raise OSError('TerminateProcess')
            kernel.WaitForSingleObject(handle,100)
        return birth
    finally: kernel.CloseHandle(handle)

def begin_message(db,run_id,candidate_id,index):
    import ledger
    if index not in (2,3): raise ValueError('first_message_uses_reserve')
    with action_lock(db):
        run=ensure_writable(db,run_id)
        if ledger.now()>=ledger.parse_time(run['deadline_at']) or ledger.control_state(db,run_id)!='running':
            raise ValueError('run_not_running')
        if ledger.unresolved(db): raise ValueError('unresolved_prior_send')
        digest=ledger.run_candidate_hash(db,run_id,candidate_id)
        first=db.execute('SELECT status FROM candidates WHERE run_id=? AND candidate_hash=?',(run_id,digest)).fetchone()
        active=ledger.active_progress(db,run_id)
        if not first or first[0]!='sent' or not active or active['candidate_hash']!=digest: raise ValueError('first_message_not_confirmed_or_candidate_inactive')
        if index==3:
            previous=db.execute('SELECT status FROM message_attempts WHERE run_id=? AND candidate_hash=? AND message_index=2',(run_id,digest)).fetchone()
            if not previous or previous[0]!='sent': raise ValueError('second_message_not_confirmed')
        token=uuid.uuid4().hex; at=ledger.iso(ledger.now())
        db.execute('INSERT INTO message_attempts VALUES (?,?,?,?,?,?,?,?)',(token,run_id,digest,index,'pending',run['generation'],at,at))
        return {'state':'ready','token':token,'generation':run['generation']}

def resolve_message(db,token,result,manual=False):
    import ledger
    if result not in ('sent','not-sent','unknown'): raise ValueError('message_result_invalid')
    with action_lock(db):
        row=db.execute('SELECT * FROM message_attempts WHERE token=?',(token,)).fetchone()
        if not row or row['status'] not in ('pending','dispatching','unknown'): raise ValueError('message_not_pending')
        if row['message_index']==1 and not manual: raise ValueError('first_message_uses_ledger_resolve')
        if manual is not True:
            ensure_writable(db,row['run_id'],row['generation'])
            if row['status']=='unknown': raise ValueError('manual_reconciliation_required')
        at=ledger.iso(ledger.now())
        db.execute('UPDATE message_attempts SET status=?,updated_at=? WHERE token=?',(result,at,token))
        if row['message_index']==1:
            db.execute('UPDATE candidates SET status=?,sent_at=?,updated_at=? WHERE token=?',
                (result,at if result=='sent' else None,at,token))
            if result=='sent':
                from datetime import timedelta
                db.execute("INSERT INTO settings VALUES ('next_allowed_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(ledger.iso(ledger.now()+timedelta(seconds=80)),))
        if manual:
            db.execute('INSERT INTO run_audit(run_id,at,event,detail) VALUES (?,?,?,?)',(row['run_id'],at,'manual_reconcile',json.dumps({'token':token,'result':result})))
        return {'state':result,'message_index':row['message_index']}

def request_stop(db,run_id,reason):
    import ledger
    with action_lock(db):
        run=ledger.run_row(db,run_id)
        if not run['stop_reason']:
            db.execute('BEGIN IMMEDIATE')
            try:
                at=ledger.iso(ledger.now())
                db.execute('UPDATE runs SET stop_reason=?,generation=generation+1 WHERE run_id=?',(reason,run_id))
                db.execute("INSERT INTO run_control(run_id,state,updated_at) VALUES (?,'stopped',?) ON CONFLICT(run_id) DO UPDATE SET state='stopped',updated_at=excluded.updated_at",(run_id,at))
                db.commit()
            except Exception: db.rollback(); raise
        return ledger.run_row(db,run_id)

def main():
    import ledger
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('command',choices=('check','message-begin','message-resolve','message-reconcile'))
    p.add_argument('--run'); p.add_argument('--candidate-id');p.add_argument('--message-index',type=int);p.add_argument('--generation',type=int)
    p.add_argument('--token');p.add_argument('--result',choices=('sent','not-sent','unknown'));p.add_argument('--manual-confirmed',action='store_true')
    a=p.parse_args()
    with contextlib.closing(ledger.connect(a.db)) as db:
        if a.command=='check':
            state=ensure_writable(db,a.run,a.generation)
            if ledger.now()>=ledger.parse_time(state['deadline_at']) or ledger.control_state(db,a.run)!='running': raise ValueError('run_not_running')
            result={'state':'ready'}
        elif a.command=='message-begin': result=begin_message(db,a.run,a.candidate_id,a.message_index)
        else:
            if a.command=='message-reconcile' and not a.manual_confirmed: raise ValueError('manual_platform_confirmation_required')
            result=resolve_message(db,a.token,a.result,a.command=='message-reconcile')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
