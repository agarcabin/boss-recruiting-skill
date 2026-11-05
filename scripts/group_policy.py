"""Configurable full-resume grouped matching; project terms come from data."""
import re
from pathlib import Path

def text(payload):
    parts=[]
    for key in ('keyword_text','resume_text','overview_text'):
        value=payload.get(key)
        if isinstance(value,str) and value:parts.append(value)
    source=(payload.get('resume_evidence') or {}).get('ocr_text')
    if source:
        try:parts.append(Path(source).read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):pass
    return '\n'.join(parts)

def hits(value,words,group,ascii_boundary=False):
    result=[];seen=set()
    for word in words:
        canonical=str(word);key=canonical.casefold()
        if key in seen:continue
        seen.add(key);pattern=re.escape(canonical)
        if re.fullmatch(r'\d+\s+年',canonical):
            pattern=r'(?<!\d)'+re.escape(canonical.split()[0])+r'\s*年'
        elif canonical.isascii() and ascii_boundary:
            pattern=r'(?<![A-Za-z])'+pattern+r'(?![A-Za-z])'
        match=re.search(pattern,value,re.I)
        if match:result.append(dict(word=canonical,group=group,quote=value[max(0,match.start()-36):min(len(value),match.end()+55)]))
    return result

def evaluate(rules,payload):
    config=rules.get('fulltext_groups')
    if rules.get('version',0)<7 or not isinstance(config,dict):return None
    value=text(payload)
    a=hits(value,config.get('a',[]),'A',config.get('ascii_boundary',False))
    b=hits(value,config.get('b',[]),'B',config.get('ascii_boundary',False))
    both=bool(a and b);mode=config.get('scoring')
    if mode=='keyword_incremental':
        # Opt-in keyword-only policy; historical fixed/incremental snapshots keep their behavior.
        count=len({h['word'].casefold() for h in a+b})
        base=config['both_base'] if both else config['single_score'] if count else 0
        score=base+config['extra_points']*max(0,count-(2 if both else 1))
        import resume_special_rules
        adjusted=resume_special_rules.score_details(rules,payload,score) if count else dict(
            score=0,score_before_experience=0,experience_penalty=0,preference_penalty=0)
        trigger='fulltext_ab' if both else 'single_group' if count else 'none'
        return dict(eligible=bool(count),**adjusted,requirements={},trigger=trigger,
                    direct_channels=[trigger] if count else [],hits=a+b,method='direct_rule',
                    summary=summary(a,b),groups=dict(A=len(a),B=len(b)),keyword_count=count)
    if mode=='incremental':
        score=min(config.get('cap',100),config['both_base']+config['extra_points']*(len(a)+len(b)-2)) if both else config['single_score'] if a or b else 0
        return dict(eligible=both,score=score,score_before_experience=score,
                    experience_penalty=0,preference_penalty=0,requirements={},
                    trigger='fulltext_ab' if both else 'single_group' if a or b else 'none',
                    direct_channels=['fulltext_ab'] if both else [],hits=a+b,
                    method='direct_rule',summary=summary(a,b),groups=dict(A=len(a),B=len(b)))
    if mode=='fixed' and both:
        import resume_special_rules
        adjusted=resume_special_rules.score_details(rules,payload,config['base'])
        return dict(eligible=True,**adjusted,requirements={},trigger='fulltext_ab',
                    direct_channels=['fulltext_ab'],hits=a+b,method='direct_rule',
                    summary=summary(a,b),groups=dict(A=len(a),B=len(b)))
    return None

def summary(a,b):
    return '命中词：'+'、'.join(h['word'] for h in a+b) if a or b else '未命中关键词'
