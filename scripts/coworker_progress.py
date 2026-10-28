"""Evaluate only the FIRST visible coworker greeting, using the user's >7-day rule.

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


def evaluate(observation: dict | None, at: datetime | None = None) -> dict:
    at = at or datetime.now(timezone.utc)
    if at.tzinfo is None:
        raise ValueError("checked_at must include timezone")
    observation = observation if isinstance(observation, dict) else {}
    state = observation.get("state", "unavailable")
    evidence = str(observation.get("evidence", "")).strip()
    result = {"action": "review", "reason": "coworker_check_required",
              "state": state, "first_greeting_at": observation.get("first_greeting_at"),
              "evidence": evidence, "checked_at": at.isoformat(), "skip": False,
              "may_continue": False, "threshold_days": 7,
              "lookup_completed": observation.get("lookup_completed") is True}
    if not evidence:
        return result
    if state == "empty" and not observation.get("first_greeting_at"):
        return dict(result, action="continue", reason="no_coworker_greetings", may_continue=True)
    if (state == "not_found" and observation.get("lookup_completed") is True
            and not observation.get("first_greeting_at")):
        return dict(result, action="continue", reason="coworker_not_found_user_policy", may_continue=True)
    if state != "first_record":
        return dict(result, reason="coworker_progress_unavailable")
    try:
        first = parse_greeting_time(str(observation.get("first_greeting_at", "")))
    except (TypeError, ValueError):
        return dict(result, reason="first_coworker_time_unreadable")
    if first > at:
        return dict(result, reason="first_coworker_time_in_future")
    # Deliberately NOT the conventional recent-contact rule: user specified OLD => SKIP.
    skip = first < at - timedelta(days=7)
    return dict(result, action="skip" if skip else "continue", skip=skip,
                may_continue=not skip, first_greeting_at=first.isoformat(),
                reason="first_coworker_older_than_7_days" if skip else "first_coworker_within_7_days")


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
