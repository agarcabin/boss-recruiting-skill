"""Minimum time per opened resume and durable rest after confirmed greetings."""
import math


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
    row = db.execute('SELECT * FROM greeting_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    if row is None:
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
        db.execute('INSERT INTO greeting_view_waits VALUES (?,?,?,?,?)', (run, visit, view, rest, active))
        row = db.execute('SELECT * FROM greeting_view_waits WHERE run_id=? AND visit=?', (run, visit)).fetchone()
    spent = max(0, active - row['start_active'])
    view_left = max(0, math.ceil(row['view_seconds'] - spent))
    rest_left = max(0, math.ceil(row['rest_seconds'] - max(0, spent - row['view_seconds'])))
    left = max(0, math.ceil(row['view_seconds'] + row['rest_seconds'] - spent))
    return dict(state='short_view_wait' if left else 'ready', seconds=row['view_seconds'] + row['rest_seconds'],
                retry_after_seconds=left, retry_at=None, timing_policy='per_resume_greetings_v3',
                view_wait_seconds=row['view_seconds'], rest_seconds=row['rest_seconds'],
                view_remaining_seconds=view_left, rest_remaining_seconds=rest_left)


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
