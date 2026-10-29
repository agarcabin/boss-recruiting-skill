"""Register cancellable local capture/OCR/wait helpers; no arbitrary UI shell entrypoint."""
import contextlib
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
import ledger
import run_safety

def run(db,run_id,generation,command):
    with run_safety.action_lock(db):
        state=run_safety.ensure_writable(db,run_id,generation)
        process=subprocess.Popen(command)
        db.execute('INSERT INTO run_helpers VALUES (?,?,?)',(run_id,process.pid,run_safety.process_birth(process.pid)))
    try:
        while process.poll() is None:
            state=ledger.run_row(db,run_id)
            if state['stop_reason'] or state['generation']!=generation:
                process.kill();process.wait(timeout=2);raise ValueError('helper_cancelled')
            time.sleep(.2)
        return process.returncode
    finally:
        if process.poll() is None: process.kill();process.wait(timeout=2)
        db.execute('DELETE FROM run_helpers WHERE run_id=? AND pid=?',(run_id,process.pid))

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
    with contextlib.closing(ledger.connect(a.db)) as db: code=run(db,a.run,a.generation,command)
    raise SystemExit(code)
if __name__=='__main__':main()
