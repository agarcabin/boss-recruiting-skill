"""Local handoff to the Browser plugin. This module never drives a native window."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import capture_control
import ledger
import run_safety
import startup_plan
from workflow_paths import workflow_dir

PROVIDER = 'browser-plugin'


def validate_binding(value):
    if (value.get('provider') != PROVIDER or value.get('browser') != 'iab'
            or not isinstance(value.get('tab_id'), str) or not value['tab_id'].strip()):
        raise ValueError('browser_plugin_iab_tab_binding_required')
    url = urlsplit(value.get('url', ''))
    host = (url.hostname or '').lower()
    if (url.scheme != 'https' or not (host == 'zhipin.com' or host.endswith('.zhipin.com'))
            or url.username or url.password or url.port not in (None, 443)):
        raise ValueError('browser_plugin_boss_https_url_required')
    return dict(provider=PROVIDER, browser='iab', tab_id=value['tab_id'], url=value['url'])


def binding(db, run_id, source=None):
    key = 'browser_binding/' + run_id
    saved = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    if source:
        result = validate_binding(json.loads(Path(source).read_text(encoding='utf-8-sig')))
        if saved and validate_binding(json.loads(saved[0])) != result:
            raise ValueError('browser_plugin_run_binding_changed; finish the original run before rebinding')
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(result)))
        return result
    if saved:
        return validate_binding(json.loads(saved[0]))
    raise ValueError('browser_plugin_binding_required; bind the current chat Browser tab')


def pending(db, run_id):
    row = db.execute('SELECT value FROM settings WHERE key=?', ('browser_request/' + run_id,)).fetchone()
    if not row:
        return None
    value = json.loads(row[0])
    if value.get('status') not in ('pending', 'claimed'):
        return None
    return value


def save(db, request):
    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',
               ('browser_request/' + request['run_id'], json.dumps(request, ensure_ascii=False)))


def live(db, request):
    run_id = request['run_id']
    capture_control.require_running(db, run_id, request['generation'])
    try:
        owner_alive = abs(run_safety.process_birth(request['owner_pid']) - request['owner_birth']) < .0001
    except (OSError, ProcessLookupError):
        owner_alive = False
    if not owner_alive:
        raise ValueError('browser_plugin_request_owner_exited; resume original runner before acting')
    if time.time() >= request['expires_at']:
        raise ValueError('browser_plugin_request_expired; inspect current page before continuing')
    if binding(db, run_id) != request['binding']:
        raise ValueError('browser_plugin_request_binding_changed')


def claim(db, run_id, request_id):
    request = pending(db, run_id)
    if not request or request['request_id'] != request_id or request['status'] != 'pending':
        raise ValueError('browser_plugin_request_not_pending; never replay an already claimed action')
    live(db, request)
    if request['operation'] == 'send':
        import safe_action
        candidate_id = request['arguments']['candidate']['candidate_id']
        safe_action.business_check(db, run_id, candidate_id)
        digest = ledger.run_candidate_hash(db, run_id, candidate_id)
        reserved = db.execute("SELECT 1 FROM candidates WHERE run_id=? AND candidate_hash=? AND status='pending'",
                              (run_id, digest)).fetchone()
        if not reserved:
            raise ValueError('browser_plugin_send_requires_reserved_quota')
    previous = json.dumps(request, ensure_ascii=False)
    request['status'] = 'claimed'
    changed = db.execute('UPDATE settings SET value=? WHERE key=? AND value=?',
        (json.dumps(request, ensure_ascii=False), 'browser_request/' + run_id, previous))
    if changed.rowcount != 1:
        raise ValueError('browser_plugin_request_already_claimed')
    return request


def complete(db, run_id, request_id, result):
    request = pending(db, run_id)
    if not request or request['request_id'] != request_id or request['status'] != 'claimed':
        raise ValueError('browser_plugin_request_not_claimed')
    live(db, request)
    if not isinstance(result, dict):
        raise ValueError('browser_plugin_result_object_required')
    # The response remains tied to this exact request, tab and run generation.
    startup_plan.write(request['response_file'], dict(
        request_id=request_id, binding=request['binding'], generation=request['generation'], result=result))
    request['status'] = 'answered'
    save(db, request)
    return dict(state='answered', request_id=request_id)


class Bridge:
    def __init__(self, db, run_id, tab_binding):
        self.db, self.run, self.binding = db, run_id, validate_binding(tab_binding)

    def request(self, operation, arguments=None, timeout=120):
        generation = ledger.run_row(self.db, self.run)['generation']
        capture_control.require_running(self.db, self.run, generation)
        old = pending(self.db, self.run)
        if old:
            old['status'] = 'abandoned'
            save(self.db, old)
        request_id = uuid.uuid4().hex
        folder = workflow_dir(self.run)
        request = dict(provider=PROVIDER, request_id=request_id, run_id=self.run,
                       owner_pid=os.getpid(), owner_birth=run_safety.process_birth(os.getpid()),
                       generation=generation, binding=self.binding, operation=operation,
                       arguments=arguments or {}, expires_at=time.time() + timeout, status='pending',
                       request_file=str(folder / ('browser-' + request_id + '.json')),
                       response_file=str(folder / ('browser-' + request_id + '.response.json')))
        startup_plan.write(request['request_file'], request)
        save(self.db, request)
        try:
            while True:
                live(self.db, request)
                response = Path(request['response_file'])
                if response.is_file():
                    answer = json.loads(response.read_text(encoding='utf-8-sig'))
                    if (answer.get('request_id') != request_id or answer.get('binding') != self.binding
                            or answer.get('generation') != generation):
                        raise ValueError('browser_plugin_response_mismatch')
                    result = answer['result']
                    if not isinstance(result, dict):
                        raise ValueError('browser_plugin_result_object_required')
                    if result.get('error'):
                        raise ValueError('browser_plugin_operation_failed: ' + str(result['error']))
                    return result
                time.sleep(.1)
        finally:
            request['status'] = 'consumed' if Path(request['response_file']).is_file() else 'cancelled'
            save(self.db, request)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('claim', 'reply'))
    parser.add_argument('--db', type=Path, default=ledger.DEFAULT_DB)
    parser.add_argument('--run', required=True)
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--result-file', type=Path)
    args = parser.parse_args()
    with contextlib.closing(ledger.connect(args.db)) as db:
        if args.action == 'claim':
            result = claim(db, args.run, args.request_id)
        else:
            if args.result_file is None:
                parser.error('--result-file is required for reply')
            result = complete(db, args.run, args.request_id,
                              json.loads(args.result_file.read_text(encoding='utf-8-sig')))
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
