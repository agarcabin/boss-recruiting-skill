"""Compact summaries with bounded, non-executing legacy JSON parsing."""
import json
import re
def words(hits):
    result=[]
    def visit(value,depth=0):
        if depth>8:return
        if isinstance(value,dict):
            word=value.get('word') or value.get('company')
            if isinstance(word,str) and word and word not in result:result.append(word)
            for key in ('hits','evidence','direct_evidence','matches'):
                if key in value:visit(value[key],depth+1)
        elif isinstance(value,list):
            for item in value[:1000]:visit(item,depth+1)
    visit(hits)
    return result


def summary(hits):
    values=words(hits)
    return '命中词：'+'、'.join(values) if values else '未命中关键词'


def legacy(value):
    text=str(value or '').strip()
    if not (re.match(r'^直接规则命中\s*[:：]',text) or text.startswith(('[{','{"'))):return None
    raw=re.sub(r'^直接规则命中\s*[:：]\s*','',text)
    if len(raw)>200000:return []
    try:return words(json.loads(raw))
    except (ValueError,TypeError,RecursionError):return []

def display(value,hits=None):
    values=words(hits);old=legacy(value)
    if old is not None:
        values=values or old
        return '命中词：'+'、'.join(values) if values else '规则命中，历史证据待解析'
    text=str(value or '')
    if values and text.strip().startswith('命中词：'):return '命中词：'+'、'.join(values)
    return text

def visible(hits,*fallback):
    if words(hits):return summary(hits)
    for value in fallback:
        if value:return display(value)
    return ''


def grouped(hits):
    groups={key:[] for key in ('A','B')}
    for hit in hits if isinstance(hits,list) else []:
        if not isinstance(hit,dict):continue
        group=str(hit.get('group','')).upper()
        word=hit.get('word') or hit.get('company')
        if group in groups and isinstance(word,str) and word and word not in groups[group]:groups[group].append(word)
    if any(groups.values()):
        return '；'.join(key+'组：'+('、'.join(values) if values else '未命中') for key,values in groups.items())
    return '、'.join(words(hits)) or '未命中'
