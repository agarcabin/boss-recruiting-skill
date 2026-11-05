"""Shared evidence-based eligibility; keywords never alter the observed score."""
from __future__ import annotations
import copy
import resume_special_rules
import fast_assessment
import json
import re
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / 'references' / 'recruiting-rules.json'

def snapshot(profile: Path, fields: dict, greeting_mode: str | None = None) -> dict:
    metadata_path = profile.parent / 'project.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8-sig')) if metadata_path.is_file() else {}
    policy = fields.get('trigger_policy', metadata.get('trigger_policy', 'legacy'))
    import project_vault
    policy=project_vault.normalize(policy)
    mode = fields.get('evaluation_mode', metadata.get('evaluation_mode', 'resume'))
    greeting_mode = greeting_mode if greeting_mode is not None else fields.get('greeting_mode', metadata.get('greeting_mode', 'single'))
    if greeting_mode not in ('single', 'triple'):
        raise ValueError('invalid_greeting_mode')
    if policy == 'worker' and mode == 'card': mode = 'worker_resume'
    if mode not in ('card', 'resume', 'worker_resume') or policy not in ('legacy','worker','resume_special','domain_advanced','domain_basic','domain_unified'):
        raise ValueError('invalid_evaluation_policy')
    if (policy == 'worker') != (mode in ('card','worker_resume')):
        raise ValueError('mode_policy_mismatch')
    import project_vault
    rules = project_vault.rule_config(CONFIG)
    rules.update(metadata.get('rules',{}))
    group_policies=rules.pop('group_policies',{})
    if policy in group_policies and 'fulltext_groups' not in metadata.get('rules',{}):rules['fulltext_groups']=group_policies[policy]
    rules.update(policy=policy, mode=mode, greeting_mode=greeting_mode,
                 namespace=fields.get('candidate_namespace') or metadata.get('candidate_namespace') or f"{fields['company']}-{fields['position']}",
                 pdf_required=fields.get('pdf_required', 'true').lower() != 'false',
                 browser_target='codex_iab', short_view_wait=True)
    if policy == 'worker':
        rules['worker_policy_version'] = 2
        rules['worker_keywords'] = list(dict.fromkeys(rules.get('worker_keywords', rules.get('worker_advantage', []) + rules.get('worker_expectation', []))))
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
                if re.search(r'没(?:有|做过|干过|接触过)?|未曾?|不(?:曾|做|想|考虑|接受|愿意|会|熟悉|负责|涉及|从事)|无|缺乏|拒绝', prefix):
                    continue
                if re.match(r'(?:工作)?(?:经验)?(?:没有|不足|为零|不具备|无经验)', suffix):
                    continue
                hits.append({'word':word,'quote':clause.strip()})
                break
    return list({(h['word'],h['quote']):h for h in hits}.values())

def evaluate(rules: dict, payload: dict, min_score: int) -> dict:
    import project_vault
    rules=project_vault.normalize(rules)
    payload=project_vault.normalize(payload)
    if is_domain(rules) and payload.get('read_complete') is False:
        return dict(eligible=False,score=0,trigger='score_incomplete',hits=[],requirements={},scoring_complete=False)
    if rules.get('mode')=='worker_resume':
        if worker_v2(rules) and (payload.get('worker_stage') != 'resume' or payload.get('read_complete') is not True):
            return dict(eligible=False, score=0, trigger='resume_evidence_required', hits=[], requirements={})
        return worker_match(rules,payload)
    grouped=domain_group_score(rules,payload,min_score) if is_domain(rules) else None
    if grouped is not None: return grouped
    direct=fast_assessment.evaluate(rules,payload,positive_hits)
    if direct:return direct
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
        coworker=card.get('coworker_contact',{})
        if coworker.get('state')!='absent' or not coworker.get('lookup_completed') or not coworker.get('evidence'):
            return dict(eligible=False,score=0,trigger='coworker_skip' if coworker.get('state')=='present' else 'coworker_unknown',hits=[],requirements={})
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
        try: text = Path(evidence['ocr_text']).read_text(encoding='utf-8-sig')
        except (OSError,ValueError): pass
    if policy == 'resume_special':
        if rules.get('resume_special_companies'):
            base=payload.get('score_before_experience',score)
            adjusted=resume_special_rules.score_details(rules,payload,base)
            score=adjusted['score']
            direct=resume_special_rules.direct_channels(rules,payload,text,positive_hits) if rules.get('version',0)<7 else dict(channels=[],evidence=[])
            year_keys={'experience','years','experience_years','related_experience','industry_years'}
            others=resume_special_rules.language_requirements(rules,payload,{k:v for k,v in statuses.items() if k not in year_keys})
            hard=(payload.get('hard_requirements_without_experience') is True or
                  (payload.get('hard_requirements') is True and not any(v=='failed' for v in others.values())) or
                  (any(statuses.get(k)=='failed' for k in year_keys) and bool(others) and all(v=='met' for v in others.values())))
            if rules.get('resume_special_language_policy')=='any' and others.get('language')=='met':
                hard=hard or (payload.get('hard_requirements_without_language') is True and not any(v=='failed' for v in others.values()))
            if others.get('language')=='failed':hard=False
            a=positive_hits(text,rules['resume_special_industry']);b=positive_hits(text,rules['resume_special_business'])
            hits=a+b if a and b and rules.get('version',0)<7 else []
            eligible=bool(direct['channels']) or (hard and (bool(hits) or score>=min_score))
            return dict(eligible=eligible,**adjusted,
                        trigger='+'.join(direct['channels']) if direct['channels'] else ('both' if hits and score>=min_score else 'keyword' if hits else 'score') if eligible else 'none',
                        direct_channels=direct['channels'],hits=direct['evidence'] if direct['channels'] else hits,requirements=others,hard_requirements_met=hard)
        a = positive_hits(text,rules['resume_special_industry'])
        b = positive_hits(text,rules['resume_special_business'])
        hits = a+b if a and b else []
        hard = payload.get('hard_requirements') is True and not any(v=='failed' for v in statuses.values())
    elif policy.startswith('domain_'):
        current = rules.get('version', 0) >= 3
        required = (('brand_work','domain','independent','vendor','team','travel')
                    if current and policy=='domain_advanced' else
                    ('domain','independent','vendor','team','travel') if policy=='domain_advanced' else ('domain','vendor'))
        statuses = {k:statuses.get(k,'unknown') for k in (*required,'certificate','left_job')}
        hard = (any(statuses[k]!='failed' for k in required)
                if current and policy=='domain_basic' else all(statuses[k]!='failed' for k in required))
        weights = rules[policy+'_weights']
        score = sum(weight for key,weight in weights.items() if statuses.get(key)=='met')
        if not current and policy=='domain_advanced' and statuses['domain']=='unknown' and payload.get('generic_domain_experience') is True:
            score += 20
        hits = [h for h in positive_hits(text,rules['domain']) if re.search(r'经验|经历|项目|实施|部署|调试|交付|负责|工作|做过|从事|运维|开发|集成',h['quote']) and not re.search(r'期望|意向|想做|希望从事',h['quote'])]
        if current:
            # A failed alternative cannot trigger the keyword channel itself.
            hits = [dict(h, requirement='domain') for h in hits if statuses['domain']!='failed']
            if policy=='domain_basic' and statuses['vendor']!='failed':
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
    import project_vault
    return project_vault.normalize(json.loads(run['rule_snapshot'] or '{}')) if 'rule_snapshot' in run.keys() else {}


def run_greeting_mode(run) -> str:
    # Snapshots made before this switch retain their original three-message contract.
    mode = run_rules(run).get('greeting_mode', 'triple')
    if mode not in ('single', 'triple'):
        raise ValueError('invalid_greeting_mode')
    return mode

def from_assessment(row) -> dict:
    return json.loads(row['eligibility_json'] or '{}') if 'eligibility_json' in row.keys() else {}


def worker_v2(rules):
    return rules.get('mode') == 'worker_resume' and rules.get('worker_policy_version') == 2


def worker_match(rules, payload):
    if worker_v2(rules):
        stage = payload.get('worker_stage', 'resume')
        if stage != 'list' and payload.get('read_complete') is False:
            return dict(eligible=False, score=0, trigger='score_incomplete', hits=[], requirements={})
        card = payload.get('card', {})
        text = (payload.get('raw_text') or card.get('readable_text') or '\n'.join(str(card.get(k, '')) for k in ('advantage', 'expectation'))) if stage == 'list' else payload.get('keyword_text', '')
        words = list(dict.fromkeys(rules.get('worker_keywords', rules.get('worker_advantage', []) + rules.get('worker_expectation', []))))
        hits = positive_hits(text, words)
        found = list({h['word']: dict(h, field='card' if stage == 'list' else 'resume') for h in hits}.values())
        return dict(eligible=bool(found), score=min(100, 60 + 2 * (len(found) - 1)) if found else 0,
                    trigger='keyword' if found else 'none', hits=found, requirements={})
    stage=payload.get('worker_stage','resume')
    card=payload.get('card',{})
    text=payload.get('keyword_text','')
    a=positive_hits(card.get('advantage','') if stage=='list' else text,rules.get('worker_advantage',[]))
    b=positive_hits(card.get('expectation','') if stage=='list' else text,rules.get('worker_expectation',[]))
    found=[dict(h,field='advantage') for h in a]+[dict(h,field='expectation') for h in b]
    return dict(eligible=bool(found) and not card.get('already_contacted',False),score=(60 if a else 0)+(40 if b else 0),trigger='keyword' if found else 'none',hits=found,requirements={})

def is_domain(rules):
    return rules.get('policy') in ('domain_basic','domain_advanced','domain_unified')


def domain_group_score(rules,payload,min_score):
    import group_policy
    if payload.get('read_complete') is False:
        return dict(eligible=False,score=0,trigger='score_incomplete',hits=[],requirements={},scoring_complete=False)
    cfg=rules.get('fulltext_groups')
    if not isinstance(cfg,dict): return None
    value=group_policy.text(payload)
    if not value.strip(): return dict(eligible=False,score=0,trigger='unreadable',hits=[],requirements={},scoring_complete=False)
    # Only positive personal evidence contributes to either group or score.
    groups={key:[h['word'] for h in positive_hits(value,cfg.get(key,[]))] for key in ('a','b')}
    clean=dict(rules,fulltext_groups=dict(cfg,a=groups['a'],b=groups['b']))
    result=group_policy.evaluate(clean,payload)
    if result is None: return None
    statuses=payload.get('requirement_states',{})
    required=('brand_work','domain','independent','vendor','team','travel') if rules['policy']=='domain_advanced' else ('domain','vendor')
    hard=not any(statuses.get(k)=='failed' for k in required)
    keyword=bool(result.get('direct_channels'))
    score=result['score']; by_score=score>=min_score
    result.update(eligible=hard and (keyword or by_score),trigger=('both' if keyword and by_score else 'keyword' if keyword else 'score') if hard and (keyword or by_score) else 'none',requirements={k:statuses.get(k,'unknown') for k in required},scoring_complete=True,scoring_rule_version=rules.get('version'))
    return result
