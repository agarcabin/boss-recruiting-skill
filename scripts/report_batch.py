"""Coalesce in-process candidate updates into one export per day/job/root."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from report_paths import report_path,report_filename

_current=ContextVar('candidate_report_batch',default=None)


def active(db):
    session=_current.get()
    return session is not None and session['db'] is db


def request(db,root,stamp,filename,profile):
    session=_current.get()
    if session is None or session['db'] is not db: return None
    if profile is None: return None
    path=report_path(Path(root),stamp,profile)
    if filename: path=path.with_name(report_filename(profile,filename))
    session['pending'][str(path)]=(root,stamp,filename,profile)
    return path


def mark_written(db,run,digest):
    if not active(db):
        db.execute('UPDATE assessments SET report_written=1 WHERE run_id=? AND candidate_hash=?',(run,digest))


def flush_now(db):
    session=_current.get()
    if session is None or session['db'] is not db:return
    _flush(session)


def _flush(session):
    import candidate_log,daily_metrics
    pending=list(session['pending'].values());session['pending'].clear()
    token=_current.set(None)
    try:
        for root,stamp,filename,profile in pending:
            try:
                path=candidate_log.workbook(session['db'],root,stamp,filename=filename,profile_path=profile)
                for row in daily_metrics.rows(session['db'],profile,stamp):
                    mark_written(session['db'],row['run_id'],row['candidate_hash'])
                session['exports'].append(str(path))
            except (OSError,ValueError) as exc:
                session['warnings'].append('表格待补写：'+str(exc))
    finally:_current.reset(token)


@contextmanager
def batch(db):
    if active(db):
        yield _current.get()
        return
    session=dict(db=db,pending={},warnings=[],exports=[])
    token=_current.set(session)
    try:
        yield session
    finally:
        _current.reset(token)
        if session.get('flush',True):_flush(session)
