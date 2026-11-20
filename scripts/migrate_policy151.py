"""Preview the one-time HR document migration; installation commits the changes."""
import hashlib
import re
from pathlib import Path
import hr_job

VETO_NOTE = '在命中筛选词库后启动否决词库的二筛，只要卡片中出现其中任意词汇，就会跳过该卡片，不会点开电子简历。填空为不启动否决词库'


def format_document(text):
    """Normalize HR-facing notes and district display without changing rules."""
    lines = []
    in_locations = False
    has_location_switch = bool(re.search(r'(?m)^(?:##\s*)?偏好地点筛选\s*[：:]\s*[开关]\s*$', text))
    for line in text.splitlines():
        switch = re.fullmatch(r'\s*(?:##\s*)?偏好地点筛选\s*[：:]\s*([开关])\s*', line)
        if switch:
            lines.append('偏好地点筛选：'+switch[1])
            in_locations = False
            continue
        heading = re.fullmatch(r'##\s*([^#].+?)\s*[：:]?\s*', line)
        if heading:in_locations = heading[1].rstrip('：:').strip() == '偏好地点筛选'
        note = re.fullmatch(r'\s*(?:>\s*)?(?:注释|备注)\s*[：:]\s*(.*)', line)
        if note:
            content = note[1]
            if re.match(r'以上(?:为|两项是)基准值', content) and '浮动' in content:
                continue
            line = '> 备注：'+content
        elif in_locations and line.strip() and not heading:
            import preferred_locations
            values = preferred_locations.parse_config(line)
            line = '、'.join(re.sub(r'^.+?市(.+[区县市])$', r'\1', value) for value in values) if values else line
        lines.append(line)
        if not has_location_switch and re.fullmatch(r'过及格线就进行AI整体复盘\s*[：:]\s*[开关]\s*', line):
            lines.extend(('', '偏好地点筛选：关'))
    return '\n'.join(lines)+'\n'


def render(text, persona=None, locations=None):
    old = hr_job.parse(text)
    # Future upgrades must not repeatedly reset the recruiter's accepted edits.
    if hr_job.PASS_REVIEW in text and '### 2. 否决词库' in text:
        return format_document(text)
    worker = '普工' in old['position']
    persona = old.get('overall_review_rules', '') if persona is None else persona
    locations = old.get('preferred_locations', []) if locations is None else locations
    prefix, separator, _ = text.partition('## 三、其他配置')
    if not separator:raise ValueError('other_config_section_missing')
    list_part, resume_part = prefix.split('## 二、电子简历', 1)
    list_part, count = re.subn(r'### +2\.\s*减分词库', '### 2. 否决词库', list_part, count=1)
    if not count:raise ValueError('list_negative_section_missing')
    start = list_part.index('### 2. 否决词库')+len('### 2. 否决词库')
    body = list_part[start:]
    body = '\n'.join(line for line in body.splitlines() if not line.strip().lstrip('> ').startswith(('注释：','注释:','说明：','备注：')))
    list_part = list_part[:start]+'\n\n> 备注：'+VETO_NOTE+'\n\n'+body.strip()+'\n\n'
    prefix = list_part+'## 二、电子简历'+resume_part
    settings = (
        '单简历查看时间不低于：30 秒', '连续招呼五次后额外休息：30 秒',
        '同事几天以上可打招呼（填 0 为不判断同事）：7 天',
        '三句招呼（关闭为单句）：关', 'AI优缺点判断：关',
        '减分至合格线后AI整体复盘：'+('开' if worker else '关'),
        '过及格线就进行AI整体复盘：'+('关' if worker else '开'))
    updated = prefix+separator+'\n\n'+'\n\n'.join(settings)
    updated += '\n\n## AI整体复盘规则\n\n> 备注：目标角色的人物画像\n\n'+persona.strip()
    updated += '\n\n## 偏好地点筛选\n\n> 备注：填入目标地点城市或周边城市。牛人分析器中有偏好地点的会进行筛选，没有的会跳过偏好地点筛选继续判断简历。留空或写“关”为该岗位跳过偏好地点筛选。\n\n'+'、'.join(locations)+'\n'
    updated = format_document(updated)
    new = hr_job.parse(updated)
    for stage in ('list','resume'):
        for key in ('groups','terms','negative'):
            if old[stage][key] != new[stage][key]:raise ValueError('migration_changed_job_vocabulary')
    return updated


def propose(path, persona=None, locations=None, template=False):
    path = Path(path)
    original = path.read_bytes()
    text = original.decode('utf-8-sig')
    if template:text = text.replace('{{岗位名称}}', '模板示例岗位')
    updated = render(text, persona, locations)
    if template:updated = updated.replace('# 模板示例岗位\n', '# {{岗位名称}}\n', 1)
    newline = '\r\n' if b'\r\n' in original else '\n'
    data = updated.replace('\r\n','\n').replace('\n',newline).encode('utf-8')
    if original.startswith(b'\xef\xbb\xbf'):data = b'\xef\xbb\xbf'+data
    return dict(path=str(path.resolve()), before_sha256=hashlib.sha256(original).hexdigest(), data=data)
