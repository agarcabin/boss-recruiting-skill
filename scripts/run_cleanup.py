"""Stop earlier runs before a new start; keep report failures recoverable."""
import json
import os
from pathlib import Path

import ledger
import run_safety


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS overlay_owner (run_id TEXT PRIMARY KEY,pid INTEGER NOT NULL,birth REAL NOT NULL)')


def alive(pid, birth):
    try:
        return abs(run_safety.process_birth(pid) - birth) < .0001
    except (OSError, ProcessLookupError):
        return False


def close_process(pid, birth):
    if pid == os.getpid():
        return
    if alive(pid, birth):
        run_safety.process_birth(pid, terminate=True, expected=birth)
        if alive(pid, birth):
            raise ValueError('previous_recruiting_process_still_running')


def close_previous(db, keep_run=None, root=None):
    import stop_controller
    import workspace_paths
    ensure(db)
    ids = {r[0] for r in db.execute('SELECT run_id FROM runs WHERE stop_reason IS NULL OR finalized_at IS NULL')}
    ids.update(r[0] for r in db.execute('SELECT run_id FROM overlay_owner'))
    has_worker = db.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_owner'").fetchone()
    if has_worker:
        ids.update(r[0] for r in db.execute('SELECT run_id FROM workflow_owner'))
    results = []
    for run_id in sorted(ids):
        if run_id == keep_run:
            continue
        # Persist the stop before closing any window or worker. Never stop Codex.
        run_safety.request_stop(db, run_id, 'replaced_by_new_run')
        tables = ['overlay_owner'] + (['workflow_owner'] if has_worker else [])
        for table in tables:
            owner = db.execute(f'SELECT pid,birth FROM {table} WHERE run_id=?', (run_id,)).fetchone()
            if owner:
                close_process(owner['pid'], owner['birth'])
                db.execute(f'DELETE FROM {table} WHERE run_id=?', (run_id,))
        result = dict(run_id=run_id, stopped=True)
        if not ledger.run_row(db, run_id)['finalized_at']:
            try:
                report = stop_controller.finalize(db, run_id, root or workspace_paths.desktop_dir(), interrupt=False)
                if report is None:
                    raise ValueError('previous_report_finalization_pending')
                result['report'] = str(report)
            except Exception as exc:
                result['report_pending'] = str(exc)
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('startup_cleanup/'+run_id, json.dumps(result)))
        results.append(result)
    return results
