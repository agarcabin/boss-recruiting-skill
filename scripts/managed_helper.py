"""Register cancellable local capture/OCR/wait helpers; no arbitrary UI shell entrypoint."""
import contextlib
import argparse
import os
import subprocess
import sys
import time
import json
from pathlib import Path
import ledger
import run_safety
import capture_control
import foreground_activity
from windows_process import hidden_options,decode_output

def run(db,run_id,generation,command):
    capture_control.require_running(db,run_id,generation)
    with foreground_activity.track(db,run_id,command):
        return _run(db,run_id,generation,command)


def _run(db,run_id,generation,command):
    process=None;registered=False
    try:
        with run_safety.action_lock(db):
            capture_control.require_running(db,run_id,generation)
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**hidden_options())
            db.execute('INSERT INTO run_helpers VALUES (?,?,?)',(run_id,process.pid,run_safety.process_birth(process.pid)))
            registered=True
        while True:
            capture_control.require_running(db,run_id,generation)
            try:
                stdout,stderr=process.communicate(timeout=.2)
                break
            except subprocess.TimeoutExpired:
                continue
        sys.stdout.buffer.write(stdout);sys.stdout.buffer.flush()
        sys.stderr.buffer.write(stderr);sys.stderr.buffer.flush()
        return process.returncode
    finally:
        try:
            if process is not None and process.poll() is None:
                process.kill();process.wait(timeout=2)
        finally:
            if registered:
                db.execute('DELETE FROM run_helpers WHERE run_id=? AND pid=?',(run_id,process.pid))


def write_error(state,exc,**values):
    message=dict(state=state,reason=str(exc),error_type=type(exc).__name__,**values)
    if isinstance(exc,subprocess.CalledProcessError):
        message.update(exit_code=exc.returncode,reason=decode_output(exc.stderr or exc.stdout) or str(exc))
    sys.stderr.buffer.write((json.dumps(message,ensure_ascii=False)+'\n').encode('utf-8'))
    sys.stderr.buffer.flush()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('--run',required=True);p.add_argument('--generation',type=int,required=True)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command: raise ValueError('helper_command_required')
    # A supervisor, not an alternative route for unguarded BOSS clicks/keystrokes.
    allowed={'resume_capture.ps1','resume_image_pipeline.py','capture-card.ps1','idle_mouse.py'}
    scripts=[Path(x).name for x in command if x.endswith(('.py','.ps1'))]
    if len(scripts)!=1 or scripts[0] not in allowed: raise ValueError('unsupported_managed_helper')
    try:
        with contextlib.closing(ledger.connect(a.db)) as db: code=run(db,a.run,a.generation,command)
    except capture_control.CaptureInterrupted as exc:
        write_error('helper_interrupted',exc,foreground_required=exc.foreground_required,normal=exc.normal)
        code=20
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        write_error('helper_failed',exc)
        code=1
    raise SystemExit(code)
if __name__=='__main__':main()
