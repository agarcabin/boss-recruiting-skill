"""One durable random cooldown per visit, independent of shared greeting quota."""
import json,math,random
from datetime import timedelta
import ledger

def active_clock(db,run):
    row=db.execute('SELECT * FROM run_control WHERE run_id=?',(run,)).fetchone()
    value=(ledger.now()-ledger.parse_time(ledger.run_row(db,run)['started_at'])).total_seconds()
    if row:
        value-=row['paused_seconds'] or 0
        if row['state']=='paused':value-=max(0,(ledger.now()-ledger.parse_time(row['paused_at'] or row['updated_at'])).total_seconds())
    return max(0,value)

def enabled(db,run):
    row=db.execute('SELECT value FROM settings WHERE key=?',('short_view_wait/'+run,)).fetchone()
    return json.loads(row[0]) if row else True

def set_enabled(db,run,value):
    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('short_view_wait/'+run,json.dumps(bool(value))))
    # Disabling consumes any pending wait so re-enabling cannot replay it.
    if not value:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='short_view_waits'").fetchone()
        if exists: db.execute('UPDATE short_view_waits SET cancelled=1 WHERE run_id=?',(run,))

def plan(db,run,visit,elapsed,at=None):
    at=at or ledger.now()
    db.execute('''CREATE TABLE IF NOT EXISTS short_view_waits(
        run_id TEXT NOT NULL,visit TEXT NOT NULL,seconds INTEGER NOT NULL,
        deadline TEXT NOT NULL,cancelled INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(run_id,visit))''')
    row=db.execute('SELECT * FROM short_view_waits WHERE run_id=? AND visit=?',(run,visit)).fetchone()
    if not row:
        seconds=random.randint(20,40) if enabled(db,run) and elapsed<30 else 0
        db.execute('INSERT OR IGNORE INTO short_view_waits VALUES (?,?,?,?,0)',(run,visit,seconds,(at+timedelta(seconds=seconds)).isoformat()))
        row=db.execute('SELECT * FROM short_view_waits WHERE run_id=? AND visit=?',(run,visit)).fetchone()
    left=max(0,math.ceil((ledger.parse_time(row['deadline'])-at).total_seconds())) if enabled(db,run) and not row['cancelled'] else 0
    return dict(state='short_view_wait' if left else 'ready',retry_after_seconds=left,retry_at=row['deadline'] if left else None,seconds=row['seconds'])
