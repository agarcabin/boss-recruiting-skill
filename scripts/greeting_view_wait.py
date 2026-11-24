"""Minimum time per opened resume and durable rest after confirmed greetings."""
import math


MIN_ADAPTIVE_SECONDS=30
MAX_ADJUST_SECONDS=5
FAST_RATIO=.75
SLOW_RATIO=1.25


def adjustment(base, speed):
    if base < MIN_ADAPTIVE_SECONDS or speed <= 0:return 0
    if speed <= base*FAST_RATIO:return MAX_ADJUST_SECONDS
    if speed >= base*SLOW_RATIO:return -MAX_ADJUST_SECONDS
    return 0


def adaptive_config(db, run, config):
    """Adjust the fixed HR waits by at most 5 seconds using actual active pace.

    Active pace is total active elapsed time divided by completed candidates, so
    AI overall-review time and page/scroll stalls are both included.
    """
    base=float(config.get('minimum_seconds', config.get('average_seconds', 30)) or 0)
    rest=float(config.get('rest_seconds', 0) or 0)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidate_progress'").fetchone():
        return dict(config), dict(base_view_seconds=base, base_rest_seconds=rest,
                                  speed_seconds=None, adjust_seconds=0)
    viewed=db.execute(
        'SELECT COUNT(*) FROM candidate_progress WHERE run_id=? AND finished_at IS NOT NULL',
        (run,),
    ).fetchone()[0]
    if base < MIN_ADAPTIVE_SECONDS or viewed < 3:
        return dict(config), dict(base_view_seconds=base, base_rest_seconds=rest,
                                  speed_seconds=None, adjust_seconds=0)
    import ledger
    elapsed=ledger.active_elapsed_seconds(db, run)
    speed=elapsed/viewed if viewed else 0
    change=adjustment(base, speed)
    adjusted=dict(config, minimum_seconds=max(0, base+change), average_seconds=max(0, base+change))
    if rest > 0:adjusted['rest_seconds']=max(0, rest+change)
    return adjusted, dict(base_view_seconds=base, base_rest_seconds=rest,
                          speed_seconds=round(speed, 1), adjust_seconds=change)


def plan(db, run, visit, elapsed, config, active):
    from greeting_rate import transaction
    with transaction(db):
        return _plan(db, run, visit, elapsed, config, active)


def _plan(db, run, visit, elapsed, config, active):
    db.execute('''CREATE TABLE IF NOT EXISTS greeting_view_waits(
        run_id TEXT,visit TEXT,view_seconds REAL,rest_seconds REAL,start_active REAL,
        PRIMARY KEY(run_id,visit))''')
    db.execute('''CREATE TABLE IF NOT EXISTS greeting_rest_awards(
        run_id TEXT,batch INTEGER,visit TEXT,PRIMARY KEY(run_id,batch))''')
    columns={row[1] for row in db.execute('PRAGMA table_info(greeting_view_waits)')}
    for name in ('base_view_seconds','base_rest_seconds','speed_seconds','adjust_seconds'):
        if name not in columns:
            db.execute(f'ALTER TABLE greeting_view_waits ADD COLUMN {name} REAL')
    row = db.execute('SELECT * FROM greeting_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    if row is None:
        config, adaptation = adaptive_config(db, run, config)
        minimum = config.get('minimum_seconds', config.get('average_seconds', 30))
        view = max(0, minimum - elapsed)
        sent = db.execute("SELECT 1 FROM candidates WHERE run_id=? AND candidate_hash=? AND status='sent'", (run, visit)).fetchone()
        rest = 0
        if sent:
            count = db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'", (run,)).fetchone()[0]
            batch = count // config.get('rest_after_greetings', 5)
            awarded = db.execute('SELECT COALESCE(MAX(batch),0) FROM greeting_rest_awards WHERE run_id=?', (run,)).fetchone()[0]
            if batch > awarded:
                rest = config.get('rest_seconds', 0)
                db.execute('INSERT INTO greeting_rest_awards VALUES (?,?,?)', (run, batch, visit))
        db.execute('''INSERT INTO greeting_view_waits(
            run_id,visit,view_seconds,rest_seconds,start_active,
            base_view_seconds,base_rest_seconds,speed_seconds,adjust_seconds)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (run, visit, view, rest, active, adaptation['base_view_seconds'],
             adaptation['base_rest_seconds'], adaptation['speed_seconds'], adaptation['adjust_seconds']))
        row = db.execute('SELECT * FROM greeting_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    spent = max(0, active - row['start_active'])
    view_left = max(0, math.ceil(row['view_seconds'] - spent))
    rest_left = max(0, math.ceil(row['rest_seconds'] - max(0, spent - row['view_seconds'])))
    left = max(0, math.ceil(row['view_seconds'] + row['rest_seconds'] - spent))
    return dict(state='short_view_wait' if left else 'ready', seconds=row['view_seconds'] + row['rest_seconds'],
                retry_after_seconds=left, retry_at=None, timing_policy='per_resume_greetings_v3',
                view_wait_seconds=row['view_seconds'], rest_seconds=row['rest_seconds'],
                view_remaining_seconds=view_left, rest_remaining_seconds=rest_left,
                base_view_seconds=row['base_view_seconds'], base_rest_seconds=row['base_rest_seconds'],
                speed_seconds=row['speed_seconds'], adjust_seconds=row['adjust_seconds'])


def runner_wait(runner, run, rules):
    import short_view_wait
    start = runner.data.get('resume_started_active')
    if start is None:
        return dict(state='ready', retry_after_seconds=0, seconds=0)
    active = short_view_wait.active_clock(runner.db, runner.run)
    elapsed = max(0, active - start - runner.data.get('excluded_wait_seconds', 0))
    config = rules['hr_job_config']
    if short_view_wait.coworker_exempt(rules, runner.data.get('coworker_result'), runner.data.get('decision')):
        config = dict(config, minimum_seconds=0)
    if not short_view_wait.enabled(runner.db, runner.run):
        config = dict(config, minimum_seconds=0, rest_seconds=0)
    return plan(runner.db, runner.run, runner.data['visit_hash'], elapsed, config, active)
