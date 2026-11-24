"""Only explicit analyzer preferences may be compared to the job's place list."""
import re
import hashlib
import json
from pathlib import Path
from functools import lru_cache


def parse_config(text):
    text = text.strip()
    if not text or text == '关':return []
    values = [v.strip() for v in re.split(r'[、，,；;\n]+', text) if v.strip()]
    if '关' in values:raise ValueError('偏好地点“关”不能与地点混填')
    return list(dict.fromkeys(values))


_PREFERENCE_LABEL = (
    r'偏\s*好\s*(?:工\s*作\s*)?地\s*点(?!\s*筛\s*选)'
)
_ANALYZER_PREFERENCE = re.compile(
    _PREFERENCE_LABEL
    + r'\s*[：:]?\s*'
    r'(?!(?:\s*查\s*看\s*全\s*部|\s*牛\s*人\s*通\s*常|'
    r'\s*求\s*职\s*意\s*愿|\s*沟\s*通\s*Boss|'
    r'\s*受\s*欢\s*迎\s*程\s*度|\s*更\s*喜\s*欢))'
    r'([\s\S]{1,160}?)'
    r'(?=\s*(?:。|；|;|查\s*看\s*全\s*部|牛\s*人\s*通\s*常|'
    r'求\s*职\s*意\s*愿|沟\s*通\s*Boss|受\s*欢\s*迎\s*程\s*度|\Z))'
)


def _ocr_value(value):
    """Join OCR line wraps while preserving boundaries between places."""
    lines = [
        re.sub(r'\s+', '', line)
        for line in str(value or '').replace('\r', '\n').split('\n')
        if line.strip()
    ]
    combined = ''
    for line in lines:
        if combined and re.search(r'[省市区县旗镇]$', combined):
            combined += '、' + line
        else:
            combined += line
    combined = re.sub(
        r'^(?:为|是|包括|包含|可接受|可以接受)[：:]?', '', combined
    )
    return combined.strip(' ：:，,、-—')


def from_resume_ocr(text):
    """Recover the analyzer's explicit preference from saved resume OCR.

    This is a fallback for pages where the analyzer panel is visible in the
    captured resume but not exposed through a stable UIA panel header. Only
    the explicit analyzer label is accepted; no residence or expectation
    location is inferred.
    """
    if not isinstance(text, str) or not text.strip():
        return dict(state='unknown', reason='resume_ocr_unavailable',
                    source='resume_ocr_analyzer_preference')
    values = []
    for match in _ANALYZER_PREFERENCE.finditer(text):
        value = _ocr_value(match.group(1))
        if value:
            values.append(value)
    values = list(dict.fromkeys(values))
    if not values:
        return dict(state='unknown',
                    reason='resume_ocr_analyzer_preference_not_found',
                    source='resume_ocr_analyzer_preference')
    if len(values) != 1:
        return dict(state='unknown',
                    reason='resume_ocr_analyzer_preference_ambiguous',
                    values=values,
                    source='resume_ocr_analyzer_preference')
    return dict(state='present', text=values[0],
                source='resume_ocr_analyzer_preference')


def normalize(value):
    value = re.sub(r'[\s·/\-—]+', '', value)
    return re.sub(r'^(?:浙江|江苏|福建|广东)(?:省)?', '', value)


def variants(value):
    value = normalize(value)
    match = re.fullmatch(r'(.+?市)(.+[市区县])', value)
    if match:
        city, district = match.groups()
        return {city+district, city[:-1]+district, city+district[:-1], city[:-1]+district[:-1]}
    return {value, re.sub(r'[市区县]$', '', value)}


@lru_cache(maxsize=1)
def parent_regions():
    try:
        data = json.loads((Path(__file__).resolve().parents[1]/'references/preferred-location-regions.json').read_text(encoding='utf-8'))
        regions = data['regions']
        for city in data.get('cities', []):regions.setdefault(city, [])
        return regions
    except (OSError, ValueError, KeyError):return {}


def qualify_preferences(preferences):
    regions = parent_regions()
    city_aliases = {alias:city for city in regions for alias in variants(city)}
    combined = []
    for preference in preferences:
        parent = city_aliases.get(normalize(combined[-1])) if combined else None
        children = [child for child in regions.get(parent, []) if variants(preference) & variants(child)]
        if len(children) == 1:
            combined[-1] = parent+children[0]
        elif combined and re.search(r'[区县]$', preference) and re.fullmatch(r'.+市', combined[-1]):
            combined[-1] += preference
        else:combined.append(preference)
    return combined


@lru_cache(maxsize=1)
def administrative_identities():
    result = {}
    for parent, children in parent_regions().items():
        for alias in variants(parent):result.setdefault(alias, set()).add(parent)
        for child in children:
            for alias in variants(child) | variants(parent+child):result.setdefault(alias, set()).add(parent+child)
    return result


def ambiguous(value):
    return len(administrative_identities().get(normalize(value), ())) > 1


@lru_cache(maxsize=1)
def known_places():
    return set(administrative_identities())


def place_match(preference, allowed):
    """Suffix omission is safe; never expand an ancestor to a stated district."""
    preference, allowed = normalize(preference), normalize(allowed)
    identities = administrative_identities()
    source, target = identities.get(preference, set()), identities.get(allowed, set())
    return len(source) == len(target) == 1 and source == target


def resolve_allowed_places(allowed):
    """A job's explicit city entries can qualify its shortened area labels.

    This is target-only qualification. Never infer a candidate's ambiguous
    preference from the locations the recruiter happens to allow.
    """
    identities = administrative_identities()
    cities = {next(iter(owners)) for value in allowed
              if len(owners := identities.get(normalize(value), set())) == 1
              and next(iter(owners)) in parent_regions()}
    resolved = []
    for value in allowed:
        owners = identities.get(normalize(value), set())
        if len(owners) > 1 and re.search(r'[区县市]$', normalize(value)):
            owners = {owner for owner in owners if any(owner == city+normalize(value) for city in cities)}
        if len(owners) != 1:return None
        resolved.append(next(iter(owners)))
    return resolved


def evaluate(config, facts):
    if config.get('preferred_location_filter_enabled', True) is False:
        return dict(state='disabled', reason='岗位偏好地点筛选开关已关闭')
    allowed = config.get('preferred_locations', [])
    if not allowed:return dict(state='disabled', reason='岗位未启用偏好地点筛选')
    observed = facts.get('preferred_location_observation') or {}
    if observed.get('evidence_file'):
        try:
            raw = Path(observed['evidence_file']).read_bytes()
            saved = json.loads(raw.decode('utf-8-sig'))
            if hashlib.sha256(raw).hexdigest() != observed.get('evidence_sha256') or any(saved.get(k) != observed.get(k) for k in ('state','text','source')):
                return dict(state='unknown', reason='偏好地点采集证据已变化，待重新读取')
        except (OSError, ValueError, UnicodeError):
            return dict(state='unknown', reason='偏好地点采集证据不可用，待重新读取')
    state = observed.get('state', 'unknown')
    if state != 'present':
        evidence = facts.get('resume_evidence') or {}
        ocr_path = evidence.get('ocr_text')
        if isinstance(ocr_path, str) and ocr_path:
            try:
                ocr_text = Path(ocr_path).read_text(encoding='utf-8-sig')
            except (OSError, UnicodeError):
                ocr_text = ''
            fallback = from_resume_ocr(ocr_text)
            if fallback.get('state') == 'present':
                fallback['uia_observation'] = observed
                observed = fallback
                state = 'present'
    if state == 'absent':return dict(state='absent', reason='牛人分析器未提供偏好地点，默认通过')
    if state != 'present' or not isinstance(observed.get('text'), str) or not observed['text'].strip():
        return dict(state='absent', reason='未读取到牛人分析器偏好地点，默认通过')
    text = observed['text'].strip()
    allowed = resolve_allowed_places(allowed)
    if allowed is None:
        return dict(state='unknown', reason='岗位地点条目无法唯一识别，请补全所属城市或行政区名称')
    preferences = parse_config(text)
    preferences = qualify_preferences(preferences)
    if any(v in ('全国', '不限', '不限地点', '全国均可') for v in preferences):
        return dict(state='match', reason='候选人明确不限地点', observed=text)
    matched = [p for p in preferences if any(place_match(p, a) for a in allowed)]
    if not matched and any(ambiguous(p) or normalize(p) not in known_places() for p in preferences):
        return dict(state='unknown', observed=text, reason='偏好地点无法唯一解析所属行政区，待复核')
    return dict(state='match' if matched else 'mismatch', observed=text, matched=matched,
                reason='偏好地点匹配' if matched else '偏好地点未命中岗位地点清单')
