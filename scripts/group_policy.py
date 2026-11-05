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

def longest_group_hits(value,config):
    import recruiting_rules
    found=[]
    for clause in re.split(r'[。！!？?；;\n，,]|但是|但|不过|然而',value):
        # Source context is allowed by this project; explicit negation still does not match.
        checked=re.sub(r'招聘启事|招聘广告|岗位要求|任职要求|招聘信息|转发|引用','',clause)
        candidates=[]
        for group,key in (('A','a'),('B','b')):
            for word in config.get(key,[]):
                if not recruiting_rules.positive_hits(checked,[word]):continue
                pattern=re.escape(word)
                if word.isascii() and config.get('ascii_boundary',False):
                    pattern=r'(?<![A-Za-z])'+pattern+r'(?![A-Za-z])'
                for match in re.finditer(pattern,clause,re.I):
                    candidates.append(dict(word=word,group=group,quote=clause.strip(),start=match.start(),end=match.end()))
        for hit in candidates:
            if any(other['start']<=hit['start'] and other['end']>=hit['end'] and other['end']-other['start']>hit['end']-hit['start'] for other in candidates):continue
            if not any(h['word'].casefold()==hit['word'].casefold() for h in found):
                found.append({k:hit[k] for k in ('word','group','quote')})
    return [h for h in found if h['group']=='A'],[h for h in found if h['group']=='B']


def evaluate(rules,payload):
    config=rules.get('fulltext_groups')
    if rules.get('version',0)<7 or not isinstance(config,dict):return None
    value=text(payload)
    if config.get('scoring')=='keyword_threshold':
        # Independent opt-in project policy; historical snapshots retain their scoring.
        if config.get('matching')=='longest_allow_context':
            a,b=longest_group_hits(value,config)
        else:
            import recruiting_rules
            a=[dict(h,group='A') for h in recruiting_rules.positive_hits(value,config.get('a',[]))]
            b=[dict(h,group='B') for h in recruiting_rules.positive_hits(value,config.get('b',[]))]
        count=len({h['word'].casefold() for h in a+b})
        both=bool(a and b)
        base=config['both_base'] if both else config['single_score'] if count else 0
        score=base+(config['extra_points']*max(0,count-2) if both else 0) if config.get('single_group_fixed') else base+config['extra_points']*max(0,count-(2 if both else 1))
        complete=payload.get('read_complete') is True
        eligible=complete and bool(count) and score>=config['greeting_min_score']
        trigger='fulltext_ab' if both else 'single_group' if count else 'none'
        return dict(eligible=eligible,score=score,score_before_experience=score,
                    experience_penalty=0,preference_penalty=0,requirements={},
                    trigger=trigger if complete else 'score_incomplete',
                    direct_channels=[trigger] if eligible else [],hits=a+b,method='direct_rule',
                    summary=summary(a,b),groups=dict(A=len(a),B=len(b)),keyword_count=count,
                    scoring_complete=complete)
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
