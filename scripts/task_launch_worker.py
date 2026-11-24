"""On-demand scheduler worker; preserve environment, receipt and process lifetime."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import traceback



def atomic_json(path,payload):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    os.replace(temporary,path)


def run(request,token,transport):
    folder=request.parent
    payload=json.loads(request.read_text(encoding='utf-8'))
    task=payload['task']
    if folder.name!=token or task!='CodexRecruitingLaunch-'+token:
        raise ValueError('broker_request_identity_mismatch')
    claim=folder/'claimed'
    try:
        with claim.open('x'):pass
    except FileExistsError:return  # A repeated scheduler dispatch cannot create a second child.
    process=None
    try:
        import run_safety
        startup=subprocess.STARTUPINFO()
        startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        with (folder/'stdout.log').open('ab') as out,(folder/'stderr.log').open('ab') as error:
            process=subprocess.Popen(payload['argv'],cwd=payload['cwd'],env={**os.environ,**payload['environment']},
                creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP,
                startupinfo=startup,stdin=subprocess.DEVNULL,stdout=out,stderr=error)
            birth=run_safety.process_birth(process.pid)
            atomic_json(folder/'started.json',dict(state='started',token=token,transport=transport,pid=process.pid,birth=birth))
            request.unlink(missing_ok=True)
            # Keep the scheduler job alive for the real worker; cancellation of Codex cannot kill it.
            code=process.wait()
            atomic_json(folder/'exited.json',dict(pid=process.pid,birth=birth,exit_code=code))
    except Exception as exc:
        if not (folder/'started.json').exists():
            atomic_json(folder/'started.json',dict(state='failed',token=token,error=type(exc).__name__+': '+str(exc)))
        if process is not None and process.poll() is None:
            process.terminate();process.wait(timeout=5)
    finally:
        request.unlink(missing_ok=True)
        if transport=='task_scheduler':
            try:
                import powershell_host
                from windows_process import hidden_options
                result=subprocess.run(powershell_host.command(Path(__file__).with_name('task-launch-broker.ps1'),
                    '-Action','Remove','-TaskName',task),capture_output=True,timeout=12,**hidden_options())
                atomic_json(folder/'cleanup.json',dict(task_removed=result.returncode==0))
            except Exception as exc:
                atomic_json(folder/'cleanup.json',dict(task_removed=False,error=str(exc)))
        else:
            atomic_json(folder/'cleanup.json',dict(task_removed=True,transport='shell'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True,type=Path)
    parser.add_argument('--token',required=True)
    parser.add_argument('--transport',choices=('shell','task_scheduler'),default='task_scheduler')
    args=parser.parse_args();request=args.request.resolve()
    try:run(request,args.token,args.transport)
    except BaseException as exc:
        if request.parent.is_dir():
            atomic_json(request.parent/'worker-boot-error.json',dict(
                token=args.token,error=type(exc).__name__+': '+str(exc),
                traceback=traceback.format_exc()[-5000:]))
        raise


if __name__=='__main__':main()
