"""ResumeSpecial direct channels, based on the candidate's own observed work history."""
import re


def work_sections(payload, text):
    structured = payload.get('work_experience')
    if isinstance(structured, list):
        return [dict(company=str(item.get('company','')), text=' '.join(str(item.get(k,'')) for k in ('company','position','duties','description')), source='work_experience')
                for item in structured if isinstance(item,dict) and item.get('company')]
    # Plain OCR must explicitly identify an employment section or an employment statement.
    match = re.search(r'(?:工作经历|工作经验|任职经历|经历概览|职业经历|Work\s+(?:Experience|History)|Employment\s+History)\s*[:：]?([\s\S]*?)(?=教育经历|教育背景|项目经历|求职意向|Education|\Z)', text, re.I)
    if match:
        content = match.group(1)
        blocks = re.split(r'(?=\d{4}[.年/\-]\d{1,2}\s*(?:[-—至~]|to))', content)
        return [dict(company=b,text=b,source='resume_work_section') for b in blocks if b.strip()]
    return [dict(company=line,text=line,source='explicit_employment') for line in text.splitlines()
            if re.search(r'任职于|就职于|曾在|工作于|入职|(?:worked|employed)\s+(?:at|by)|公司\s*[:：]',line,re.I)]


def direct_channels(rules, payload, text, positive_hits):
    jobs = work_sections(payload,text)
    companies = rules.get('resume_special_companies',[])
    business_words = rules.get('resume_special_direct_business',[])
    # Business terms may be in a different one of the person's own employment entries.
    business = [h for job in jobs for h in positive_hits(job['text'],business_words)]
    company_hits=[]
    for job in jobs:
        for company in companies:
            names=[company]+rules.get('resume_special_company_aliases',{}).get(company,[])
            if not any(name in job['company'] for name in names):
                continue
            for line in job['text'].splitlines():
                if not any(name in line for name in names):
                    continue
                if re.search(r'客户|合作伙伴|竞品|供应商|目标公司|服务过|对标|未曾任职|没有任职|未在|非本公司',line):
                    continue
                company_hits.append(dict(company=company,quote=line.strip(),source=job['source']))
                break
    channels=[]
    evidence=[]
    if company_hits and business:
        channels.append('company_business')
        evidence.extend(company_hits+business)
    products=rules.get('resume_special_export_products',[])
    for job in jobs:
        # Require the product and export responsibility in the same observed clause.
        for clause in re.split(r'[。；;\n]',job['text']):
            product=positive_hits(clause,products)
            import project_vault
            export=positive_hits(clause,project_vault.rule_value(rules,'resume_special_export_terms',[]))
            overseas=positive_hits(job['text'],rules.get('resume_special_overseas',[]))
            if product and export and overseas and not re.search(r'留学|旅游|招聘要求|任职要求|客户名单|竞品介绍',clause):
                if 'product_export_overseas' not in channels:
                    channels.append('product_export_overseas')
                evidence.extend(product+export+overseas)
    return dict(channels=channels,evidence=evidence)


def observed_text(payload):
    text=str(payload.get('keyword_text') or '')
    source=(payload.get('resume_evidence') or {}).get('ocr_text')
    if source:
        from pathlib import Path
        try: text+='\n'+Path(source).read_text(encoding='utf-8-sig')
        except (OSError,ValueError): pass
    return text


def salary_minimum(value):
    """A labeled expected salary, RMB/month; never infer salary from raw numbers."""
    if isinstance(value,dict):
        if str(value.get('currency','CNY')).upper() not in ('CNY','RMB','人民币','元'): return None
        if str(value.get('period','month')).lower() not in ('month','monthly','月','月薪','每月'): return None
        low=salary_minimum(value.get('min',value.get('minimum')))
        high=salary_minimum(value.get('max',value.get('maximum')))
        if high is not None and low is not None and high<low:return None
        return low
    if type(value) in (int,float):
        return float(value) if 0<=value<10**8 else None
    text=str(value or '').strip().replace(',','').replace('，','')
    if re.search(r'美元|美金|港币|港元|欧元|USD|HKD|EUR|\$|年薪|年包|/年|每年|万元/年|日薪|时薪|/天|/小时|面议|以上|以下|起|不低于|至少|[<>≥≤]',text,re.I): return None
    m=re.fullmatch(r'(?:人民币|RMB|CNY|￥|¥)?\s*(\d+(?:\.\d+)?)\s*([kKwW千万]?)\s*(?:[-—–~～至]\s*(\d+(?:\.\d+)?)\s*([kKwW千万]?))?\s*(?:元)?\s*(?:/月|月薪|每月|月|/month)?(?:\s*[·×*]\s*\d+薪)?',text,re.I)
    if not m:return None
    scale={'':1,'k':1000,'千':1000,'w':10000,'万':10000}
    low=float(m[1])*scale[(m[2] or m[4] or '').lower()]
    if m[3] and float(m[3])*scale[(m[4] or m[2] or '').lower()]<low:return None
    return low


def preference_penalty(rules,payload):
    if not rules.get('resume_special_preference_penalty'):return 0,[]
    import project_vault
    threshold=project_vault.rule_value(rules,'preference_salary_threshold')
    deduction=project_vault.rule_value(rules,'preference_deduction')
    text=observed_text(payload)
    values=[]
    if payload.get('expected_salary') is not None:values.append(payload['expected_salary'])
    for match in re.finditer(r'(?:^|[\n；;])\s*(?:期望薪资|期望薪酬|期望月薪|期望工资|薪资期望)\s*[:：]?\s*([^\n；;]+)',text):
        values.append(match[1].strip())
    minima=[salary_minimum(value) for value in values]
    known=[value for value in minima if value is not None]
    reasons=[]
    if known and all(value>threshold for value in known):reasons.append('期望人民币月薪最低值>'+str(threshold)+'元')
    status=str(payload.get('job_status') or payload.get('job_search_status') or '')
    clauses=[status]+re.split(r'[\n。；;]',text)
    if any(re.search(r'^\s*(?:(?:求职|当前|工作)状态\s*[:：]?\s*)?在职\s*[-—–·•－:：]?\s*(?:暂)?不考虑',clause) and
           not re.search(r'不是|并非|不属于|招聘要求|任职要求|岗位要求|曾经|此前|过去|原来',clause)
           for clause in clauses):reasons.append('在职不考虑')
    return (deduction if reasons else 0),reasons


def score_details(rules,payload,score):
    years=payload.get('related_experience_years')
    penalty=0
    if type(years) in (int,float) and years>=0:
        penalty=next((entry['deduct'] for entry in rules.get('resume_special_experience_penalties',[]) if years<entry['below_years']),0)
    preference,reasons=preference_penalty(rules,payload)
    return dict(score=max(0,score-penalty-preference),score_before_experience=score,
                experience_penalty=penalty,preference_penalty=preference,preference_penalty_reasons=reasons)


def adjusted_score(rules,payload,score):
    result=score_details(rules,payload,score)
    return result['score'],result['experience_penalty']


def language_requirements(rules,payload,statuses):
    if rules.get('resume_special_language_policy')!='any':return dict(statuses)
    english={'english','英语','language_english'}
    other={'small_language','minor_language','second_language','小语种','other_language'}
    keys=english|other
    result={k:v for k,v in statuses.items() if k not in keys}
    states=[statuses[k] for k in keys if k in statuses]
    skills=payload.get('language_skills',[])
    if not isinstance(skills,list):skills=[]
    if skills:
        # Assessors supply only observed, positive foreign-language skills.
        if any(str(s).lower() not in ('中文','汉语','普通话','chinese','mandarin','') for s in skills):states.append('met')
    if states:result['language']='met' if 'met' in states else 'failed' if all(v=='failed' for v in states) and len(states)>=2 else 'unknown'
    return result
