"""Launch the overlay outside the cancellable agent tool's process job."""
import workspace_paths
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
    p.add_argument('--run',required=True);p.add_argument('--output-root',type=Path,default=workspace_paths.desktop_dir())
    p.add_argument('--chat-title',help='Exact recruiting chat title when renamed from the default');a=p.parse_args()
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file(): raise RuntimeError('pythonw_missing')
    db=ledger.connect(a.db)
    try:
        run=ledger.run_row(db,a.run)
        if run['stop_reason']: raise ValueError('run_already_stopped')
        import stop_controller
        binding_status='bound'
        try:stop_controller.bind_run(db,a.run,a.chat_title)
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
            binding_status='failed: '+str(exc)
        db.execute('UPDATE runs SET interrupt_status=? WHERE run_id=?',(binding_status,a.run))
        import run_cleanup,run_safety,local_mutex,run_admission
        with local_mutex.locked('recruiting-startup:'+run_admission.path(db).casefold()):
            if ledger.run_row(db,a.run)['stop_reason']:raise ValueError('run_already_stopped')
            run_cleanup.close_previous(db,keep_run=a.run,root=a.output_root)
            import chat_watchdog
            chat_watchdog.ensure(db,a.run,a.db)
            owner=db.execute('SELECT pid,birth FROM overlay_owner WHERE run_id=?',(a.run,)).fetchone()
            if owner and run_cleanup.alive(owner['pid'],owner['birth']):
                ledger.output(state='overlay_already_running',pid=owner['pid'],run_id=a.run)
                return
            command=[str(pythonw),'-X','utf8',str(Path(__file__).with_name('progress_window.py')),'--db',str(a.db),'--run',a.run,'--output-root',str(a.output_root)]
            process=launch_process(command)
            db.execute('INSERT OR REPLACE INTO overlay_owner VALUES (?,?,?)',(a.run,process.pid,run_safety.process_birth(process.pid)))
        ledger.output(state='overlay_started',pid=process.pid,require_visible_confirmation=True,stop_binding=binding_status)
    finally:db.close()
if __name__=='__main__':main()
