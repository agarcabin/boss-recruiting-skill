"""Versioned, active-time per-resume waits; frozen older runs keep their policy."""
import math


def plan(db, run, visit, elapsed, config, active, exempt=False):
    db.execute('''CREATE TABLE IF NOT EXISTS minimum_view_waits(
        run_id TEXT,visit TEXT,ordinal INTEGER,seconds REAL,start_active REAL,
        PRIMARY KEY(run_id,visit))''')
    row = db.execute('SELECT * FROM minimum_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    if row is None:
        ordinal = db.execute('SELECT COUNT(*) FROM minimum_view_waits WHERE run_id=?', (run,)).fetchone()[0]+1
        seconds = 0 if exempt else max(0, config.get('average_seconds', 30)-elapsed)
        # An exempt, genuinely opened resume still counts towards the ten-view rest.
        if ordinal % 10 == 0:
            seconds += config.get('rest_seconds', 0)
        db.execute('INSERT INTO minimum_view_waits VALUES (?,?,?,?,?)', (run, visit, ordinal, seconds, active))
        row = db.execute('SELECT * FROM minimum_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    left = max(0, math.ceil(row['seconds']-max(0, active-row['start_active'])))
    return dict(state='short_view_wait' if left else 'ready', seconds=row['seconds'],
                retry_after_seconds=left, retry_at=None, timing_policy='per_resume_v2')


def runner_wait(runner, run, rules):
    import short_view_wait
    start = runner.data.get('resume_started_active')
    if start is None:
        return dict(state='ready', retry_after_seconds=0, seconds=0)
    active = short_view_wait.active_clock(runner.db, runner.run)
    elapsed = max(0, active-start-runner.data.get('excluded_wait_seconds', 0))
    config = rules.get('hr_job_config', dict(average_seconds=rules.get('minimum_view_seconds', 30)))
    exempt = not short_view_wait.enabled(runner.db, runner.run) or short_view_wait.coworker_exempt(
        rules, runner.data.get('coworker_result'), runner.data.get('decision'))
    if exempt and not short_view_wait.enabled(runner.db, runner.run):
        config = dict(config, rest_seconds=0)
    return plan(runner.db, runner.run, runner.data['visit_hash'], elapsed, config, active, exempt)
