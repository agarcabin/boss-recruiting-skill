"""Shared company/position names for daily recruiting reports."""
from __future__ import annotations
import workspace_paths

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ledger

CN_TZ = timezone(timedelta(hours=8))


def profile_identity(profile: Path | str) -> tuple[str, str]:
    _, _, fields = ledger.profile_check(Path(profile))
    company, position = fields.get("company", ""), fields.get("position", "")
    if not company or not position:
        raise ValueError("report_profile_identity_missing")
    return company, position


def filename_component(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .") or "未命名"
    if cleaned != value or len(cleaned) > 60:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        cleaned = cleaned[:50] + "-" + digest
    return cleaned


def report_filename(profile: Path | str, filename: str | None = None) -> str:
    company, position = profile_identity(profile)
    prefix = f"{filename_component(company)}-{filename_component(position)}-"
    base = filename or "投递记录.xlsx"
    if (re.search(r'[<>:"/\\|?*\x00-\x1f]', base)
            or not base.lower().endswith(".xlsx") or base.endswith(" ")):
        raise ValueError("output_file must be an .xlsx filename in the daily folder")
    return base if base.startswith(prefix) else prefix + base


def profile_short_label(profile: Path | str) -> str:
    """Short label for archived file names: the job profile file name."""
    path = Path(profile)
    stem = path.stem.strip(' .')
    try:
        configs = workspace_paths.configs_dir().resolve()
        parent = path.parent.resolve()
        in_configs = parent != configs and parent.is_relative_to(configs)
    except (OSError, ValueError):
        in_configs = False
    if in_configs and stem:
        value = stem
    else:
        company, position = profile_identity(profile)
        value = position or company
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(' .')[:30]


def report_path(root: Path, started_at: str, profile: Path | str) -> Path:
    day = datetime.fromisoformat(started_at).astimezone(CN_TZ)
    return workspace_paths.records_dir(root) / f"{day.month}月{day.day}日" / report_filename(profile)
