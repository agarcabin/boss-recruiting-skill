"""Shared, persistent 10-person/300-second greeting windows for every job."""
from contextlib import contextmanager
from datetime import timedelta
import math
import json

LIMIT = 10
SECONDS = 300
KEY = 'greeting_rate/v1'


@contextmanager
def transaction(db):
    owns = not db.in_transaction
    if owns:
        db.execute('BEGIN IMMEDIATE')
    try:
        yield
        if owns:
            db.commit()
    except BaseException:
        if owns:
            db.rollback()
        raise


def status(db, at=None):
    import ledger
    at = at or ledger.now()
    row = db.execute('SELECT value FROM settings WHERE key=?', (KEY,)).fetchone()
    data = json.loads(row[0]) if row else {}
    start = ledger.parse_time(data['started_at']) if data else at
    # Expired windows start at the next greeting, with no accumulated quota.
    if not data or at >= start + timedelta(seconds=SECONDS):
        return dict(state='ready', used=0, remaining=LIMIT, retry_after_seconds=0, retry_at=None)
    used = data['used']
    end = start + timedelta(seconds=SECONDS)
    wait = max(0, math.ceil((end-at).total_seconds())) if used >= LIMIT else 0
    return dict(state='rate_limited' if wait else 'ready', used=used,
                remaining=max(0, LIMIT-used), retry_after_seconds=wait,
                retry_at=ledger.iso(end) if wait else None)


def claim(db, candidate_hash, at=None):
    """One slot per visit/window, including unknown attempts; no extra slot for retries."""
    import ledger
    at = at or ledger.now()
    with transaction(db):
        db.execute('''CREATE TABLE IF NOT EXISTS greeting_rate_slots (
            candidate_hash TEXT PRIMARY KEY, window_started_at TEXT NOT NULL)''')
        row = db.execute('SELECT value FROM settings WHERE key=?', (KEY,)).fetchone()
        data = json.loads(row[0]) if row else None
        if not data or at >= ledger.parse_time(data['started_at']) + timedelta(seconds=SECONDS):
            data = dict(started_at=ledger.iso(at), used=0)
            db.execute('DELETE FROM greeting_rate_slots')
        slot = db.execute('SELECT window_started_at FROM greeting_rate_slots WHERE candidate_hash=?',
                          (candidate_hash,)).fetchone()
        if slot and slot[0] == data['started_at']:
            return dict(state='ready', reused=True, retry_after_seconds=0)
        if data['used'] >= LIMIT:
            return status(db, at)
        data['used'] += 1
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (KEY, json.dumps(data)))
        db.execute('INSERT OR REPLACE INTO greeting_rate_slots VALUES (?,?)',
                   (candidate_hash, data['started_at']))
        return dict(state='ready', used=data['used'], remaining=LIMIT-data['used'], retry_after_seconds=0)
