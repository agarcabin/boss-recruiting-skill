"""Any coworker contact <=7 days old skips; complete older history may continue.

Input is a small, directed UIA observation, never the full resume or page tree.
This module performs no browser operations and sends no messages.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

CN_TZ = timezone(timedelta(hours=8))
LOCAL_EXCEL_DEDUP_ENABLED = False


def parse_greeting_time(value: str) -> datetime:
    value = value.strip()
    # Do not guess the year/time from relative or date-only labels.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?", value):
        raise ValueError("first_coworker_time_unreadable")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp.replace(tzinfo=CN_TZ) if stamp.tzinfo is None else stamp


def date_interval(value, observed):
    """Only unambiguous dates; relative labels are anchored to observation time."""
    try:
        exact=parse_greeting_time(value)
        return exact,exact
    except (ValueError,TypeError):pass
    match=re.fullmatch(r'(今天|昨天)(?:\s*(\d{1,2}):(\d{2}))?',value.strip())
    if match:
        day=observed.astimezone(CN_TZ).replace(hour=0,minute=0,second=0,microsecond=0)
        if match[1]=='昨天':day-=timedelta(days=1)
        if match[2]:
            try:exact=day.replace(hour=int(match[2]),minute=int(match[3]))
            except ValueError:return None
            return exact,exact
        return day,day+timedelta(days=1)-timedelta(microseconds=1)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value.strip()):
        try:day=datetime.fromisoformat(value.strip()).replace(tzinfo=CN_TZ)
        except ValueError:return None
        return day,day+timedelta(days=1)-timedelta(microseconds=1)
    return None


def evaluate(observation: dict | None, at: datetime | None = None, threshold_days=7) -> dict:
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError("checked_at must include timezone")
    observation = observation if isinstance(observation, dict) else {}
    state = observation.get("state", "unavailable")
    evidence = str(observation.get("evidence", "")).strip()
    result = {"action": "review", "reason": "coworker_check_required",
              "state": state, "first_greeting_at": observation.get("first_greeting_at"),
              "evidence": evidence, "checked_at": at.isoformat(), "skip": False,
              "may_continue": False, "threshold_days": threshold_days,
              "lookup_completed": observation.get("lookup_completed") is True}
    records=observation.get('records')
    result.update(records=records,records_complete=observation.get('records_complete') is True)
    if not evidence:
        return result
    if state == "empty" and not observation.get("first_greeting_at") and not records:
        return dict(result, action="continue", reason="no_coworker_greetings", may_continue=True)
    if (state == "not_found" and observation.get("lookup_completed") is True
            and not observation.get("first_greeting_at") and not records):
        return dict(result, action="continue", reason="coworker_not_found_user_policy", may_continue=True)
    if state not in ("first_record","records"):
        return dict(result, reason="coworker_progress_unavailable")
    if records is None:records=[observation.get('first_greeting_at')]
    if not isinstance(records,list) or not records:return dict(result,reason='coworker_times_unreadable')
    error=None
    for record in records:
        value=record.get('greeting_at') if isinstance(record,dict) else record
        try:stamp=parse_greeting_time(str(value or ''))
        except (TypeError,ValueError):
            error='coworker_time_unreadable';continue
        if stamp>at:
            error='coworker_time_in_future';continue
        if stamp>=at-timedelta(days=threshold_days):
            return dict(result,action='skip',skip=True,may_continue=False,
                        matched_greeting_at=stamp.isoformat(),reason=f'coworker_within_or_exactly_{threshold_days:g}_days')
    if error:return dict(result,reason=error)
    if not result['records_complete']:return dict(result,reason='coworker_history_incomplete_requires_fresh_lookup')
    return dict(result,action='continue',may_continue=True,reason=f'all_coworker_contacts_older_than_{threshold_days:g}_days')


def evaluate_for_rules(observation, rules, at=None):
    """Worker v2 permits attempted but unreadable checks, never a known recent contact."""
    import recruiting_rules
    result = evaluate(observation, at, rules.get('hr_job_config', {}).get('coworker_days', 7))
    if rules.get('coworker_notice_policy') == 1:
        if not isinstance(observation, dict) or observation.get('state') in (None, 'not_checked'):
            return result
        records=list(observation.get('records') or [])
        if observation.get('first_greeting_at'):records.append(observation['first_greeting_at'])
        checked=at or datetime.now(timezone.utc)
        threshold=rules.get('hr_job_config',{}).get('coworker_days',7)
        try:observed=datetime.fromisoformat(observation.get('observed_at',''))
        except (ValueError,TypeError):observed=checked
        if observed.tzinfo is None:observed=checked
        all_old=bool(records)
        for record in records:
            value=record.get('greeting_at') if isinstance(record,dict) else record
            interval=date_interval(str(value or ''),observed)
            if not interval:
                all_old=False;continue
            start,end=interval;cutoff=checked-timedelta(days=threshold)
            if cutoff <= start <= checked:
                return dict(result,skip=True,may_continue=False,action='skip',reason=f'coworker_within_or_exactly_{threshold:g}_days')
            if end>=cutoff:all_old=False
        if result.get('skip'):
            return result
        if all_old and observation.get('records_complete') and observation.get('evidence'):
            return dict(result,action='continue',may_continue=True,reason='all_confirmed_contacts_older_than_threshold')
        if result['may_continue'] and observation.get('state') != 'not_found':
            return result
        return dict(result, action='continue', may_continue=True, notice_required=True,
                    reason='coworker_unknown_requires_chat_notice', unreadable_reason=result['reason'])
    if not recruiting_rules.worker_v2(rules):
        return result
    if not isinstance(observation, dict) or not observation or observation.get('state') in (None, 'not_checked'):
        return result
    at = at or datetime.now(timezone.utc)
    records = observation.get('records')
    records = list(records) if isinstance(records, list) else []
    if observation.get('first_greeting_at'):
        records.append(observation['first_greeting_at'])
    for record in records:
        value = record.get('greeting_at') if isinstance(record, dict) else record
        try:
            stamp = parse_greeting_time(str(value or ''))
        except (ValueError, TypeError):
            continue
        if at - timedelta(days=7) <= stamp <= at:
            return dict(result, action='skip', skip=True, may_continue=False,
                        matched_greeting_at=stamp.isoformat(), reason='coworker_within_or_exactly_7_days')
    if result['may_continue']:
        return result
    return dict(result, action='continue', skip=False, may_continue=True,
                unreadable_reason=result['reason'], reason='worker_unreadable_coworker_allowed_by_user')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Small directed UIA observation JSON")
    parser.add_argument("--checked-at", help="Explicit timezone-aware time for replay/testing")
    args = parser.parse_args()
    observation = json.loads(args.input.read_text(encoding="utf-8-sig"))
    at = datetime.fromisoformat(args.checked_at) if args.checked_at else None
    print(json.dumps(evaluate(observation, at), ensure_ascii=False))


if __name__ == "__main__":
    main()
