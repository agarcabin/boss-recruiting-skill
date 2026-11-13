"""Persist isolated BOSS zoom changes and restore without a live model turn."""
import json
from pathlib import Path
import subprocess
import os
import powershell_host
from windows_process import hidden_options


def query(action='Read', percent=100, expected=None):
    args=['-Action',action,'-Percent',str(percent)]
    if expected:args+=['-ExpectedBinding',expected]
    result=subprocess.run(powershell_host.command(Path(__file__).with_name('boss-page-zoom.ps1'),*args),
        capture_output=True,text=True,encoding='utf-8-sig',timeout=15,**hidden_options())
    if result.returncode:raise ValueError('page_zoom_binding_unavailable: '+result.stderr[-600:])
    return json.loads(result.stdout)


class LayoutBlocked(ValueError):
    pass


def prepare(adapter):
    try:
        return _prepare(adapter)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        raise LayoutBlocked(str(exc)) from exc


def _prepare(adapter):
    layout=adapter.query('LayoutState')
    if layout.get('state')!='read':
        raise ValueError('无法确认页面右侧控件是否完整显示，请检查当前BOSS列表页面。')
    if layout.get('fits'):return
    state=query()
    if state.get('state')!='read':
        raise ValueError('无法确认当前BOSS页面的独立缩放控件，请手动调整页面或扩大窗口，确保控件完整显示后继续。')
    original=state['percent'];key='boss_zoom/'+adapter.run
    saved=adapter.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    record=json.loads(saved[0]) if saved else dict(original=original,binding_id=state['binding_id'],
        binding_file=os.environ.get('BOSS_BROWSER_BINDING'))
    for target in (90,80):
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
        if adapter.query('LayoutState').get('fits'):return
    raise ValueError('BOSS页面缩放至80%仍无法完整显示右侧控件，请扩大窗口后继续。')


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
