"""Idempotent favorite/login/sidebar actions via directed Win32 UIA."""
import argparse
import contextlib
import json
import subprocess
import tempfile
from pathlib import Path
import ledger
import powershell_host
import safe_action
from windows_process import hidden_options


def observe(action,hwnd=None):
    command=powershell_host.command(Path(__file__).with_name('boss-ui-features.ps1'),'-Action',action)
    if hwnd: command+=['-WindowHandle',str(hwnd)]
    done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8-sig',timeout=12,**hidden_options())
    if done.returncode: raise ValueError(done.stderr[-1500:])
    return json.loads(done.stdout)


def invoke(db,run_id,target):
    with tempfile.TemporaryDirectory(prefix='boss-feature-') as directory:
        path=Path(directory)/'target.json';path.write_text(json.dumps(target,ensure_ascii=False),encoding='utf-8')
        command=powershell_host.command(Path(__file__).with_name('guarded-uia-action.ps1'),'-Target',path,'-Action','Invoke')
        return safe_action.dispatch(db,run_id,None,command)


def favorite_eligible(db,run_id,digest):
    row=db.execute('SELECT overall_score,coworker_progress,eligibility_json FROM assessments WHERE run_id=? AND candidate_hash=?',(run_id,digest)).fetchone()
    if not row or row['overall_score'] <= 90:
        return False
    colleague=json.loads(row['coworker_progress'] or '{}')
    return colleague.get('action') not in ('skip','review') and json.loads(row['eligibility_json'] or '{}').get('trigger') not in ('coworker_skip','coworker_unknown')


def favorite(db,run_id,candidate_id,hwnd=None,reader=observe,click=invoke):
    db.execute('''CREATE TABLE IF NOT EXISTS favorite_results(run_id TEXT NOT NULL,candidate_hash TEXT NOT NULL,
        state TEXT NOT NULL,evidence TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(run_id,candidate_hash))''')
    digest=ledger.run_candidate_hash(db,run_id,candidate_id)
    if not favorite_eligible(db,run_id,digest):
        return dict(state='not_applicable')
    try:
        state=reader('Favorite',hwnd)
        if state['state']=='saved': result=dict(state='already_saved',evidence=state)
        elif state['state']=='unsaved':
            click(db,run_id,state['target'])
            verified=reader('Favorite',hwnd)
            result=dict(state='saved' if verified['state']=='saved' else 'pending',evidence=verified)
        else: result=dict(state='pending',evidence=state)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        result=dict(state='pending',evidence=dict(error=str(exc)))
    db.execute('INSERT INTO favorite_results VALUES (?,?,?,?,?) ON CONFLICT(run_id,candidate_hash) DO UPDATE SET state=excluded.state,evidence=excluded.evidence,updated_at=excluded.updated_at',
               (run_id,digest,result['state'],json.dumps(result['evidence'],ensure_ascii=False),ledger.iso(ledger.now())))
    return result


def once(action,db=None,run_id=None,hwnd=None,reader=observe,click=invoke):
    before=reader(action,hwnd)
    needed='present' if action=='Login' else 'expanded'
    if before['state']!=needed: return before
    try:
        click(db,run_id,before['target'])
    except RuntimeError as exc:
        # A missing runtime element means nothing was invoked. Refresh once.
        if 'uia_target_not_found' not in str(exc):
            return dict(state='pending',error=str(exc),clicked_once=False)
        before=reader(action,hwnd)
        if before['state']!=needed: return before
        try: click(db,run_id,before['target'])
        except RuntimeError as retry: return dict(state='pending',error=str(retry))
    after=reader(action,hwnd)
    success=after['state']==('absent' if action=='Login' else 'collapsed')
    return dict(state='confirmed' if success else 'pending',observation=after,clicked_once=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('inspect','favorite','login','sidebar'))
    p.add_argument('--db',type=Path,default=ledger.DEFAULT_DB);p.add_argument('--run');p.add_argument('--candidate-id');p.add_argument('--hwnd',type=int)
    args=p.parse_args()
    if args.action=='inspect': result=observe('Inspect',args.hwnd)
    elif args.action in ('login','sidebar'):
        # Native startup steps do not create a recruiting run or send messages.
        result=once(args.action.title(),hwnd=args.hwnd)
    else:
        with contextlib.closing(ledger.connect(args.db)) as db:
            result=favorite(db,args.run,args.candidate_id,args.hwnd)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
