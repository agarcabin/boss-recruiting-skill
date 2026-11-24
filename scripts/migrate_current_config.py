"""Normalize local HR labels while preserving job vocabularies and configured values."""
import re
import hr_job


def seconds(value):
    return str(int(value)) if float(value).is_integer() else str(value)


def update(text):
    if hr_job.PASS_REVIEW in text:
        hr_job.parse(text)
        return text
    before = hr_job.parse(text)
    # The advisory-only switch has been replaced by the overall review setting.
    text = re.sub(r'^### +3\.\s*误判复诊\s*\n[\s\S]*?(?=^## +三、其他配置)', '', text, flags=re.M)
    text = text.replace('初筛通过后，判断是否命中减分词库，命中则跳过。可填写表示不符合要求的词语。留空则不判断，建议少写。',
                        '每命中一个不同减分词扣10分，同词重复只扣一次；正向通过但减分低于合格线时按AI整体复盘开关处理。')
    config = '\n\n'.join((
        '单简历查看时间不低于：'+seconds(before['minimum_seconds'])+' 秒',
        '连续招呼五次后额外休息：'+seconds(before['rest_seconds'])+' 秒',
        '同事几天以上可打招呼（填 0 为不判断同事）：'+seconds(before['coworker_days'])+' 天',
        '三句招呼（关闭为单句）：'+('开' if before['greeting_mode']=='triple' else '关'),
        'AI总评：'+('开' if before.get('ai_total_review') else '关'),
        '减分至合格线后AI整体复盘：'+('开' if before['overall_review'] else '关')))
    prefix, separator, _ = text.partition('## 三、其他配置')
    if not separator:raise ValueError('other_config_section_missing')
    result = prefix+separator+'\n\n'+config+'\n'
    after = hr_job.parse(result)
    for stage in ('list','resume'):
        for key in ('groups','terms','negative'):
            if before[stage][key] != after[stage][key]:raise ValueError('migration_changed_vocabulary')
    for key in ('position','minimum_seconds','rest_seconds','coworker_days','greeting_mode','ai_total_review','overall_review'):
        if before[key] != after[key]:raise ValueError('migration_changed_configuration')
    return result
