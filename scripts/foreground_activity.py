"""Publish only live operations that need the user's foreground window."""
import contextlib
import os
import subprocess
from pathlib import Path
import uuid
import run_safety
import powershell_host
from windows_process import hidden_options,decode_output


def activate():
    command=powershell_host.command(Path(__file__).with_name('request-boss-foreground.ps1'))
    try:
        subprocess.run(command,check=True,capture_output=True,timeout=12,
                       env={**os.environ,'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'},**hidden_options())
    except subprocess.CalledProcessError as exc:
        detail=decode_output(exc.stderr or exc.stdout) or str(exc)
        if 'bound_codex_iab_not_foreground' in detail:
            import capture_control
            raise capture_control.CaptureInterrupted('无法将本聊天的BOSS窗口前置，请返回后回复继续。',foreground_required=True) from exc
        import capture_control
        raise capture_control.CaptureInterrupted('无法定位或前置本聊天的BOSS窗口：'+detail[-1800:]) from exc
    except subprocess.TimeoutExpired as exc:
        import capture_control
        raise capture_control.CaptureInterrupted('前置BOSS窗口超时，请返回本聊天后回复继续。',foreground_required=True) from exc


def requirement(command):
    names={Path(str(arg)).name.lower() for arg in command}
    args=[str(arg).lower() for arg in command]
    if 'resume_capture.ps1' in names:
        return '正在采集简历截图'
    if 'capture-card.ps1' in names and '-noimage' not in args:
        return '正在采集卡片截图'
    if names & {'move-click.ps1','idle_mouse.py'}:
        return '正在进行鼠标操作'
    if 'guarded-uia-action.ps1' in names and '-action' in args:
        index=args.index('-action')+1
        if index<len(args) and args[index] in ('key','sendtext'):
            return '正在进行键盘输入'
    return None


@contextlib.contextmanager
def track(db, run_id, command):
    label=requirement(command)
    if not label:
        yield
        return
    db.execute('''CREATE TABLE IF NOT EXISTS foreground_activity(
        token TEXT PRIMARY KEY,run_id TEXT NOT NULL,pid INTEGER NOT NULL,birth REAL NOT NULL,label TEXT NOT NULL)''')
    token=uuid.uuid4().hex
    db.execute('INSERT INTO foreground_activity VALUES (?,?,?,?,?)',
               (token,run_id,os.getpid(),run_safety.process_birth(os.getpid()),label))
    try:
        activate()
        yield
    finally:
        db.execute('DELETE FROM foreground_activity WHERE token=?',(token,))


def current(db,run_id):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='foreground_activity'").fetchone():
        return None
    for row in db.execute('SELECT pid,birth,label FROM foreground_activity WHERE run_id=?',(run_id,)):
        try:
            if abs(run_safety.process_birth(row['pid'])-row['birth'])<.0001:
                return row['label']
        except (OSError,ValueError,ProcessLookupError):
            continue
    return None
