"""Persist colleague observations before resume analysis; no old action/state fences."""
import argparse
import contextlib
import json
from pathlib import Path
import coworker_progress
import ledger
import recruiting_rules


def table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS candidate_checks (
        run_id TEXT NOT NULL,candidate_hash TEXT NOT NULL,kind TEXT NOT NULL,
        observation TEXT NOT NULL,checked_at TEXT NOT NULL,
        PRIMARY KEY(run_id,candidate_hash,kind))''')


def mark_resume_opened(db, run_id, candidate_id):
    _receipt(db, run_id, candidate_id, 'resume_opened', {'confirmed': True})


def record_resume_attempt(db, run_id, candidate_id, observation):
    previous = get(db, run_id, candidate_id, 'resume_attempted') or {}
    history = previous.get('observations', [previous['observation']] if previous.get('observation') else [])
    _receipt(db, run_id, candidate_id, 'resume_attempted',
             {'attempted': True, 'observation': observation, 'observations': history + [observation]})


def _receipt(db, run_id, candidate_id, kind, observation):
    table(db)
    digest = ledger.run_candidate_hash(db, run_id, candidate_id)
    db.execute('INSERT OR REPLACE INTO candidate_checks VALUES (?,?,?,?,?)',
               (run_id, digest, kind, json.dumps(observation, ensure_ascii=False), ledger.iso(ledger.now())))


def worker_detail_ready(db, run_id, candidate_id):
    return bool((get(db, run_id, candidate_id, 'resume_opened') or {}).get('confirmed')
                and (get(db, run_id, candidate_id, 'resume_attempted') or {}).get('attempted'))


def evaluate_resume(db, run_id, candidate_id, observation):
    rules = recruiting_rules.run_rules(ledger.run_row(db, run_id))
    at = ledger.now()
    result = coworker_progress.evaluate_for_rules(observation, rules, at)
    if recruiting_rules.worker_v2(rules):
        attempted = get(db, run_id, candidate_id, 'resume_attempted') or {}
        for observed in attempted.get('observations', [attempted.get('observation')]):
            actual = coworker_progress.evaluate_for_rules(observed, rules, at)
            if actual.get('skip'):
                return actual
        if not worker_detail_ready(db, run_id, candidate_id):
            result.update(may_continue=False, skip=False, action='review', reason='worker_detail_check_attempt_required')
    return result


def record(db,run_id,candidate_id,observation,kind='resume'):
    table(db)
    digest=ledger.run_candidate_hash(db,run_id,candidate_id)
    active=db.execute('SELECT * FROM candidate_progress WHERE run_id=? AND candidate_hash=?',(run_id,digest)).fetchone()
    if active is None:active=ledger.ensure_candidate(db,run_id,candidate_id)
    if kind=='resume':
        result=evaluate_resume(db,run_id,candidate_id,observation)
    else:
        state=observation.get('state')
        result=dict(may_continue=state=='absent',skip=state=='present',action='skip' if state=='present' else 'continue' if state=='absent' else 'review',state=state,evidence=observation.get('evidence',''))
        if not observation.get('evidence') or (state!='present' and not observation.get('lookup_completed')):
            result.update(may_continue=False,action='review',skip=False)
    db.execute('INSERT INTO candidate_checks VALUES (?,?,?,?,?) ON CONFLICT(run_id,candidate_hash,kind) DO UPDATE SET observation=excluded.observation,checked_at=excluded.checked_at',
               (run_id,active['candidate_hash'],kind,json.dumps(observation,ensure_ascii=False),ledger.iso(ledger.now())))
    return result


def get(db,run_id,candidate_id,kind='resume'):
    table(db)
    digest=ledger.run_candidate_hash(db,run_id,candidate_id)
    row=db.execute('SELECT observation FROM candidate_checks WHERE run_id=? AND candidate_hash=? AND kind=?',(run_id,digest,kind)).fetchone()
    return json.loads(row[0]) if row else None


def require_resume(db,run_id,candidate_id):
    observation=get(db,run_id,candidate_id)
    result=evaluate_resume(db,run_id,candidate_id,observation)
    if not result['may_continue']:
        raise ValueError('coworker_check_before_analysis: '+str(result.get('reason',result['action'])))
    return observation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    parser.add_argument('--run',required=True); parser.add_argument('--candidate-id',required=True)
    parser.add_argument('--kind',choices=('resume','card'),default='resume')
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    observation=json.loads(args.input.read_text(encoding='utf-8-sig'))
    with contextlib.closing(ledger.connect(args.db)) as db:
        print(json.dumps(record(db,args.run,args.candidate_id,observation,args.kind),ensure_ascii=False))


if __name__=='__main__': main()
