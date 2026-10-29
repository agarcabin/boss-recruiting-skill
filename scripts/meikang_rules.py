"""Meikang direct channels, based on the candidate's own observed work history."""
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
    companies = rules.get('meikang_companies',[])
    business_words = rules.get('meikang_direct_business',['海外','出口','销售','业务'])
    # Business terms may be in a different one of the person's own employment entries.
    business = [h for job in jobs for h in positive_hits(job['text'],business_words)]
    company_hits=[]
    for job in jobs:
        for company in companies:
            names=[company]+rules.get('meikang_company_aliases',{}).get(company,[])
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
    products=rules.get('meikang_export_products',['生化','化学发光','质谱'])
    for job in jobs:
        # Require the product and export responsibility in the same observed clause.
        for clause in re.split(r'[。；;\n]',job['text']):
            product=positive_hits(clause,products)
            export=positive_hits(clause,['出口','外贸','export'])
            overseas=positive_hits(job['text'],rules.get('meikang_overseas',[]))
            if product and export and overseas and not re.search(r'留学|旅游|招聘要求|任职要求|客户名单|竞品介绍',clause):
                if 'product_export_overseas' not in channels:
                    channels.append('product_export_overseas')
                evidence.extend(product+export+overseas)
    return dict(channels=channels,evidence=evidence)


def adjusted_score(rules,payload,score):
    years=payload.get('related_experience_years')
    # The observed base score excludes experience; unknown years are not invented.
    if not isinstance(years,(int,float)) or isinstance(years,bool) or years<0:
        return score,0
    penalty=next((entry['deduct'] for entry in rules.get('meikang_experience_penalties',[]) if years<entry['below_years']),0)
    return max(0,score-penalty),penalty
