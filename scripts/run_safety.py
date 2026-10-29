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
    return ledger.run_row(db,run_id)


def fenced(fn):
    # Kept as an API-compatible decorator; removed per-action state/generation fences.
    return fn


def quantity_reason(db,run_id):
    import ledger
    run=ledger.run_row(db,run_id)
    if db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'",(run_id,)).fetchone()[0] >= run['target']:
        return 'run_target_reached'
    if db.execute('SELECT COUNT(*) FROM candidate_progress WHERE run_id=?',(run_id,)).fetchone()[0] >= run['max_views']:
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
    import recruiting_rules
    run=ledger.run_row(db,run_id)
    if index not in (2,3): raise ValueError('first_message_uses_reserve')
    if recruiting_rules.run_greeting_mode(run)=='single': raise ValueError('single_greeting_disallows_followups')
    digest=ledger.run_candidate_hash(db,run_id,candidate_id)
    token=uuid.uuid4().hex; stamp=ledger.iso(ledger.now())
    db.execute('INSERT INTO message_attempts VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(run_id,candidate_hash,message_index) DO UPDATE SET token=excluded.token,status=excluded.status,updated_at=excluded.updated_at',(token,run_id,digest,index,'pending',run['generation'],stamp,stamp))
    return {'state':'ready','token':token,'generation':run['generation']}


def resolve_message(db,token,result,manual=False):
    import ledger
    if result not in ('sent','not-sent','unknown'): raise ValueError('message_result_invalid')
    row=db.execute('SELECT * FROM message_attempts WHERE token=?',(token,)).fetchone()
    if not row: raise ValueError('message_record_not_found')
    stamp=ledger.iso(ledger.now())
    db.execute('UPDATE message_attempts SET status=?,updated_at=? WHERE token=?',(result,stamp,token))
    if row['message_index']==1:
        db.execute('UPDATE candidates SET status=?,sent_at=?,updated_at=? WHERE token=?',(result,stamp if result=='sent' else None,stamp,token))
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
            result={'state':'ready'}
        elif a.command=='message-begin': result=begin_message(db,a.run,a.candidate_id,a.message_index)
        else:
            result=resolve_message(db,a.token,a.result,a.command=='message-reconcile')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
