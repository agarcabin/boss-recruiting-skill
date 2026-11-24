"""Same-user task broker for hosts that forbid CREATE_BREAKAWAY_FROM_JOB."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import powershell_host
import run_safety
from windows_process import hidden_options,decode_output


def atomic_json(path,payload):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    os.replace(temporary,path)


class BrokerProcess:
    """Own the exact child process handle, never the scheduler's engine PID."""
    def __init__(self,pid,birth,args):
        self.pid=int(pid);self.args=args;self.returncode=None
        kernel=self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetProcessTimes.argtypes=(wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p)
        kernel.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
        kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD)
        kernel.TerminateProcess.argtypes=(wintypes.HANDLE,wintypes.UINT)
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
        self.handle=kernel.OpenProcess(0x1000|0x100000|1,False,self.pid)
        if not self.handle:raise OSError(ctypes.get_last_error(),'broker_child_open_failed')
        times=[ctypes.c_uint64() for _ in range(4)]
        if not kernel.GetProcessTimes(self.handle,*[ctypes.byref(value) for value in times]):
            self.close();raise OSError('broker_child_birth_unavailable')
        if abs(times[0].value/10000000-float(birth))>.0001:
            self.close();raise ValueError('broker_child_pid_reused')
    def poll(self):
        if self.returncode is not None:return self.returncode
        if self.kernel.WaitForSingleObject(self.handle,0)==0:
            code=wintypes.DWORD()
            if not self.kernel.GetExitCodeProcess(self.handle,ctypes.byref(code)):raise OSError('broker_child_exit_unavailable')
            self.returncode=code.value
        return self.returncode
    def wait(self,timeout=None):
        milliseconds=0xffffffff if timeout is None else max(0,int(timeout*1000))
        if self.kernel.WaitForSingleObject(self.handle,milliseconds)==0x102:
            raise subprocess.TimeoutExpired(self.args,timeout)
        return self.poll()
    def terminate(self):
        if self.poll() is None and not self.kernel.TerminateProcess(self.handle,1):
            raise OSError(ctypes.get_last_error(),'broker_child_terminate_failed')
    kill=terminate
    def close(self):
        if getattr(self,'handle',None):self.kernel.CloseHandle(self.handle);self.handle=None
    def __del__(self):self.close()


def launch(command,timeout=45):
    """A rejected CreateProcess has created no child; only that error may use this broker."""
    expected=Path(sys.executable).with_name('pythonw.exe').resolve()
    if not command or Path(command[0]).resolve()!=expected:
        raise ValueError('broker_requires_bundled_pythonw')
    token=uuid.uuid4().hex
    launch_root=(Path(os.environ['BOSS_LAUNCH_DIR']) if os.environ.get('BOSS_LAUNCH_DIR')
                 else Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData'/'Local')/'Codex'/'recruiting-greetings'/'launches')
    root=launch_root/token
    root.mkdir(parents=True,exist_ok=False)
    request=root/'request.json';receipt=root/'started.json'
    task='CodexRecruitingLaunch-'+token
    environment={key:value for key,value in os.environ.items() if key.startswith('BOSS_') or key in (
        'PATH','PYTHONUTF8','PYTHONIOENCODING','PYTHONPATH','APPDATA','LOCALAPPDATA','USERPROFILE',
        'TEMP','TMP','CODEX_HOME')}
    atomic_json(request,dict(token=token,task=task,transport='shell',argv=list(map(str,command)),
                             cwd=str(Path.cwd()),environment=environment))
    broker=Path(__file__).with_name('shell-launch-broker.ps1')
    result=subprocess.run(powershell_host.command(broker,'-PythonPath',expected,
        '-Bootstrap',Path(__file__).with_name('task_launch_worker.py'),'-Request',request,'-Token',token),
        capture_output=True,timeout=timeout,**hidden_options())
    if result.returncode:
        # ShellExecute failed before dispatch; the scheduler is the bounded fallback.
        atomic_json(request,dict(token=token,task=task,transport='task_scheduler',argv=list(map(str,command)),
                                 cwd=str(Path.cwd()),environment=environment))
        result=subprocess.run(powershell_host.command(Path(__file__).with_name('task-launch-broker.ps1'),
            '-TaskName',task,'-PythonPath',expected,'-Bootstrap',Path(__file__).with_name('task_launch_worker.py'),
            '-Request',request,'-Token',token),capture_output=True,timeout=timeout,**hidden_options())
        if result.returncode:
            request.unlink(missing_ok=True)
            raise RuntimeError('Windows 同用户后台启动通道失败：'+decode_output(result.stderr)[-1200:])
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if receipt.exists():
            info=json.loads(receipt.read_text(encoding='utf-8'))
            if info.get('token')!=token:raise ValueError('broker_receipt_identity_mismatch')
            if info.get('state')!='started':raise RuntimeError('后台进程启动失败：'+str(info.get('error','unknown')))
            process=BrokerProcess(info['pid'],info['birth'],command)
            process.transport=info.get('transport','unknown');process.launch_folder=root
            return process
        time.sleep(.05)
    # No second launch: the broker might have started the child before a delayed receipt.
    raise RuntimeError('后台启动回执超时，未重复启动；诊断目录：'+str(root))
