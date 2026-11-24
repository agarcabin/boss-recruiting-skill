"""Deterministic analyzer gates for job intent and communication rate."""
import re


_INTENT = re.compile(
    r'求职意愿\s*(?:(?:为|是)\s*)?[：:]?\s*'
    r'(较强|强|一般|较低|低)'
)
_ANALYZER = re.compile(r'(?:BOSS)?牛人分析器|查看全部\d+项分析')
_COMMUNICATION_BOSS = re.compile(
    r'沟\s*通\s*Boss\s*(?:超过|高于|大于|达到|达)?\s*'
    r'(\d{1,3}(?:\.\d+)?)\s*(?:%|％)\s*的?\s*同类牛人',
    re.I,
)
_COMMUNICATION_RATE = re.compile(
    r'沟\s*通\s*率\s*[：:]?\s*'
    r'(?:高于|超过|大于|达|达到)?\s*'
    r'(?:同行|平均|平均水?平)?\s*'
    r'(\d{1,3}(?:\.\d+)?)\s*(?:%|％|分|以上|及以上)?'
)
_VIP_OC_OCR = re.compile(r'(?:V[I1]P|/IP|IP)专[享亭]', re.I)


def _normalize(text):
    # BOSS can inject its "VIP专享" label between analyzer lines. OCR then
    # reads it inside a field such as "求职意\nVIP专享\n愿强".
    normalized = re.sub(r'\s+', '', text or '')
    normalized = _VIP_OC_OCR.sub('', normalized)
    return re.sub(r'(?<=意)[<>‹›·•](?=愿)', '', normalized)


def analyzer_present(text):
    normalized = _normalize(text)
    return bool(
        _ANALYZER.search(normalized)
        or _INTENT.search(normalized)
        or _COMMUNICATION_BOSS.search(normalized)
        or _COMMUNICATION_RATE.search(normalized)
    )


def evaluate_intent(enabled, accepted, text):
    if not enabled:
        return dict(state='disabled', reason='求职意愿筛选已关闭')
    normalized = _normalize(text)
    values = list(dict.fromkeys(_INTENT.findall(normalized)))
    if not values:
        if not analyzer_present(normalized):
            return dict(state='analyzer_absent', reason='未出现牛人分析器')
        return dict(state='unknown', reason='未读取到牛人分析器求职意愿')
    if len(values) != 1:
        return dict(state='unknown', values=values,
                    reason='牛人分析器求职意愿存在冲突')
    value = values[0]
    if value not in set(accepted):
        return dict(state='mismatch', observed=value,
                    reason=f'求职意愿为{value}，不属于允许的{"、".join(accepted)}')
    return dict(state='match', observed=value, reason='求职意愿符合要求')


def evaluate_communication_boss(enabled, minimum, unknown_policy, text):
    if not enabled:
        return dict(state='disabled', reason='沟通Boss门槛已关闭')
    normalized = _normalize(text)
    values = []
    for match in list(_COMMUNICATION_BOSS.finditer(normalized)) + list(_COMMUNICATION_RATE.finditer(normalized)):
        try:
            value = float(match.group(1))
        except ValueError:
            continue
        if 0 <= value <= 100:
            values.append(value)
    values = sorted(set(values))
    if not values:
        if not analyzer_present(normalized):
            return dict(state='analyzer_absent', reason='未出现牛人分析器')
        if unknown_policy == 'skip':
            return dict(state='unknown', reason='未读取到牛人分析器沟通Boss百分位')
        return dict(state='absent', reason='未读取到牛人分析器沟通Boss百分位，按符合处理')
    if len(values) != 1:
        if unknown_policy == 'skip':
            return dict(state='unknown', values=values,
                        reason='牛人分析器沟通Boss百分位存在冲突')
        return dict(state='absent', values=values,
                    reason='牛人分析器沟通Boss百分位存在冲突，按符合处理')
    value = values[0]
    if value > minimum:
        return dict(state='match', observed=value,
                    reason=f'沟通Boss超过{value:g}%的同类牛人，高于门槛{minimum:g}%')
    return dict(state='mismatch', observed=value,
                reason=f'沟通Boss超过{value:g}%的同类牛人，未超过门槛{minimum:g}%')
