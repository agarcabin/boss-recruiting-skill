"""Persist isolated BOSS zoom changes and restore without a live model turn."""
import json
from pathlib import Path
import subprocess
import os
import powershell_host
from windows_process import hidden_options,decode_output


def query(action='Read', percent=100, expected=None):
    args=['-Action',action,'-Percent',str(percent)]
    if expected:args+=['-ExpectedBinding',expected]
    result=subprocess.run(powershell_host.command(Path(__file__).with_name('boss-page-zoom.ps1'),*args),
        capture_output=True,timeout=45,**hidden_options())
    if result.returncode:raise ValueError('page_zoom_binding_unavailable: '+decode_output(result.stderr)[-600:])
    payload=json.loads(decode_output(result.stdout))
    if payload.get('menu_closed') is False:
        raise LayoutBlocked('缩放菜单未能关闭，已暂停；请关闭当前页面的缩放菜单后继续。')
    return payload


class LayoutBlocked(ValueError):
    pass


def prepare(adapter):
    try:
        return _prepare(adapter)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        raise LayoutBlocked(str(exc)) from exc


ZOOM_LEVELS = (90, 80, 70, 60, 50)


def ensure_sidebar_hidden(chat_title):
    if not chat_title:
        raise LayoutBlocked("缺少当前聊天标题，无法核验侧边栏")
    result = subprocess.run(powershell_host.command(Path(__file__).with_name("collapse-chat-sidebar.ps1"), "-ChatTitle", chat_title), capture_output=True, timeout=30, **hidden_options())
    if result.returncode:
        raise LayoutBlocked("隐藏侧边栏失败：" + decode_output(result.stderr)[-600:])
    receipt = json.loads(decode_output(result.stdout))
    if receipt.get("state") != "collapsed" or receipt.get("chat_title") != chat_title:
        raise LayoutBlocked("侧边栏隐藏状态未确认")
    return receipt


def read_layout(adapter):
    layout=adapter.query('LayoutState')
    if layout.get('state')!='read':
        reason=layout.get('reason','unknown')
        messages={
            'filter_control_not_found':'未识别到筛选控件',
            'filter_control_not_unique':'识别到多个筛选控件，无法确定当前控件',
        }
        raise LayoutBlocked('页面控件识别失败：'+messages.get(reason,reason)+'；尚未判断页面是否被截断。')
    return layout


def _prepare(adapter):
    binding = json.loads(Path(os.environ["BOSS_BROWSER_BINDING"]).read_text(encoding="utf-8-sig"))
    receipt = ensure_sidebar_hidden(binding.get("chat_title"))
    adapter.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", ("sidebar_check/"+adapter.run, json.dumps(receipt)))
    layout=read_layout(adapter)
    if layout.get('fits'):return
    state=query()
    if state.get('state')!='read':
        raise ValueError('无法确认当前BOSS页面的独立缩放控件，请手动调整页面或扩大窗口，确保控件完整显示后继续。')
    original=state['percent'];key='boss_zoom/'+adapter.run
    saved=adapter.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    record=json.loads(saved[0]) if saved else dict(original=original,binding_id=state['binding_id'],
        binding_file=os.environ.get('BOSS_BROWSER_BINDING'))
    for target in ZOOM_LEVELS:
        if target>=original:continue
        # Persist restoration information before dispatch, including a crash
        # between a successful zoom and recording its response.
        record.update(last=target,restored=False)
        adapter.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(record)))
        changed=query('Set',target,record['binding_id'])
        if isinstance(changed.get('percent'),(float,int)):
            record['last']=changed['percent']
            adapter.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(record)))
        if changed.get('state')!='read' or abs(changed['percent']-target)>.1:
            raise ValueError('无法确认BOSS页面缩放成功，已暂停，未使用旧坐标继续操作。')
        if read_layout(adapter).get('fits'):return
    raise ValueError('BOSS页面已按90%、80%、70%、60%、50%逐级检查（跳过不低于当前比例的档位），仍无法完整显示右侧控件，请扩大窗口后继续。')


def restore(db, run):
    key='boss_zoom/'+run
    row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    if not row:return 'unchanged'
    data=json.loads(row[0])
    if data.get('restored'):return 'restored'
    previous=os.environ.get('BOSS_BROWSER_BINDING')
    if data.get('binding_file'):os.environ['BOSS_BROWSER_BINDING']=data['binding_file']
    try:
        current=query(expected=data['binding_id'])
        if current.get('state')!='read':raise ValueError('zoom_restore_unavailable')
        if abs(current['percent']-data['last'])>.1:
            data.update(restored=True,result='user_changed_zoom_preserved')
        else:
            result=query('Set',data['original'],data['binding_id'])
            if result.get('state')!='read' or abs(result['percent']-data['original'])>.1:raise ValueError('zoom_restore_unconfirmed')
            data.update(restored=True,result='restored')
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        data.update(result='restore_pending',error=str(exc))
    finally:
        if previous is None:os.environ.pop('BOSS_BROWSER_BINDING',None)
        else:os.environ['BOSS_BROWSER_BINDING']=previous
    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(data)))
    return data['result']
