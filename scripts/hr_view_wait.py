"""Persistent viewing-average waits and extra rest every ten opened resumes."""
import math


def plan(db, run, visit, elapsed, config, active):
    db.execute('''CREATE TABLE IF NOT EXISTS hr_view_waits(
        run_id TEXT NOT NULL,visit TEXT NOT NULL,ordinal INTEGER NOT NULL,
        elapsed REAL NOT NULL,start_active REAL NOT NULL,average_wait REAL NOT NULL,
        rest REAL NOT NULL,done INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(run_id,visit),UNIQUE(run_id,ordinal))''')
    row = db.execute('SELECT * FROM hr_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    if row is None:
        previous = db.execute('SELECT * FROM hr_view_waits WHERE run_id=? ORDER BY ordinal', (run,)).fetchall()
        if any(not r['done'] for r in previous):
            raise ValueError('上一份查看等待尚未完成')
        ordinal = len(previous)+1
        total = sum(r['elapsed']+r['average_wait'] for r in previous)+elapsed
        wait = max(0, ordinal*config['average_seconds']-total)
        rest = config['rest_seconds'] if ordinal % 10 == 0 else 0
        db.execute('INSERT INTO hr_view_waits VALUES(?,?,?,?,?,?,?,0)', (run, visit, ordinal, elapsed, active, wait, rest))
        row = db.execute('SELECT * FROM hr_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    seconds = row['average_wait']+row['rest']
    left = 0 if row['done'] else max(0, math.ceil(seconds-max(0, active-row['start_active'])))
    if not left:
        db.execute('UPDATE hr_view_waits SET done=1 WHERE run_id=? AND visit=?', (run, visit))
    return dict(state='short_view_wait' if left else 'ready', retry_after_seconds=left,
                retry_at=None, seconds=seconds, timing_policy='hr', ordinal=row['ordinal'])


def runner_wait(runner, run):
    import recruiting_rules
    import short_view_wait
    start = runner.data.get('resume_started_active')
    if start is None:
        return dict(state='ready', retry_after_seconds=0, seconds=0)
    active = short_view_wait.active_clock(runner.db, runner.run)
    elapsed = max(0, active-start-runner.data.get('excluded_wait_seconds', 0))
    config = recruiting_rules.run_rules(run)['hr_job_config']
    return plan(runner.db, runner.run, runner.data['visit_hash'], elapsed, config, active)
