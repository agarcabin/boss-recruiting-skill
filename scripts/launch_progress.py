"""Launch the overlay outside the cancellable agent tool's process job."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
import ledger

def launch_process(command):
    if os.name!='nt': raise RuntimeError('windows_overlay_required')
    flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
    # No fallback into the agent job: cancelling that job must not kill finalization.
    return subprocess.Popen(command,creationflags=flags,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('--run',required=True);p.add_argument('--output-root',type=Path,default=Path.home()/'Desktop');a=p.parse_args()
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file(): raise RuntimeError('pythonw_missing')
    db=ledger.connect(a.db)
    try:
        run=ledger.run_row(db,a.run)
        if run['stop_reason']: raise ValueError('run_already_stopped')
        command=[str(pythonw),'-X','utf8',str(Path(__file__).with_name('progress_window.py')),'--db',str(a.db),'--run',a.run,'--output-root',str(a.output_root)]
        process=launch_process(command)
        ledger.output(state='overlay_started',pid=process.pid,require_visible_confirmation=True)
    finally:db.close()
if __name__=='__main__':main()
