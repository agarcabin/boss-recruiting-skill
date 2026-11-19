"""Wait for the next model handoff without starting a runner or touching BOSS."""
import argparse
import contextlib
import json
from pathlib import Path
import sqlite3
import time

import ledger


def snapshot(db, run_id):
    control = ledger.control_state(db, run_id)
    row = db.execute('SELECT phase,payload FROM workflow_state WHERE run_id=?', (run_id,)).fetchone()
    if row is None:
        return dict(state=control if control != 'running' else 'not_started', run_id=run_id)
    data = json.loads(row['payload'])
    result = dict(state=control if control != 'running' else data.get('scheduler_state', row['phase']),
                  run_id=run_id, phase=row['phase'], visits=data.get('visits', 0),
                  candidate_name=(data.get('candidate') or {}).get('candidate_name'),
                  error=data.get('error'),notice_wait=data.get('notice_wait'))
    if control != 'running':
        return result
    kind = data.get('handoff_kind')
    request, response = data.get('request_file'), data.get('response_file')
    if kind and request and response:
        try:
            evidence = json.loads(Path(request).read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, json.JSONDecodeError, UnicodeError):
            return dict(result, state='handoff_file_pending')
        try:
            # A partially written response is not ready for the runner either.
            answered = json.loads(Path(response).read_text(encoding='utf-8-sig'))
        except FileNotFoundError:
            answered = None
        except (json.JSONDecodeError, UnicodeError):
            return dict(result, state='handoff_file_pending')
        if not answered:
            return dict(result, state='needs_' + kind, request_file=request,
                        response_file=response, request=evidence)
    return result


def wait(db, run_id, timeout=45, poll=.1):
    deadline = time.monotonic() + timeout
    while True:
        result = snapshot(db, run_id)
        state = result['state']
        if (state in {'paused', 'stopped', 'login_required', 'complete', 'needs_attention', 'needs_page'}
                or ('request' in result and state.startswith('needs_'))):
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return dict(result, wait_timed_out=True)
        time.sleep(min(poll, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ledger.DEFAULT_DB)
    parser.add_argument('--run', required=True)
    parser.add_argument('--timeout', type=float, default=45)
    args = parser.parse_args()
    if not 0 <= args.timeout <= 45:
        parser.error('--timeout must be between 0 and 45 seconds')
    # Read-only SQLite connection: monitoring must never create runs or events.
    with contextlib.closing(sqlite3.connect(args.db.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        print(json.dumps(wait(db, args.run, args.timeout), ensure_ascii=False))


if __name__ == '__main__':
    main()
