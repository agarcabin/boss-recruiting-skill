"""UIA action entrypoint with optional accounting, without per-action identity fences."""
from __future__ import annotations
import argparse
import contextlib
import json
import subprocess
from pathlib import Path
import ledger
import powershell_host
import recruiting_rules


def validate_greeting_action(run, action, target):
    if recruiting_rules.run_greeting_mode(run) == 'single':
        if action == 'send-text' or target.get('name') in ('继续沟通', '继续打招呼'):
            raise ValueError('single_greeting_disallows_followups')


def validate_candidate_target(db, run, action, target, active, digest, token=None, key=None):
    # Compatibility API. Candidate/active/generation checks were removed by the user.
    return None


def business_check(db, run_id, candidate_id):
    """Retain selected job criteria, colleague check, target quantity and profile version."""
    import coworker_progress
    run = ledger.run_row(db, run_id)
    path = Path(run['profile_path'])
    if ledger.profile_hash(path) != run['profile_hash']:
        raise ValueError('profile_changed_since_start')
    digest = ledger.run_candidate_hash(db, run_id, candidate_id)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone():
        raise ValueError('assessment_not_eligible')
    assessment = db.execute('SELECT * FROM assessments WHERE run_id=? AND candidate_hash=?', (run_id, digest)).fetchone()
    if not assessment or assessment['decision'] != 'greet' or not ledger.assessment_eligible(run, assessment):
        raise ValueError('assessment_not_eligible')
    if assessment['evaluation_mode'] != 'card':
        result = coworker_progress.evaluate(json.loads(assessment['coworker_progress'] or '{}'), ledger.now())
        if not result['may_continue']:
            raise ValueError(result['reason'])
    count = db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'", (run_id,)).fetchone()[0]
    if count >= run['target']:
        raise ValueError('run_target_reached')


def dispatch(db, run_id, generation, command, token=None):
    # No action lock, run-state/generation, active-candidate or token validity gate.
    process = subprocess.run(command, capture_output=True, timeout=8)
    if process.returncode:
        raise RuntimeError(process.stderr.decode('utf-8', errors='replace')[-1600:])
    return {'state': 'dispatched', 'verified_sent': False, 'token': token,
            'output': process.stdout.decode('utf-8-sig', errors='replace')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ledger.DEFAULT_DB)
    parser.add_argument('--run', required=True)
    parser.add_argument('--generation', type=int, help='Compatibility argument, ignored')
    parser.add_argument('--target', required=True, type=Path)
    parser.add_argument('--token', help='Optional accounting reference, not an action credential')
    parser.add_argument('--text-file', type=Path)
    parser.add_argument('--action', choices=('invoke', 'send-text', 'mouse', 'scroll-list', 'key'), default='invoke')
    parser.add_argument('--mouse-args', type=Path)
    parser.add_argument('--key', choices=('Right', 'Left', 'Escape', 'Refresh'))
    args = parser.parse_args()
    target = json.loads(args.target.read_text(encoding='utf-8-sig'))
    with contextlib.closing(ledger.connect(args.db)) as db:
        run = ledger.run_row(db, args.run)
        validate_greeting_action(run, args.action, target)
        is_sending = args.action == 'send-text' or target.get('name') in ('打招呼', '发送')
        token = args.token
        if is_sending:
            candidate_id = target.get('candidate_id')
            if not candidate_id:
                raise ValueError('candidate_id_needed_for_job_and_coworker_check')
            business_check(db, args.run, candidate_id)
            # Accounting is automatic; callers need not reserve or pass a token.
            if token is None and args.action != 'send-text':
                import io
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    ledger.reserve(db, argparse.Namespace(run=args.run, candidate_id=candidate_id))
                recorded = json.loads(out.getvalue())
                if recorded['state']=='already_sent':
                    print(json.dumps(recorded,ensure_ascii=False));return
                if recorded['state'] != 'ready':
                    raise ValueError(recorded.get('reason', recorded['state']))
                token = recorded['token']
        if args.action == 'mouse':
            values = json.loads(args.mouse_args.read_text(encoding='utf-8-sig'))
            allowed = {'X', 'Y', 'StartX', 'StartY', 'WindowHandle', 'ContentBounds', 'SafeZonesPath'}
            if set(values) - allowed:
                raise ValueError('unsupported_mouse_arguments')
            command = [str(Path(__file__).with_name('move-click.ps1'))]
            for key, value in values.items():
                command += ['-' + key, str(value)]
        else:
            action = {'send-text': 'SendText', 'key': 'Key', 'scroll-list': 'Scroll'}.get(args.action, 'Invoke')
            command = [str(Path(__file__).with_name('guarded-uia-action.ps1')), '-Target', str(args.target), '-Action', action]
            if args.key:
                command += ['-Key', args.key]
            if args.text_file:
                command += ['-TextFile', str(args.text_file)]
        command = powershell_host.command(command[0], *command[1:])
        result = dispatch(db, args.run, args.generation, command, token)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
