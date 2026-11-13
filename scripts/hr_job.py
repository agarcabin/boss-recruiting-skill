"""Compile HR Markdown into detached run JSON; never execute document text."""
import hashlib
import json
from pathlib import Path
import re


class ConfigError(ValueError):
    pass


HEADINGS = ('一、列表卡片', '二、电子简历', '三、其他配置')
SETTINGS = ('单简历查看时间（为期望平均值）', '查看十人后休息', '同事几天以上可打招呼', '三句招呼（关闭为单句）')


def is_hr(text):
    return not text.lstrip('\ufeff').startswith('---') and bool(re.search(r'^# +\S', text, re.M))


def clean(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    lines = []
    for line in text.splitlines():
        line = re.sub(r'^\s*(?:>\s*)?(?:[-*]\s+)?', '', line).strip()
        if line and not line.startswith(('注释：', '注释:', '说明：', '说明:')):
            lines.append(line)
    return '\n'.join(lines)


def words(text):
    from misjudgment_review import unmark
    text = unmark(text)
    result = [w.strip() for w in re.split(r'[、，,；;\n]+', text) if w.strip()]
    if any(w in ('xx', 'XX', '…', '...', '{{关键词}}') for w in result):
        raise ConfigError('请把示例词替换为实际词语，或直接留空')
    return list(dict.fromkeys(result))


def positive(text, grouped):
    groups, plain, formula = {}, [], None
    for line in clean(text).splitlines():
        rule = re.fullmatch(r'(?:匹配方式|组合)\s*[：:]\s*(.*)', line)
        label = re.fullmatch(r'([A-Za-z][0-9]*)(?:组|词库)?\s*[：:]\s*(.*)', line)
        if rule:
            if formula is not None:
                raise ConfigError('匹配方式不能重复')
            formula = rule[1]
        elif label:
            key = label[1].upper()
            if key in groups or not words(label[2]):
                raise ConfigError('分组词库不能重名或留空')
            groups[key] = words(label[2])
        else:
            plain.append(line)
    if groups:
        if plain or not grouped:
            raise ConfigError('列表初筛只填词语；简历分组词库请每组单独一行')
    else:
        values = words('\n'.join(plain))
        groups = {'A': values} if values else {}
    if formula is None:
        terms = [[key] for key in groups]
    else:
        formula = re.sub(r'\s+', '', formula).upper().replace('＋', '+').replace('／', '/')
        terms = [part.split('/') for part in formula.split('+')]
        if any(not re.fullmatch(r'[A-Z][0-9]*', key) or key not in groups for term in terms for key in term):
            raise ConfigError('匹配方式请使用已填写的词库名称以及 +、/，例如 A1+B1/B2')
        if set(key for term in terms for key in term) != set(groups):
            raise ConfigError('匹配方式须包含所有已填写词库')
    return dict(groups=groups, terms=terms)


def duration(value, label, days=False):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(秒|分钟|分|天)', value)
    if not match or (days != (match[2] == '天')):
        raise ConfigError(f'{label}请填写非负数字和正确单位')
    number = float(match[1]) * (60 if match[2] in ('分钟', '分') else 1)
    if number > (3650 if days else 86400):
        raise ConfigError(f'{label}数值过大，请检查单位')
    return number


def parse(text):
    if len(text.encode('utf-8')) > 1024*1024:
        raise ConfigError('岗位文件超过1MiB')
    titles = re.findall(r'^# +(.+?)\s*$', text, re.M)
    if len(titles) != 1 or '{{' in titles[0]:
        raise ConfigError('请在第一行填写实际岗位名称')
    sections, current, sub = {}, None, None
    for line in text.splitlines():
        heading = re.fullmatch(r'## +(.+?)\s*', line)
        item = re.fullmatch(r'### +([123])\.\s*(初筛词库|减分词库|误判复诊)\s*', line)
        if heading:
            current, sub = heading[1], None
            if current not in HEADINGS or current in sections:
                raise ConfigError('请保留模板的三个板块，且不要重复')
            sections[current] = {}
        elif item:
            if current not in HEADINGS[:2] or not ((item[1], item[2]) in (('1', '初筛词库'), ('2', '减分词库')) or (current == HEADINGS[1] and (item[1], item[2]) == ('3', '误判复诊'))):
                raise ConfigError('词库小标题与模板不一致')
            sub = item[2]
            if sub in sections[current]:
                raise ConfigError('词库小标题不能重复')
            sections[current][sub] = []
        elif line.startswith('###'):
            raise ConfigError('请保留模板中的词库小标题')
        elif current:
            sections[current].setdefault(sub, []).append(line)
    if set(sections) != set(HEADINGS):
        raise ConfigError('请保留列表卡片、电子简历、其他配置三个板块')
    config = dict(format='hr-job/v1', position=titles[0])
    for title, stage in zip(HEADINGS[:2], ('list', 'resume')):
        part = sections[title]
        if not {'初筛词库', '减分词库'} <= set(part) or clean('\n'.join(part.get(None, []))):
            raise ConfigError('请在对应初筛词库和减分词库小标题下填写词语')
        config[stage] = positive('\n'.join(part['初筛词库']), stage == 'resume')
        config[stage]['negative'] = words(clean('\n'.join(part['减分词库'])))
        if stage == 'resume':
            review = clean('\n'.join(part.get('误判复诊', []))) or '开'
            if review not in ('开', '关'):
                raise ConfigError('误判复诊请填写“开”或“关”')
            config[stage]['misjudgment_review'] = review == '开'
    settings = {}
    for line in clean('\n'.join(sections[HEADINGS[2]].get(None, []))).splitlines():
        match = re.fullmatch(r'(.+?)\s*[：:]\s*(.*)', line)
        if match and match[1] == '单简历查看时间（不足时补足）':
            match = re.fullmatch(r'(.+?)\s*[：:]\s*(.*)', SETTINGS[0] + '：' + match[2])
        if not match or match[1] not in SETTINGS or match[1] in settings:
            raise ConfigError('其他配置名称与模板不一致，或重复填写')
        settings[match[1]] = match[2]
    settings.setdefault(SETTINGS[0], '30 秒')
    if set(settings) != set(SETTINGS):
        raise ConfigError('请填写其他配置中的四项设置')
    if settings[SETTINGS[3]] not in ('开', '关'):
        raise ConfigError('三句招呼请填写“开”或“关”')
    config.update(average_seconds=duration(settings[SETTINGS[0]], SETTINGS[0]),
                  rest_seconds=duration(settings[SETTINGS[1]], SETTINGS[1]),
                  coworker_days=duration(settings[SETTINGS[2]], SETTINGS[2], True),
                  greeting_mode='triple' if settings[SETTINGS[3]] == '开' else 'single')
    return config


def metadata(profile):
    profile = Path(profile)
    sidecar = profile.with_name('.'+profile.stem+'.project.json')
    path = sidecar if sidecar.is_file() else profile.parent/'project.json'
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}


def fields(profile, text=None):
    profile = Path(profile)
    config = parse(text if text is not None else profile.read_text(encoding='utf-8-sig'))
    meta = metadata(profile)
    company = meta.get('company') or re.sub(r'^\d+\s+', '', profile.parent.name)
    identity = 'project-'+hashlib.sha256(f"{company}\0{config['position']}".encode()).hexdigest()[:16]
    return dict(schema='boss-greeting-profile/v1', company=company, position=config['position'],
                candidate_namespace=meta.get('candidate_namespace') or meta.get('project_id') or identity,
                evaluation_mode='resume', trigger_policy='hr_job', greeting_mode=config['greeting_mode'], approval='approved')


def snapshot(profile):
    text = Path(profile).read_text(encoding='utf-8-sig')
    config = parse(text)
    return dict(hr_job_config=config,
                hr_config_sha256=hashlib.sha256(json.dumps(config, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                namespace=fields(profile, text)['candidate_namespace'], policy='hr_job', mode='resume',
                greeting_mode=config['greeting_mode'], browser_target='codex_iab', pdf_required=False,
                list_prefilter=True, ai_pros_cons=True, short_view_wait=True, coworker_skip_wait_exempt=True,
                release_policy=1410, view_wait_policy=2, coworker_notice_policy=1,
                csv_reports=True, ocr_highlights=True, page_layout_policy=1)


def match(config, text, grouped):
    from recruiting_rules import positive_hits
    hits = [dict(h, group=key) for key, values in config['groups'].items() for h in positive_hits(text, values)]
    negative = positive_hits(text, config['negative'])
    found = {h['group'] for h in hits}
    qualified = all(any(key in found for key in term) for term in config['terms']) if grouped else bool(found)
    if not config['groups']:
        qualified = True
    return dict(eligible=qualified and not negative, hits=hits, negative_hits=negative)


def list_assessment(rules, payload):
    config = rules['hr_job_config']['list']
    text = payload.get('raw_text') or (payload.get('card') or {}).get('readable_text') or ''
    result = match(config, text, False)
    readable = bool(text.strip()) or not (config['groups'] or config['negative'])
    return dict(result, configured=True, readable=readable, eligible=readable and result['eligible'])


def assessment(rules, payload):
    if payload.get('evaluation_stage') == 'list':
        result = list_assessment(rules, payload)
        return dict(result, eligible=False, score=0, requirements={}, trigger='list_prefilter')
    text = payload.get('keyword_text') or ''
    source = (payload.get('resume_evidence') or {}).get('ocr_text')
    if source:
        try:
            text = Path(source).read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            text = ''
    config = rules['hr_job_config']['resume']
    result = match(config, text, True)
    complete = payload.get('read_complete') is True and bool(text.strip())
    count = len({h['word'].casefold() for h in result['hits']})
    multi = len({h['group'] for h in result['hits']}) >= 2
    score = min(100, 70+max(0, count-2)*2 if multi else 60+max(0, count-1)*2) if count else 0
    summary = ('命中跳过词：'+'、'.join(h['word'] for h in result['negative_hits']) if result['negative_hits'] else
               '命中词：'+'、'.join(h['word'] for h in result['hits']) if count else
               '未设置简历初筛词库' if not config['groups'] else '未满足简历词库条件')
    return dict(result, eligible=complete and result['eligible'], score=score, scoring_complete=complete,
                requirements={}, trigger='hr_job' if complete else 'score_incomplete',
                score_before_experience=score, experience_penalty=0, preference_penalty=0,
                direct_channels=['hr_job'] if complete and result['eligible'] else [], method='direct_rule', summary=summary)
