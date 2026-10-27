"""Shared evidence-based eligibility; keywords never alter the observed score."""
from __future__ import annotations
import copy
import json
import re
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / 'references' / 'recruiting-rules.json'

def snapshot(profile: Path, fields: dict) -> dict:
    metadata_path = profile.parent / 'project.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8-sig')) if metadata_path.is_file() else {}
    policy = fields.get('trigger_policy', metadata.get('trigger_policy', 'legacy'))
    mode = fields.get('evaluation_mode', metadata.get('evaluation_mode', 'resume'))
    if mode not in ('card', 'resume') or policy not in ('legacy','worker','meikang','agv_advanced','agv_basic'):
        raise ValueError('invalid_evaluation_policy')
    if (policy == 'worker') != (mode == 'card'):
        raise ValueError('mode_policy_mismatch')
    rules = json.loads(CONFIG.read_text(encoding='utf-8'))
    rules.update(policy=policy, mode=mode,
                 namespace=fields.get('candidate_namespace') or metadata.get('candidate_namespace') or f"{fields['company']}-{fields['position']}",
                 pdf_required=fields.get('pdf_required', 'true').lower() != 'false')
    return rules

def positive_hits(text: str, words: list[str]) -> list[dict]:
    hits = []
    for clause in re.split(r'[。！!？?；;\n，,]|但是|但|不过|然而', str(text or '')):
        if re.search(r'招聘启事|招聘广告|岗位要求|任职要求|招聘信息|转发|引用', clause):
            continue
        for word in words:
            pattern = re.escape(word)
            if word.isascii():
                pattern = r'(?<![A-Za-z])' + pattern + r'(?![A-Za-z])'
            for match in re.finditer(pattern, clause, re.I):
                prefix = clause[max(0,match.start()-14):match.start()]
                suffix = clause[match.end():match.end()+8]
                if re.search(r'(?i)\b(?:no|not|never|without)\b',prefix):
                    continue
                if re.search(r'没(?:有|做过|干过|接触过)?|未曾?|不(?:曾|做|想|考虑|接受|愿意|会|熟悉)|无|缺乏|拒绝', prefix):
                    continue
                if re.match(r'(?:工作)?(?:经验)?(?:没有|不足|为零|不具备|无经验)', suffix):
                    continue
                hits.append({'word':word,'quote':clause.strip()})
                break
    return list({(h['word'],h['quote']):h for h in hits}.values())

def evaluate(rules: dict, payload: dict, min_score: int) -> dict:
    policy = rules.get('policy','legacy')
    score = payload.get('overall_score',0)
    hits = []
    statuses = payload.get('requirement_states', {})
    if not isinstance(statuses,dict) or any(v not in ('met','unknown','failed') for v in statuses.values()):
        raise ValueError('requirement_states_invalid')
    if policy == 'worker':
        card = payload.get('card',{})
        if not isinstance(card,dict):
            raise ValueError('card_fields_required')
        a = positive_hits(card.get('advantage',''),rules['worker_advantage'])
        e = positive_hits(card.get('expectation',''),rules['worker_expectation'])
        hits = [dict(h,field='advantage') for h in a] + [dict(h,field='expectation') for h in e]
        score = (60 if a else 0)+(40 if e else 0)
        eligible = bool(hits) and not card.get('already_contacted',False)
        return dict(eligible=eligible,score=score,trigger='keyword' if eligible else 'none',hits=hits,requirements={})
    text = payload.get('keyword_text','')
    # Actual locally archived OCR is authoritative, never an invented keyword list.
    evidence = payload.get('resume_evidence') or {}
    if evidence.get('ocr_text'):
        text = Path(evidence['ocr_text']).read_text(encoding='utf-8-sig')
    if policy == 'meikang':
        a = positive_hits(text,rules['meikang_industry'])
        b = positive_hits(text,rules['meikang_business'])
        hits = a+b if a and b else []
        hard = payload.get('hard_requirements') is True and not any(v=='failed' for v in statuses.values())
    elif policy.startswith('agv_'):
        current = rules.get('version', 0) >= 3
        required = (('brand_work','agv','independent','vendor','team','travel')
                    if current and policy=='agv_advanced' else
                    ('agv','independent','vendor','team','travel') if policy=='agv_advanced' else ('agv','vendor'))
        statuses = {k:statuses.get(k,'unknown') for k in (*required,'certificate','left_job')}
        hard = (any(statuses[k]!='failed' for k in required)
                if current and policy=='agv_basic' else all(statuses[k]!='failed' for k in required))
        weights = rules[policy+'_weights']
        score = sum(weight for key,weight in weights.items() if statuses.get(key)=='met')
        if not current and policy=='agv_advanced' and statuses['agv']=='unknown' and payload.get('generic_agv_experience') is True:
            score += 20
        hits = [h for h in positive_hits(text,rules['agv']) if re.search(r'经验|经历|项目|实施|部署|调试|交付|负责|工作|做过|从事|运维|开发|集成',h['quote']) and not re.search(r'期望|意向|想做|希望从事',h['quote'])]
        if current:
            # A failed alternative cannot trigger the keyword channel itself.
            hits = [dict(h, requirement='agv') for h in hits if statuses['agv']!='failed']
            if policy=='agv_basic' and statuses['vendor']!='failed':
                hits += [dict(h, requirement='vendor') for h in positive_hits(text,rules['vendor'])
                         if positive_hits(h['quote'],rules['vendor_implementation'])
                         and not re.search(r'期望|意向|想做|希望从事',h['quote'])]
    else:
        hard = payload.get('hard_requirements') is True or payload.get('hard_requirement_override') is True
    by_keyword = bool(hits)
    by_score = score >= min_score
    eligible = hard and (by_keyword or by_score)
    return dict(eligible=eligible,score=score,trigger=('both' if by_keyword and by_score else 'keyword' if by_keyword else 'score') if eligible else 'none',hits=hits,requirements=statuses)

def run_rules(run) -> dict:
    return json.loads(run['rule_snapshot'] or '{}') if 'rule_snapshot' in run.keys() else {}

def from_assessment(row) -> dict:
    return json.loads(row['eligibility_json'] or '{}') if 'eligibility_json' in row.keys() else {}
