"""Independent per-run chat monitoring; UIA never writes a user's composer."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
import time

import ledger
import local_mutex
import powershell_host
import run_safety
from vault_crypto import atomic, canonical
from windows_process import hidden_options

HANDOFFS = {'assessment','overall_review','misjudgment_review','summary','followups','filter_notice','coworker_notice'}


def display_state(saved, at=None):
    state = dict(saved)
    at = time.time() if at is None else at
    if state.get('checked_at') is not None and at-state['checked_at'] > 45:
        state.update(measured='unknown', alert='GPT状态监测已中断，请检查运行状态')
    return state


def pending(data):
    if data.get('handoff_kind') not in HANDOFFS:return None
    try:
        request = Path(data['request_file']).read_bytes()
        request_object = json.loads(request)
        if not isinstance(request_object, dict):return None
        response = Path(data['response_file'])
        if response.exists():
            try:
                answer = json.loads(response.read_text(encoding='utf-8-sig'))
                evidence = request_object.get('evidence', {})
                kind = data['handoff_kind']
                valid = bool(isinstance(answer, dict) and answer)
                if kind in ('overall_review','misjudgment_review'):
                    valid = valid and answer.get('request_id') == evidence.get('request_id') and bool(evidence.get('request_id'))
                    if valid:
                        if kind == 'overall_review':
                            import overall_review
                            overall_review.validate(answer, evidence)
                        else:
                            import misjudgment_review
                            misjudgment_review.validate(answer, evidence)
                elif kind == 'summary':valid = valid and all(isinstance(answer.get(k), str) and answer[k].strip() for k in ('pros','cons'))
                elif kind in ('filter_notice','coworker_notice'):
                    valid = valid and answer.get('displayed') is True and answer.get('notice_id') == evidence.get('notice_id') and bool(evidence.get('notice_id'))
                if valid:return None
            except (OSError, ValueError, UnicodeError):pass
    except (KeyError, OSError, ValueError):return None
    return hashlib.sha256(request).hexdigest()


def transition(previous, episode, observation, at):
    """Pure fake-clock-testable state machine. UNKNOWN never counts as idle."""
    state = dict(previous) if previous.get('episode') == episode else dict(episode=episode, strikes=0)
    measured = observation.get('state', 'unknown')
    state.update(measured=measured, checked_at=at, reason=observation.get('reason'))
    if not episode:
        return dict(measured=measured, checked_at=at, strikes=0), 'none'
    if measured == 'user_stop':return state, 'pause'
    if state.get('attempted'):
        if measured == 'active':
            state.update(active_seen=True, strikes=0)
            state.pop('idle_since', None)
            return state, 'none'
        if measured == 'idle':state.setdefault('idle_since', at)
        deadline_base = state.get('idle_since', at) if state.get('active_seen') else state.get('confirmation_since', state['attempted_at'])
        if (measured == 'idle' or not state.get('active_seen')) and at-deadline_base >= 45:
            return state, 'pause'
        return state, 'none'
    state['strikes'] = state.get('strikes', 0)+1 if measured == 'idle' else 0
    return state, 'recover' if state['strikes'] >= 3 else 'none'


def probe(binding, run_id, resume=False):
    if not binding:return dict(state='unknown', reason='chat_binding_missing')
    if binding.get('kind') == 'uia':
        if resume:return dict(state='unsupported', reason='当前聊天仅支持状态监测，自动续发通道不可用，请回复“继续”')
        script, args = 'codex-recovery-probe.ps1', []
    elif binding.get('kind') == 'app_server' and binding.get('desktop_thread_verified') is True:
        if resume and not (binding.get('recovery_guard_method') and binding.get('recovery_dispatch_method')):
            return dict(state='unsupported', reason='原桌面聊天未提供带用户输入门禁的原子恢复通道，请回复“继续”')
        script = 'app-server-stop.ps1'
        args = ['-Action', 'Resume' if resume else 'RecoveryProbe', '-RunId', run_id]
    else:return dict(state='unknown', reason='verified_desktop_channel_unavailable')
    with tempfile.TemporaryDirectory(prefix='recruiting-chat-probe-') as folder:
        path = Path(folder)/'binding.json'
        atomic(path, canonical(binding))
        result = subprocess.run(powershell_host.command(Path(__file__).with_name(script), '-Binding', path, *args),
                                capture_output=True, timeout=7, **hidden_options())
        if result.returncode:return dict(state='unknown', reason='chat_probe_failed')
        return json.loads(result.stdout.decode('utf-8-sig'))


def mark_pause_boundary(db, run_id, episode):
    if not episode:return
    row = db.execute('SELECT payload FROM chat_recovery_episodes WHERE run_id=? AND episode=?', (run_id, episode)).fetchone()
    if not row:return
    saved = json.loads(row[0])
    saved.update(strikes=0, boundary_paused=True)
    saved.pop('idle_since', None)
    # Attempted/attempted_at are audit facts and must survive this boundary.
    db.execute('UPDATE chat_recovery_episodes SET payload=? WHERE run_id=? AND episode=?', (json.dumps(saved,ensure_ascii=False),run_id,episode))


def control_epoch(db, run_id):
    db.execute('CREATE TABLE IF NOT EXISTS chat_control_epochs(run_id TEXT PRIMARY KEY,epoch INTEGER NOT NULL)')
    db.execute('''CREATE TRIGGER IF NOT EXISTS chat_control_epoch_update AFTER UPDATE OF state ON run_control
        WHEN OLD.state!=NEW.state BEGIN
        INSERT INTO chat_control_epochs VALUES(NEW.run_id,1)
        ON CONFLICT(run_id) DO UPDATE SET epoch=chat_control_epochs.epoch+1;
        END''')
    db.execute('''CREATE TRIGGER IF NOT EXISTS chat_control_epoch_insert AFTER INSERT ON run_control BEGIN
        INSERT INTO chat_control_epochs VALUES(NEW.run_id,1)
        ON CONFLICT(run_id) DO UPDATE SET epoch=chat_control_epochs.epoch+1;
        END''')
    row = db.execute('SELECT epoch FROM chat_control_epochs WHERE run_id=?', (run_id,)).fetchone()
    return row[0] if row else 0


def tick(db, run_id, at=None, transport=probe):
    at = time.time() if at is None else at
    key = 'chat_watchdog/'+run_id
    with run_safety.action_lock(db):
        db.execute('CREATE TABLE IF NOT EXISTS chat_recovery_episodes(run_id TEXT NOT NULL,episode TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(run_id,episode))')
        has_workflow = db.execute("SELECT 1 FROM sqlite_master WHERE name='workflow_state'").fetchone()
        row = db.execute('SELECT phase,payload FROM workflow_state WHERE run_id=?', (run_id,)).fetchone() if has_workflow else None
        data = json.loads(row['payload']) if row else {}
        running = ledger.control_state(db, run_id) == 'running'
        episode = pending(data) if running else None
        old = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        previous = json.loads(old[0]) if old else {}
        if episode:
            saved = db.execute('SELECT payload FROM chat_recovery_episodes WHERE run_id=? AND episode=?', (run_id, episode)).fetchone()
            if saved:previous = json.loads(saved[0])
            previous.pop('paused', None)
            previous.pop('alert', None)
        run = ledger.run_row(db, run_id)
        generation = run['generation']
        epoch = control_epoch(db, run_id)
        if episode and (previous.pop('boundary_paused', False) or previous.get('run_generation', generation) != generation or previous.get('control_epoch', epoch) != epoch):
            previous['strikes'] = 0
            previous.pop('idle_since', None)
            if previous.get('attempted'):previous['confirmation_since'] = at
        binding = json.loads(run['stop_binding']) if run['stop_binding'] else None
    try:observed = transport(binding, run_id)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):observed = dict(state='unknown', reason='chat_probe_failed')
    state, action = transition(previous, episode, observed, at)
    state['run_generation'] = generation
    state['control_epoch'] = epoch
    persist_episode = bool(episode)
    with run_safety.action_lock(db):
        # A completed response, user pause, or changed candidate wins over a
        # measurement that was taken while the native call was in flight.
        row = db.execute('SELECT payload FROM workflow_state WHERE run_id=?', (run_id,)).fetchone() if has_workflow else None
        latest = json.loads(row[0]) if row else {}
        latest_running = ledger.control_state(db, run_id) == 'running'
        latest_generation = ledger.run_row(db, run_id)['generation']
        latest_epoch = control_epoch(db, run_id)
        if not latest_running or pending(latest) != episode or latest_generation != generation or latest_epoch != epoch:
            persist_episode = False
            state, action = transition({}, None, observed, at)
            if not latest_running or latest_generation != generation or latest_epoch != epoch:mark_pause_boundary(db,run_id,pending(latest))
            if not latest_running:
                state['paused'] = True
                if previous.get('alert'):state['alert'] = previous['alert']
        if action == 'recover':
            state.update(attempted=True, attempted_at=at, recovery_state='dispatching')
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(state, ensure_ascii=False)))
            db.execute('INSERT OR REPLACE INTO chat_recovery_episodes VALUES (?,?,?)', (run_id, episode, json.dumps(state, ensure_ascii=False)))
            try:receipt = transport(binding, run_id, resume=True)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):receipt = dict(state='unknown', reason='recovery_dispatch_unconfirmed')
            state['recovery_state'] = receipt.get('state', 'unknown')
            if receipt.get('state') != 'started':
                state['reason'] = receipt.get('reason') or '自动恢复未确认，请回复“继续”'
                action = 'pause'
        if action == 'pause':
            state['paused'] = True
            state['strikes'] = 0
            state['boundary_paused'] = True
            state.pop('idle_since', None)
            state['alert'] = state.get('reason') or 'GPT未恢复，招聘已暂停，请回复“继续”'
            with contextlib.redirect_stdout(io.StringIO()):
                ledger.control(db, argparse.Namespace(run=run_id, action='pause'))
            import error_alert
            error_alert.play()
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, json.dumps(state, ensure_ascii=False)))
        if persist_episode:
            db.execute('INSERT OR REPLACE INTO chat_recovery_episodes VALUES (?,?,?)', (run_id, episode, json.dumps(state, ensure_ascii=False)))
    return state


def ensure(db, run_id, database):
    import run_cleanup
    from launch_progress import launch_process
    with local_mutex.locked('chat-watchdog:'+str(database)+':'+run_id):
        db.execute('CREATE TABLE IF NOT EXISTS watchdog_owner(run_id TEXT PRIMARY KEY,pid INTEGER,birth REAL)')
        owner = db.execute('SELECT pid,birth FROM watchdog_owner WHERE run_id=?', (run_id,)).fetchone()
        if owner and run_cleanup.alive(owner['pid'], owner['birth']):return owner['pid']
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        process = launch_process([str(pythonw), '-X', 'utf8', __file__, '--db', str(database), '--run', run_id])
        db.execute('INSERT OR REPLACE INTO watchdog_owner VALUES (?,?,?)', (run_id, process.pid, run_safety.process_birth(process.pid)))
        return process.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ledger.DEFAULT_DB)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        with local_mutex.locked('chat-watchdog-instance:'+str(args.db.resolve())+':'+args.run, timeout=.1):
            with contextlib.closing(ledger.connect(args.db)) as db:
                # A detached child claims itself even if its launcher crashes
                # before recording the PID. The lifetime mutex is authoritative.
                with local_mutex.locked('chat-watchdog:'+str(args.db)+':'+args.run):
                    db.execute('CREATE TABLE IF NOT EXISTS watchdog_owner(run_id TEXT PRIMARY KEY,pid INTEGER,birth REAL)')
                    db.execute('INSERT OR REPLACE INTO watchdog_owner VALUES (?,?,?)', (args.run, os.getpid(), run_safety.process_birth(os.getpid())))
                try:
                    while not ledger.run_row(db, args.run)['stop_reason']:
                        time.sleep(15)
                        if ledger.run_row(db, args.run)['stop_reason']:break
                        try:tick(db, args.run)
                        except (OSError, ValueError, RuntimeError, TimeoutError, sqlite3.Error) as exc:
                            # A temporarily unavailable native surface must not
                            # kill the independent monitor or authorize a retry.
                            try:
                                db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('chat_watchdog/'+args.run, json.dumps(dict(measured='unknown', checked_at=time.time(),reason='monitor_temporarily_unavailable',alert='GPT状态暂无法确认：'+str(exc)[:120]),ensure_ascii=False)))
                            except sqlite3.Error:pass
                finally:db.execute('DELETE FROM watchdog_owner WHERE run_id=? AND pid=?', (args.run, os.getpid()))
    except TimeoutError:return


if __name__ == '__main__':main()
