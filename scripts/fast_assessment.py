"""Fast direct-rule assessment after the colleague check, without a full scorecard."""
import json
from pathlib import Path
import meikang_rules


def evaluate(rules,payload,positive_hits):
    if rules.get('policy')!='meikang' or not rules.get('meikang_companies'):return None
    text=payload.get('keyword_text','')
    source=(payload.get('resume_evidence') or {}).get('ocr_text')
    if source:
        try:text=Path(source).read_text(encoding='utf-8-sig')
        except (OSError,ValueError):pass
    direct=meikang_rules.direct_channels(rules,payload,text,positive_hits)
    if not direct['channels']:return None
    base=payload.get('score_before_experience',payload.get('overall_score'))
    if type(base) not in (int,float):base=rules.get('meikang_quick_base_score',80)
    score,penalty=meikang_rules.adjusted_score(rules,payload,base)
    return dict(eligible=True,score=score,score_before_experience=base,experience_penalty=penalty,
                trigger='+'.join(direct['channels']),direct_channels=direct['channels'],
                hits=direct['evidence'],requirements={},method='direct_rule',
                summary='直接规则命中：'+json.dumps(direct['evidence'],ensure_ascii=False))


def fill(payload,result):
    result_payload=dict(payload)
    result_payload.update(overall_score=result['score'],score_before_experience=result['score_before_experience'],
                          decision='greet',hard_requirements=payload.get('hard_requirements',False),electronic_resume_enabled=True)
    result_payload.setdefault('pros',result['summary'])
    result_payload.setdefault('cons','快速规则分，仅记录直接匹配及已知年限；未逐项评估旧硬条件')
    result_payload.setdefault('electronic',dict(score=result['score'],evidence=result['summary']))
    return result_payload
