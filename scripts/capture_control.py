"""Distinguish interrupted acquisition from failed resume files."""
import ledger
import json
from windows_process import decode_output


class CaptureInterrupted(RuntimeError):
    def __init__(self,message,foreground_required=False,normal=None):
        super().__init__(message)
        self.foreground_required=foreground_required
        self.normal=bool(foreground_required) if normal is None else bool(normal)


def require_running(db, run_id, generation):
    run = ledger.run_row(db, run_id)
    state = ledger.control_state(db, run_id)
    if run['stop_reason'] or state != 'running':
        raise CaptureInterrupted('简历采集已随任务暂停或结束而中断。',normal=True)
    if run['generation'] != generation:
        raise CaptureInterrupted('简历采集所属运行代次已改变，请续接当前任务。',normal=True)
    return run


def raise_if_interrupted(db, run_id, generation, error):
    output=decode_output(getattr(error,'stderr',None) or getattr(error,'stdout',None))
    import resume_diagnostics
    if resume_diagnostics.is_program_bug(str(error)+output):
        return  # A concurrent manual stop must not hide a real program exception.
    require_running(db, run_id, generation)
    for line in reversed(output.splitlines()):
        try:message=json.loads(line)
        except (ValueError,TypeError):continue
        if isinstance(message,dict) and message.get('state') in ('helper_interrupted','helper_cancelled'):
            raise CaptureInterrupted(str(message.get('reason') or '简历采集子任务已取消。'),
                                     foreground_required=message.get('foreground_required') is True,
                                     normal=message.get('normal',True if message['state']=='helper_cancelled' else None)) from error
    detail = str(error) + output
    if 'bound_codex_iab_not_foreground' in detail:
        raise CaptureInterrupted('当前操作需要键盘或鼠标焦点；请手动返回 BOSS 窗口后回复继续。',foreground_required=True) from error
    if any(code in detail for code in ('capture_window_not_visible','capture_region_occluded',
            'capture_region_outside_monitor','capture_region_outside_window','capture_window_not_in_visible_zorder')):
        raise CaptureInterrupted('简历截图区域被遮挡或不可见，采集已暂停；请露出窗口或切到副屏后回复继续。',normal=True) from error
    if 'resume_capture_geometry_changed' in detail:
        raise CaptureInterrupted('截图区域已改变，采集已暂停；保持窗口布局后回复继续。',normal=True) from error
    if 'helper_cancelled' in detail:
        raise CaptureInterrupted('简历采集子任务已取消，尚未完成读取。',normal=True) from error
