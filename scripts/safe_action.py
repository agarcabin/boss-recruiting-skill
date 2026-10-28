"""Only external-action entrypoint: binds an attempt, serializes with stop, never retries."""
import contextlib
import argparse
import json
import subprocess
import sys
from pathlib import Path
import ledger
import run_safety
import powershell_host

def dispatch(db,run_id,generation,command,token=None):
    with run_safety.action_lock(db):
        run=run_safety.ensure_writable(db,run_id,generation)
        if ledger.now()>=ledger.parse_time(run['deadline_at']) or ledger.control_state(db,run_id)!='running': raise ValueError('run_not_running')
        if token:
            attempt=db.execute('SELECT * FROM message_attempts WHERE token=?',(token,)).fetchone()
            if not attempt or attempt['run_id']!=run_id or attempt['status']!='pending' or attempt['generation']!=generation: raise ValueError('attempt_not_ready')
            db.execute("UPDATE message_attempts SET status='dispatching' WHERE token=?",(token,))
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        created=run_safety.process_birth(process.pid)
        db.execute('INSERT OR REPLACE INTO run_helpers VALUES (?,?,?)',(run_id,process.pid,created))
        try:
            out,err=process.communicate(timeout=4)
            if process.returncode: raise RuntimeError(err.decode('utf-8',errors='replace')[-1200:])
            return {'state':'dispatched','verified_sent':False,'token':token,'output':out.decode('utf-8-sig',errors='replace')}
        except Exception:
            if process.poll() is None: process.kill();process.communicate()
            if token:
                db.execute("UPDATE message_attempts SET status='unknown',updated_at=? WHERE token=?",(ledger.iso(ledger.now()),token))
                db.execute("UPDATE candidates SET status='unknown' WHERE token=? AND status='pending'",(token,))
            raise
        finally: db.execute('DELETE FROM run_helpers WHERE run_id=? AND pid=?',(run_id,process.pid))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB)
    p.add_argument('--run',required=True);p.add_argument('--generation',required=True,type=int)
    p.add_argument('--target',required=True,type=Path);p.add_argument('--token');p.add_argument('--text-file',type=Path)
    p.add_argument('--action',choices=('invoke','send-text','mouse','scroll-list','key'),default='invoke');p.add_argument('--mouse-args',type=Path);p.add_argument('--key',choices=('Right','Left','Escape'))
    a=p.parse_args()
    if a.action=='send-text' and (not a.token or not a.text_file): raise ValueError('send_text_requires_attempt_and_text')
    if a.action=='key' and (not a.key or a.token or a.text_file): raise ValueError('key_action_requires_allowed_key_without_message_token')
    with contextlib.closing(ledger.connect(a.db)) as db:
        run=ledger.run_row(db,a.run)
        target=json.loads(a.target.read_text(encoding="utf-8-sig"))
        digest=ledger.run_candidate_hash(db,a.run,target["candidate_id"]) if a.action!="scroll-list" else None
        active=ledger.active_progress(db,a.run)
        if a.action=="scroll-list":
            if active or run_safety.quantity_reason(db,a.run) or not target["document_url"].startswith("https://www.zhipin.com/web/chat/recommend"): raise ValueError("cannot_scroll_next_list")
        elif not active or active["candidate_hash"]!=digest: raise ValueError("target_candidate_not_active")
        if a.action=='key' and run['evaluation_mode']!='resume': raise ValueError('key_navigation_requires_resume_mode')
        if a.action=='key' and not any(target.get('document_url','').startswith(prefix) for prefix in ('https://www.zhipin.com/web/frame/recommend/','https://www.zhipin.com/web/frame/c-resume/')): raise ValueError('key_navigation_document_not_allowed')
        if run["evaluation_mode"]=="card" and a.action in ("invoke","mouse") and target["name"] not in ("打招呼","继续沟通","继续打招呼","关闭"):
            raise ValueError("card_mode_cannot_open_resume")
        if target.get("name") in ("打招呼","发送") and not a.token: raise ValueError("sending_requires_attempt")
        if a.token:
            attempt=db.execute("SELECT candidate_hash,message_index FROM message_attempts WHERE token=?",(a.token,)).fetchone()
            if not attempt or attempt[0]!=digest: raise ValueError("attempt_target_mismatch")
            if attempt[1]>1 and a.action!="send-text": raise ValueError("followup_requires_text_action")
            if attempt[1]==1 and (a.action=="send-text" or target["name"]!="打招呼"): raise ValueError("first_message_requires_greeting_button")
        command=[]
        if a.action=='mouse':
            args=json.loads(a.mouse_args.read_text(encoding='utf-8-sig'))
            command += [str(Path(__file__).with_name('move-click.ps1')),'-GuardDeadline',run['deadline_at'],'-GuardTarget',str(a.target)]
            allowed={'X','Y','StartX','StartY','WindowHandle','ContentBounds','SafeZonesPath'}
            if set(args)-allowed: raise ValueError('unsupported_mouse_arguments')
            for key,value in args.items(): command += ['-'+key,str(value)]
        elif a.action=='key':
            command += [str(Path(__file__).with_name('guarded-uia-action.ps1')),'-Target',str(a.target),'-Deadline',run['deadline_at'],'-Action','Key','-Key',a.key]
        else:
            command += [str(Path(__file__).with_name('guarded-uia-action.ps1')),'-Target',str(a.target),'-Deadline',run['deadline_at'],'-Action','SendText' if a.action=='send-text' else 'Scroll' if a.action=='scroll-list' else 'Invoke']
            if a.text_file: command += ['-TextFile',str(a.text_file)]
        command=powershell_host.command(command[0], *command[1:])
        print(json.dumps(dispatch(db,a.run,a.generation,command,a.token),ensure_ascii=False))
if __name__=='__main__': main()
