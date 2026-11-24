"""Persist the operator's thirty-second page adjustment window."""
import json
import math
import time

MESSAGE = '🔴等待 30 秒，可以手动切换岗位和筛选数据，回复“继续”可以跳过等待。'


def read(db, run):
    row = db.execute('SELECT value FROM settings WHERE key=?', ('notice_wait/'+run,)).fetchone()
    return json.loads(row[0]) if row else {}


def write(db, run, data):
    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',
               ('notice_wait/'+run, json.dumps(data, ensure_ascii=False)))


def prepare(db, run, notice_id):
    current = read(db, run)
    if current.get('notice_id') != notice_id:
        write(db, run, dict(notice_id=notice_id, active=True, deadline=None, skipped=False))


def remaining(db, run, notice_id, now=None):
    current = read(db, run)
    if current.get('notice_id') != notice_id:
        raise ValueError('notice_wait_id_mismatch')
    now = time.time() if now is None else now
    if current.get('deadline') is None:
        current['deadline'] = now + 30
        write(db, run, current)
    seconds = 0 if current.get('skipped') else max(0, math.ceil(current['deadline']-now))
    if seconds == 0:
        current['active'] = False
        write(db, run, current)
    return seconds


def skip(db, run):
    current = read(db, run)
    if not current.get('active'):
        return False
    current['skipped'] = True
    write(db, run, current)
    return True
