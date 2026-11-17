"""Fast direct-rule assessment after the colleague check, without a full scorecard."""
import json
from pathlib import Path
import resume_special_rules
import hit_summary


def evaluate(rules,payload,positive_hits):
    if rules.get('policy','').startswith('domain_'): return None
    import group_policy
    grouped=group_policy.evaluate(rules,payload)
    if grouped is not None:return grouped
    if rules.get('version',0)>=7 and rules.get('fulltext_groups'):return None
    if rules.get('policy')!='resume_special' or not rules.get('resume_special_companies'):return None
    text=payload.get('keyword_text','')
    source=(payload.get('resume_evidence') or {}).get('ocr_text')
    if source:
        try:text=Path(source).read_text(encoding='utf-8-sig')
        except (OSError,ValueError):pass
    direct=resume_special_rules.direct_channels(rules,payload,text,positive_hits)
    if not direct['channels']:return None
    base=payload.get('score_before_experience',payload.get('overall_score'))
    if type(base) not in (int,float):
        import project_vault
        base=project_vault.rule_value(rules,'resume_special_quick_base_score')
    adjusted=resume_special_rules.score_details(rules,payload,base)
    return dict(eligible=True,**adjusted,
                trigger='+'.join(direct['channels']),direct_channels=direct['channels'],
                hits=direct['evidence'],requirements={},method='direct_rule',
                summary=hit_summary.summary(direct['evidence']))


def fill(payload,result):
    result_payload=dict(payload)
    result_payload.update(overall_score=result['score'],score_before_experience=result['score_before_experience'],
                          decision='greet' if result['eligible'] else 'skip',hard_requirements=payload.get('hard_requirements',False),electronic_resume_enabled=True)
    result_payload.setdefault('pros',result['summary'])
    result_payload.setdefault('cons','快速规则分，记录直接匹配及已知扣分；未逐项评估旧硬条件')
    if result.get('preference_penalty'):
        note='；扣'+str(result['preference_penalty'])+'分：'+'、'.join(result['preference_penalty_reasons'])
        if note not in result_payload['cons']:result_payload['cons']+=note
    result_payload.setdefault('electronic',dict(score=result['score'],evidence=result['summary']))
    return result_payload
