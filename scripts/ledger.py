"""Local, privacy-minimal ledger for one-at-a-time BOSS greeting runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sqlite3
import sys
import time
import uuid
import coworker_progress
import recruiting_rules
import run_safety
from datetime import datetime, timedelta, timezone
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


MAX_ROLLING_SENDS = 150
MAX_RUN_VIEWS = 300
DEFAULT_DB = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Codex" / "recruiting-greetings" / "ledger.sqlite3"
PROFILE_ROOT = Path(__file__).resolve().parents[1] / "profiles"


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def parse_timestamp_argument(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def output(**items: object) -> None:
    print(json.dumps(items, ensure_ascii=False))


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path, timeout=20, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 20000")
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            deadline_at TEXT NOT NULL,
            target INTEGER NOT NULL,
            profile_path TEXT NOT NULL,
            profile_hash TEXT NOT NULL,
            min_score INTEGER NOT NULL DEFAULT 70
        );
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_hash TEXT PRIMARY KEY,
            project TEXT NOT NULL,
            run_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','sent','not-sent','unknown','skipped','review')),
            token TEXT UNIQUE,
            created_at TEXT NOT NULL,
            sent_at TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS candidate_progress (
            run_id TEXT NOT NULL,
            candidate_hash TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            electronic_opened_at TEXT,
            finished_at TEXT,
            PRIMARY KEY(run_id, candidate_hash),
            UNIQUE(run_id, ordinal),
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );
        CREATE TABLE IF NOT EXISTS run_control (
            run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
            state TEXT NOT NULL CHECK(state IN ('running','paused','stopped')),
            updated_at TEXT NOT NULL,
            pause_reason TEXT,
            paused_at TEXT,
            paused_seconds INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS candidates_sent_at ON candidates(sent_at);
        CREATE INDEX IF NOT EXISTS candidates_run ON candidates(run_id, status);
        CREATE INDEX IF NOT EXISTS candidate_progress_active ON candidate_progress(run_id, finished_at);
        """
    )
    if "min_score" not in {row[1] for row in db.execute("PRAGMA table_info(runs)")}:
        db.execute("ALTER TABLE runs ADD COLUMN min_score INTEGER NOT NULL DEFAULT 70")
    if "pause_reason" not in {row[1] for row in db.execute("PRAGMA table_info(run_control)")}:
        db.execute("ALTER TABLE run_control ADD COLUMN pause_reason TEXT")
    control_columns = {row[1] for row in db.execute("PRAGMA table_info(run_control)")}
    if "paused_at" not in control_columns:
        db.execute("ALTER TABLE run_control ADD COLUMN paused_at TEXT")
    if "paused_seconds" not in control_columns:
        db.execute("ALTER TABLE run_control ADD COLUMN paused_seconds INTEGER NOT NULL DEFAULT 0")
    run_safety.migrate(db)
    return db


def profile_check(path: Path) -> tuple[bool, str, dict[str, str]]:
    if not path.is_file():
        return False, "profile_missing", {}
    content = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", content, re.S)
    if not match:
        return False, "front_matter_missing", {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    if fields.get("schema") != "boss-greeting-profile/v1":
        return False, "schema_mismatch", fields
    if not fields.get("company") or not fields.get("position"):
        return False, "identity_missing", fields
    if fields.get("approval") != "approved" or not fields.get("approved_by") or not fields.get("approved_at"):
        return False, "approval_missing", fields
    required_sections = ("页面核验", "企业与岗位事实", "自动筛选条件", "评分规则", "加分项", "待人工确认", "固定招呼话术", "冲突与待确认", "来源")
    if any(f"## {title}" not in content for title in required_sections):
        return False, "required_section_missing", fields
    if re.search(r"(?m)^\s*-\s*\[\s*\]", content):
        return False, "unresolved_conflicts", fields
    for title in ("页面核验", "企业与岗位事实", "自动筛选条件", "评分规则", "固定招呼话术"):
        section = re.search(rf"(?ms)^## {title}\s*\n(.*?)(?=^## |\Z)", content)
        if section and re.search(r"待确认|尚未确认|待审核|需确认|未决", section.group(1)):
            return False, "unresolved_policy_text", fields
    greeting = re.search(r"(?ms)^## 固定招呼话术\s*\n(.*?)(?=^## |\Z)", content)
    if not greeting or len(greeting.group(1).strip()) < 10:
        return False, "greeting_missing", fields
    return True, "ready", fields


def candidate_hash(project: str, candidate_id: str) -> str:
    normalized = candidate_id.strip()
    if len(normalized) < 6 or any(ch in normalized for ch in "\r\n"):
        raise ValueError("candidate_id must be a stable platform ID or profile URL")
    return hashlib.sha256((project.strip() + "\x00" + normalized).encode("utf-8")).hexdigest()


def profile_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unresolved(db: sqlite3.Connection) -> int:
    first = db.execute("SELECT COUNT(*) FROM candidates WHERE status IN ('pending','unknown')").fetchone()[0]
    later = db.execute("SELECT COUNT(*) FROM message_attempts WHERE message_index>1 AND status IN ('pending','dispatching','unknown')").fetchone()[0]
    return first + later


def rolling_count(db: sqlite3.Connection, at: datetime) -> int:
    return db.execute("SELECT COUNT(*) FROM candidates WHERE status='sent' AND sent_at > ?", (iso(at - timedelta(hours=24)),)).fetchone()[0]


def run_row(db: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
    if row is None:
        raise ValueError("run_not_found")
    return row


def control_state(db: sqlite3.Connection, run_id: str) -> str:
    run_row(db, run_id)
    row = db.execute("SELECT state,pause_reason FROM run_control WHERE run_id=?", (run_id,)).fetchone()
    if not row:
        return "running"  # Runs created before this control was added.
    return "login_required" if row["state"] == "paused" and row["pause_reason"] in ("session_expired", "risk_logout") else row["state"]


def active_elapsed_seconds(db: sqlite3.Connection, run_id: str, at: datetime | None = None) -> int:
    current = at or now()
    run = run_row(db, run_id)
    control_row = db.execute(
        "SELECT state,pause_reason,updated_at,paused_at,paused_seconds FROM run_control WHERE run_id=?",
        (run_id,),
    ).fetchone()
    elapsed = (current - parse_time(run["started_at"])).total_seconds()
    if control_row:
        elapsed -= int(control_row["paused_seconds"] or 0)
        if control_row["state"] == "paused":
            paused_at = parse_time(control_row["paused_at"] or control_row["updated_at"])
            elapsed -= max(0.0, (current - paused_at).total_seconds())
    return max(0, int(elapsed))


def control(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    if args.action == "stop":
        before = control_state(db, args.run)
        run_safety.request_stop(db, args.run, "manual_stop")
        output(state="stopped", changed=before != "stopped", reason="manual_stop")
        return
    at = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        before = control_state(db, args.run)
        control_row = db.execute(
            "SELECT state,pause_reason,updated_at,paused_at,paused_seconds FROM run_control WHERE run_id=?",
            (args.run,),
        ).fetchone()
        paused_at = control_row["paused_at"] if control_row else None
        paused_seconds = int((control_row["paused_seconds"] if control_row else 0) or 0)
        transitions = {"pause": {"running": "paused"},
                       "resume": {"paused": "running"},
                       "stop": {"running": "stopped", "paused": "stopped", "login_required": "stopped"},
                       "login-required": {"running": "login_required", "paused": "login_required"},
                       "login-confirmed": {"login_required": "running"}}
        after = transitions[args.action].get(before, before)
        reason = None
        if args.action == "login-confirmed" and before == "login_required":
            if not getattr(args, "manual_confirmed", False):
                after, reason = before, "manual_login_confirmation_required"
            elif at >= parse_time(run_row(db, args.run)["deadline_at"]):
                after, reason = before, "run_expired"
            elif unresolved(db):
                after, reason = before, "unresolved_prior_send"
        if after != before:
            if before == "running" and after in ("paused", "login_required"):
                paused_at = iso(at)
            elif before in ("paused", "login_required") and after in ("running", "stopped"):
                pause_start = parse_time(
                    paused_at
                    or (control_row["updated_at"] if control_row else iso(at))
                )
                paused_seconds += max(0, int((at - pause_start).total_seconds()))
                paused_at = None
            stored_state = "paused" if after == "login_required" else after
            pause_reason = getattr(args, "reason", "session_expired") if after == "login_required" else None
            db.execute("""INSERT INTO run_control
                (run_id,state,updated_at,pause_reason,paused_at,paused_seconds) VALUES (?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    state=excluded.state,
                    updated_at=excluded.updated_at,
                    pause_reason=excluded.pause_reason,
                    paused_at=excluded.paused_at,
                    paused_seconds=excluded.paused_seconds""",
                       (args.run, stored_state, iso(at), pause_reason, paused_at, paused_seconds))
        db.commit()
    except Exception:
        db.rollback()
        raise
    output(state=after, changed=after != before, reason=reason)


def gate(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    state = control_state(db, args.run)
    if state != "stopped" and now() >= parse_time(run_row(db, args.run)["deadline_at"]):
        state = "expired"
    reason = run_safety.quantity_reason(db, args.run) if state == "running" else None
    active = active_progress(db, args.run)
    output(state="draining" if reason and active and state == "running" else state,
           may_continue=state == "running" and (not reason or active is not None),
           may_start_candidate=state == "running" and not reason, drain_reason=reason,
           generation=run_row(db,args.run)["generation"])


def run_candidate_hash(db: sqlite3.Connection, run_id: str, candidate_id: str) -> str:
    run = run_row(db, run_id)
    _, _, fields = profile_check(Path(run["profile_path"]))
    return candidate_hash(run_namespace(run, fields), candidate_id)


def run_namespace(run, fields=None):
    if run["candidate_namespace"]:
        return run["candidate_namespace"]
    if fields is None:
        _, _, fields = profile_check(Path(run["profile_path"]))
    return fields.get("candidate_namespace") or f"{fields.get('company','')}-{fields.get('position','')}"


def active_progress(db: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM candidate_progress WHERE run_id=? AND finished_at IS NULL", (run_id,)).fetchone()


def candidate_begin(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    at = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        run = run_row(db, args.run)
        started_at = parse_timestamp_argument(getattr(args, "started_at", None), at)
        if started_at > at + timedelta(seconds=5):
            result = {"state": "blocked", "reason": "candidate_start_in_future"}
            db.commit()
            output(**result)
            return
        if started_at < parse_time(run["started_at"]):
            result = {"state": "blocked", "reason": "candidate_start_before_run"}
            db.commit()
            output(**result)
            return
        digest = run_candidate_hash(db, args.run, args.candidate_id)
        active = active_progress(db, args.run)
        existing = db.execute("SELECT * FROM candidate_progress WHERE run_id=? AND candidate_hash=?", (args.run, digest)).fetchone()
        if at >= parse_time(run["deadline_at"]):
            result = {"state": "blocked", "reason": "run_expired"}
        elif control_state(db, args.run) != "running":
            result = {"state": "blocked", "reason": "run_" + control_state(db, args.run)}
        elif not existing and run_safety.quantity_reason(db,args.run):
            result = {"state":"blocked", "reason":run_safety.quantity_reason(db,args.run)}
        elif active and active["candidate_hash"] != digest:
            result = {"state": "blocked", "reason": "another_candidate_active", "current_candidate_number": active["ordinal"]}
        elif not existing and db.execute("SELECT COUNT(*) FROM candidate_progress WHERE run_id=?", (args.run,)).fetchone()[0] >= MAX_RUN_VIEWS:
            result = {"state": "blocked", "reason": "run_view_limit_reached"}
        elif existing and existing["finished_at"]:
            result = {"state": "blocked", "reason": "candidate_already_finished", "current_candidate_number": existing["ordinal"]}
        elif existing:
            result = {"state": "resumed", "current_candidate_number": existing["ordinal"], "candidate_started_at": existing["started_at"]}
        elif db.execute("SELECT 1 FROM candidates WHERE candidate_hash=?", (digest,)).fetchone():
            result = {"state": "blocked", "reason": "candidate_seen"}
        else:
            ordinal = db.execute("SELECT COALESCE(MAX(ordinal),0)+1 FROM candidate_progress WHERE run_id=?", (args.run,)).fetchone()[0]
            db.execute("INSERT INTO candidate_progress VALUES (?,?,?,?,?,?)", (args.run, digest, ordinal, iso(started_at), None, None))
            result = {"state": "started_candidate", "current_candidate_number": ordinal, "candidate_started_at": iso(started_at)}
        db.commit()
    except Exception:
        db.rollback()
        raise
    output(**result)


def electronic_opened(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    if run_row(db,args.run)['evaluation_mode']=='card':
        output(state='blocked',reason='electronic_resume_not_applicable')
        return
    at = now()
    digest = run_candidate_hash(db, args.run, args.candidate_id)
    active = active_progress(db, args.run)
    if not active or active["candidate_hash"] != digest:
        output(state="blocked", reason="candidate_not_active")
        return
    db.execute("UPDATE candidate_progress SET electronic_opened_at=COALESCE(electronic_opened_at,?) WHERE run_id=? AND candidate_hash=?", (iso(at), args.run, digest))
    count = db.execute("SELECT COUNT(*) FROM candidate_progress WHERE run_id=? AND electronic_opened_at IS NOT NULL", (args.run,)).fetchone()[0]
    output(state="electronic_opened", current_candidate_number=active["ordinal"], electronic_resume_opened_candidates=count)


def candidate_finish(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    digest = run_candidate_hash(db, args.run, args.candidate_id)
    active = active_progress(db, args.run)
    if not active or active["candidate_hash"] != digest:
        output(state="blocked", reason="candidate_not_active")
        return
    assessment_columns = (
        {row["name"] for row in db.execute("PRAGMA table_info(assessments)").fetchall()}
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone()
        else set()
    )
    resume_status_sql = (
        "resume_archive_status"
        if "resume_archive_status" in assessment_columns
        else "'pending' AS resume_archive_status"
    )
    assessment = db.execute(
        f"SELECT send_status,pdf_status,{resume_status_sql},report_written,ended_at,evaluation_mode "
        "FROM assessments WHERE run_id=? AND candidate_hash=?",
        (args.run, digest),
    ).fetchone() if assessment_columns else None
    candidate = db.execute("SELECT status FROM candidates WHERE candidate_hash=?", (digest,)).fetchone()
    if candidate and candidate['status']=='sent' and recruiting_rules.run_rules(run_row(db,args.run)).get('policy','legacy')!='legacy':
        sent_messages={r[0] for r in db.execute("SELECT message_index FROM message_attempts WHERE run_id=? AND candidate_hash=? AND status='sent'",(args.run,digest))}
        if sent_messages!={1,2,3}:
            output(state='blocked',reason='greeting_messages_incomplete')
            return
    if (
        not assessment
        or not candidate
        or not assessment["report_written"]
        or assessment["send_status"] != candidate["status"]
        or candidate["status"] in ("pending", "unknown")
        or (
            candidate["status"] == "sent"
            and (
                (assessment["pdf_status"] not in ("saved", "missing") and not (assessment["pdf_status"]=="not_applicable" and (assessment["evaluation_mode"]=="card" or not recruiting_rules.run_rules(run_row(db,args.run)).get("pdf_required",True))))
                or (assessment["evaluation_mode"] != "card" and assessment["resume_archive_status"] not in ("saved", "missing"))
            )
        )
    ):
        output(state="blocked", reason="candidate_workflow_incomplete")
        return
    if not assessment["ended_at"]:
        output(state="blocked", reason="candidate_timing_pending")
        return
    at = now()
    ended_at = parse_time(assessment["ended_at"])
    requested_end = getattr(args, "ended_at", None)
    if requested_end and iso(parse_time(requested_end)) != iso(ended_at):
        output(state="blocked", reason="candidate_end_mismatch")
        return
    if ended_at > at + timedelta(seconds=5):
        output(state="blocked", reason="candidate_end_in_future")
        return
    if ended_at < parse_time(active["started_at"]):
        output(state="blocked", reason="candidate_end_before_start")
        return
    db.execute("UPDATE candidate_progress SET finished_at=? WHERE run_id=? AND candidate_hash=?", (iso(ended_at), args.run, digest))
    output(state="finished_candidate", current_candidate_number=active["ordinal"], candidate_ended_at=iso(ended_at))


def start(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    path = Path(args.profile).resolve()
    if not path.is_relative_to(PROFILE_ROOT.resolve()):
        output(state="blocked", reason="profile_outside_skill_profiles")
        return
    ok, reason, fields = profile_check(path)
    if not ok:
        output(state="blocked", reason=reason)
        return
    rules = recruiting_rules.snapshot(path,fields)
    binding = None
    if rules["policy"] != "legacy":
        import stop_controller
        binding_path = getattr(args,"stop_binding",None)
        if not binding_path:
            output(state="blocked",reason="stop_binding_required")
            return
        binding = stop_controller.load_binding(Path(binding_path))
        stop_controller.probe_binding(binding)
    if not 1 <= args.target <= MAX_ROLLING_SENDS or not 1 <= args.duration_min <= 240 or not 0 <= args.min_score <= 100:
        raise ValueError("target 1..150, duration_min 1..240, min_score 0..100 required")
    if unresolved(db):
        output(state="blocked", reason="unresolved_prior_send")
        return
    at = now()
    run_id = uuid.uuid4().hex
    db.execute("INSERT INTO runs (run_id,started_at,deadline_at,target,profile_path,profile_hash,min_score) VALUES (?,?,?,?,?,?,?)", (run_id, iso(at), iso(at + timedelta(minutes=args.duration_min)), args.target, str(path), profile_hash(path), args.min_score))
    db.execute("UPDATE runs SET candidate_namespace=?,evaluation_mode=?,rule_snapshot=?,stop_binding=? WHERE run_id=?",
               (rules["namespace"],rules["mode"],json.dumps(rules,ensure_ascii=False),json.dumps(binding) if binding else None,run_id))
    db.execute("INSERT INTO run_control (run_id,state,updated_at) VALUES (?,?,?)", (run_id, "running", iso(at)))
    output(state="started", run_id=run_id, company=fields["company"], position=fields["position"], min_score=args.min_score, deadline_at=iso(at + timedelta(minutes=args.duration_min)))


def status(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    at = now()
    counts: dict[str, int] = {}
    details: dict[str, object] = {}
    if args.run:
        row = run_row(db, args.run)
        counts = {r["status"]: r["n"] for r in db.execute("SELECT status, COUNT(*) AS n FROM candidates WHERE run_id=? GROUP BY status", (args.run,))}
        elapsed = active_elapsed_seconds(db, args.run, at)
        active = active_progress(db, args.run)
        progress = db.execute("SELECT COUNT(*) AS started, COUNT(finished_at) AS finished, COUNT(electronic_opened_at) AS electronic_opened FROM candidate_progress WHERE run_id=?", (args.run,)).fetchone()
        current_stage = None
        if active:
            assessed = db.execute("SELECT 1 FROM assessments WHERE run_id=? AND candidate_hash=?", (args.run, active["candidate_hash"])).fetchone() if db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone() else None
            current_stage = "post_assessment" if assessed else "judging"
        details = {"run_id": args.run, "target": row["target"], "min_score": row["min_score"],
                   "run_state": control_state(db, args.run),
                   "started_at": row["started_at"], "deadline_at": row["deadline_at"], "run_expired": at >= parse_time(row["deadline_at"]),
                   "elapsed_seconds": elapsed, "elapsed_display": f"{elapsed // 3600:02d}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",
                   "current_candidate_number": active["ordinal"] if active else None, "current_stage": current_stage,
                   "candidates_started": progress["started"], "candidates_completed": progress["finished"], "view_remaining": max(0, MAX_RUN_VIEWS-progress["started"]),
                   "electronic_resume_opened_candidates": progress["electronic_opened"], "greetings_sent": counts.get("sent", 0)}
    next_row = db.execute("SELECT value FROM settings WHERE key='next_allowed_at'").fetchone()
    next_at = parse_time(next_row[0]) if next_row else None
    output(state="status", rolling_sent=rolling_count(db, at), rolling_remaining=MAX_ROLLING_SENDS - rolling_count(db, at), unresolved=unresolved(db), next_allowed_at=iso(next_at) if next_at else None, counts=counts, **details)


def recent_runs(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    at = now()
    rows = db.execute(
        "SELECT run_id,started_at,deadline_at,target,profile_path FROM runs ORDER BY started_at DESC LIMIT 5"
    ).fetchall()
    items = []
    for row in rows:
        profile_path = Path(row["profile_path"])
        fields: dict[str, str] = {}
        try:
            fields = profile_check(profile_path)[2]
        except OSError:
            fields = {}
        metadata: dict[str, object] = {}
        metadata_path = profile_path.parent / "project.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
        company = str(fields.get("company") or metadata.get("company") or "")
        position = str(fields.get("position") or metadata.get("position") or "")
        expired = at >= parse_time(row["deadline_at"])
        state = "expired" if expired else control_state(db, row["run_id"])
        counts = {item["status"]: item["n"] for item in db.execute(
            "SELECT status, COUNT(*) AS n FROM candidates WHERE run_id=? GROUP BY status", (row["run_id"],)
        )}
        unresolved_count = db.execute(
            "SELECT COUNT(*) FROM candidates WHERE run_id=? AND status IN ('pending','unknown')",
            (row["run_id"],),
        ).fetchone()[0]
        items.append({
            "run_id": row["run_id"],
            "profile_path": str(profile_path),
            "project_id": metadata.get("project_id"),
            "company": company,
            "position": position,
            "display_name": f"{company} - {position}".strip(" -"),
            "started_at": row["started_at"],
            "deadline_at": row["deadline_at"],
            "target": row["target"],
            "run_state": state,
            "resumable": not expired and state in ("running", "paused", "login_required"),
            "greetings_sent": counts.get("sent", 0),
            "unresolved": unresolved_count,
        })
    output(state="runs", items=items)

def watch(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    if not 1 <= args.interval <= 60:
        raise ValueError("interval must be 1..60 seconds")
    run_row(db, args.run)
    try:
        while True:
            at = now()
            run = run_row(db, args.run)
            elapsed = active_elapsed_seconds(db, args.run, at)
            active = active_progress(db, args.run)
            electronic = db.execute("SELECT COUNT(*) FROM candidate_progress WHERE run_id=? AND electronic_opened_at IS NOT NULL", (args.run,)).fetchone()[0]
            sent = db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'", (args.run,)).fetchone()[0]
            if active:
                assessed = db.execute("SELECT 1 FROM assessments WHERE run_id=? AND candidate_hash=?", (args.run, active["candidate_hash"])).fetchone() if db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone() else None
                current = f"第{active['ordinal']}位候选人（{'发送或归档中' if assessed else '判断中'}）"
            else:
                current = "无"
            state = control_state(db, args.run)
            print(f"状态 {state} | 已运行 {elapsed // 3600:02d}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d} | 当前处理 {current} | 已打开电子简历 {electronic} 人 | 成功打招呼 {sent} 次", flush=True)
            if state == "stopped" or (at >= parse_time(run["deadline_at"]) and not active):
                return
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return


def reserve(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    at = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        run = run_row(db, args.run)
        path = Path(run["profile_path"])
        ok, reason, fields = profile_check(path)
        project = run_namespace(run, fields)
        digest = candidate_hash(project, args.candidate_id)
        has_assessments = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='assessments'").fetchone()
        assessment_columns = (
            {row["name"] for row in db.execute("PRAGMA table_info(assessments)").fetchall()}
            if has_assessments else set()
        )
        override_expr = "hard_requirement_override" if "hard_requirement_override" in assessment_columns else "'false' AS hard_requirement_override"
        coworker_expr = "coworker_progress" if "coworker_progress" in assessment_columns else "NULL AS coworker_progress"
        assessment = (db.execute(f"SELECT decision,overall_score,hard_requirements,{override_expr},send_status,pdf_status,report_written,evaluation_mode,eligibility_json,evaluation_input,{coworker_expr} FROM assessments WHERE run_id=? AND candidate_hash=?", (args.run, digest)).fetchone()
                      if has_assessments else None)
        try:
            coworker_check = coworker_progress.evaluate(
                json.loads(assessment["coworker_progress"] or "{}") if assessment else None, at)
        except (ValueError, TypeError):
            coworker_check = coworker_progress.evaluate(None, at)
        unsynced = (db.execute("""SELECT 1 FROM candidates c JOIN assessments a ON a.candidate_hash=c.candidate_hash
            WHERE a.send_status<>c.status LIMIT 1""").fetchone() if has_assessments else None)
        unwritten = (db.execute("SELECT 1 FROM assessments WHERE report_written=0 LIMIT 1").fetchone() if has_assessments else None)
        if "resume_archive_status" in assessment_columns:
            resume_unarchived = db.execute(
                "SELECT 1 FROM assessments WHERE send_status='sent' "
                "AND resume_archive_status='pending' AND evaluation_mode<>'card' LIMIT 1"
            ).fetchone()
        else:
            resume_unarchived = (
                db.execute("SELECT 1 FROM assessments WHERE send_status='sent' LIMIT 1").fetchone()
                if has_assessments else None
            )
        pdf_unarchived = (
            db.execute(
                "SELECT 1 FROM assessments WHERE send_status='sent' AND pdf_status='pending' AND evaluation_mode<>'card' LIMIT 1"
            ).fetchone()
            if has_assessments else None
        )
        if not ok:
            result = {"state": "blocked", "reason": reason}
        elif profile_hash(path) != run["profile_hash"]:
            result = {"state": "blocked", "reason": "profile_changed_since_start"}
        elif at >= parse_time(run["deadline_at"]):
            result = {"state": "blocked", "reason": "run_expired"}
        elif control_state(db, args.run) != "running":
            result = {"state": "blocked", "reason": "run_" + control_state(db, args.run)}
        elif unresolved(db):
            result = {"state": "blocked", "reason": "unresolved_prior_send"}
        elif unsynced:
            result = {"state": "blocked", "reason": "report_not_synced"}
        elif unwritten:
            result = {"state": "blocked", "reason": "report_not_written"}
        elif resume_unarchived:
            result = {"state": "blocked", "reason": "resume_archive_pending"}
        elif pdf_unarchived:
            result = {"state": "blocked", "reason": "pdf_archive_pending"}
        elif db.execute("SELECT 1 FROM candidates WHERE candidate_hash=?", (digest,)).fetchone():
            result = {"state": "blocked", "reason": "candidate_seen"}
        elif not active_progress(db, args.run) or active_progress(db, args.run)["candidate_hash"] != digest:
            result = {"state": "blocked", "reason": "candidate_not_active"}
        elif not assessment:
            result = {"state": "blocked", "reason": "assessment_missing"}
        elif assessment["decision"] != "greet" or not assessment_eligible(run,assessment) or assessment["send_status"] != "assessed" or not assessment["report_written"]:
            result = {"state": "blocked", "reason": "assessment_not_eligible"}
        elif assessment["evaluation_mode"] != "card" and not coworker_check["may_continue"]:
            result = {"state": "blocked", "reason": coworker_check["reason"]}
        elif db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'", (args.run,)).fetchone()[0] >= run["target"]:
            result = {"state": "blocked", "reason": "run_target_reached"}
        elif rolling_count(db, at) >= MAX_ROLLING_SENDS:
            result = {"state": "blocked", "reason": "rolling_limit_reached"}
        else:
            next_row = db.execute("SELECT value FROM settings WHERE key='next_allowed_at'").fetchone()
            next_at = parse_time(next_row[0]) if next_row else None
            if next_at and at < next_at:
                result = {"state": "wait", "until": iso(next_at), "seconds": max(1, int((next_at - at).total_seconds() + 0.999))}
            else:
                token = uuid.uuid4().hex
                db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)", (digest, project, args.run, "pending", token, iso(at), None, iso(at)))
                db.execute("INSERT INTO message_attempts VALUES (?,?,?,?,?,?,?,?)", (token,args.run,digest,1,"pending",run["generation"],iso(at),iso(at)))
                result = {"state": "ready", "token": token}
        db.commit()
    except Exception:
        db.rollback()
        raise
    output(**result)


def resolve(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    if not 60 <= args.min_gap <= args.max_gap <= 600:
        raise ValueError("min_gap/max_gap must satisfy 60 <= min <= max <= 600")
    at = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT status FROM candidates WHERE token=?", (args.token,)).fetchone()
        if row is None or row["status"] != "pending":
            result = {"state": "blocked", "reason": "reservation_not_pending"}
        else:
            sent_at = iso(at) if args.result == "sent" else None
            db.execute("UPDATE candidates SET status=?, sent_at=?, updated_at=? WHERE token=?", (args.result, sent_at, iso(at), args.token))
            db.execute("UPDATE message_attempts SET status=?,updated_at=? WHERE token=?",(args.result,iso(at),args.token))
            if args.result == "sent":
                gap = random.SystemRandom().uniform(args.min_gap, args.max_gap)
                next_allowed = iso(at + timedelta(seconds=gap))
                db.execute("INSERT INTO settings VALUES ('next_allowed_at', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (next_allowed,))
                result = {"state": "sent", "next_allowed_at": next_allowed, "rolling_sent": rolling_count(db, at)}
            else:
                result = {"state": args.result, "requires_manual_reconciliation": args.result == "unknown"}
        db.commit()
    except Exception:
        db.rollback()
        raise
    output(**result)


def note(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    at = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        run = run_row(db, args.run)
        path = Path(run["profile_path"])
        ok, reason, fields = profile_check(path)
        if not ok or profile_hash(path) != run["profile_hash"]:
            raise ValueError(reason if not ok else "profile_changed_since_start")
        project = run_namespace(run, fields)
        digest = candidate_hash(project, args.candidate_id)
        active = active_progress(db, args.run)
        if not active or active["candidate_hash"] != digest:
            raise ValueError("candidate_not_active")
        assessment = db.execute("SELECT decision,report_written FROM assessments WHERE run_id=? AND candidate_hash=?", (args.run, digest)).fetchone() if db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone() else None
        if not assessment or not assessment["report_written"] or assessment["decision"] != ("skip" if args.result == "skipped" else "review"):
            raise ValueError("assessment_missing_or_not_synced")
        cur = db.execute("INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?,?,?)", (digest, project, args.run, args.result, None, iso(at), None, iso(at)))
        db.commit()
    except Exception:
        db.rollback()
        raise
    output(state="noted" if cur.rowcount else "candidate_seen", result=args.result)


def reconcile(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    if not args.manual_confirmed:
        raise ValueError("manual platform verification is required")
    at = now()
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT status, created_at FROM candidates WHERE token=?", (args.token,)).fetchone()
        if row is None or row["status"] not in ("pending", "unknown"):
            result = {"state": "blocked", "reason": "reservation_not_unresolved"}
        else:
            # The exact click time is unknown after recovery; use the later confirmation
            # time so the rolling limit remains conservative.
            sent_at = iso(at) if args.result == "sent" else None
            db.execute("UPDATE candidates SET status=?, sent_at=?, updated_at=? WHERE token=?", (args.result, sent_at, iso(at), args.token))
            if args.result == "sent":
                next_allowed = iso(at + timedelta(seconds=80))
                db.execute("INSERT INTO settings VALUES ('next_allowed_at', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (next_allowed,))
            db.execute("UPDATE message_attempts SET status=?,updated_at=? WHERE token=?",(args.result,iso(at),args.token))
            result = {"state": "reconciled", "result": args.result}
        db.commit()
    except Exception:
        db.rollback()
        raise
    output(**result)


def unresolved_items(db: sqlite3.Connection, args: argparse.Namespace) -> None:
    rows = db.execute("SELECT run_id,token,status,created_at,updated_at,candidate_hash FROM candidates WHERE status IN ('pending','unknown') ORDER BY created_at").fetchall()
    later=db.execute("SELECT * FROM message_attempts WHERE message_index>1 AND status IN ('pending','dispatching','unknown') ORDER BY created_at").fetchall()
    output(state="unresolved", items=[dict(row) for row in rows]+[dict(row) for row in later])


def assessment_eligible(run, assessment):
    rules = recruiting_rules.run_rules(run)
    result = recruiting_rules.from_assessment(assessment)
    if "evaluation_input" in assessment.keys() and assessment["evaluation_input"]:
        result = recruiting_rules.evaluate(rules,json.loads(assessment["evaluation_input"]),run["min_score"])
    if rules.get("policy","legacy") != "legacy":
        return bool(result.get("eligible"))
    return assessment["overall_score"] >= run["min_score"] and (assessment["hard_requirements"] == "true" or assessment["hard_requirement_override"] == "true")

for _mutation_name in ("candidate_begin","electronic_opened","candidate_finish","reserve","resolve","note"):
    globals()[_mutation_name] = run_safety.fenced(globals()[_mutation_name])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("profile-check")
    check.add_argument("--profile", required=True)
    begin = commands.add_parser("start")
    begin.add_argument("--profile", required=True)
    begin.add_argument("--stop-binding", type=Path, help="Validated chat-specific stop binding JSON; mandatory for new policies")
    begin.add_argument("--target", type=int, default=150)
    begin.add_argument("--duration-min", type=int, default=240)
    begin.add_argument("--min-score", type=int, default=70)
    view = commands.add_parser("status")
    view.add_argument("--run")
    commands.add_parser("runs")
    action = commands.add_parser("control")
    action.add_argument("--run", required=True)
    action.add_argument("--action", required=True, choices=("pause", "resume", "stop", "login-required", "login-confirmed"))
    action.add_argument("--reason", choices=("session_expired", "risk_logout"), default="session_expired")
    action.add_argument("--manual-confirmed", action="store_true")
    gate_command = commands.add_parser("gate")
    gate_command.add_argument("--run", required=True)
    for name in ("candidate-begin", "electronic-opened", "candidate-finish"):
        progress_command = commands.add_parser(name)
        progress_command.add_argument("--run", required=True)
        progress_command.add_argument("--candidate-id", required=True)
    begin_candidate = commands.choices["candidate-begin"]
    begin_candidate.add_argument(
        "--started-at",
        help="ISO timestamp captured immediately before the switch/list click that opened this candidate",
    )
    finish_candidate = commands.choices["candidate-finish"]
    finish_candidate.add_argument(
        "--ended-at",
        help="ISO timestamp captured immediately after the next-resume switch click",
    )
    live = commands.add_parser("watch")
    live.add_argument("--run", required=True)
    live.add_argument("--interval", type=int, default=5)
    commands.add_parser("unresolved")
    hold = commands.add_parser("reserve")
    hold.add_argument("--run", required=True)
    hold.add_argument("--candidate-id", required=True)
    mark = commands.add_parser("resolve")
    mark.add_argument("--token", required=True)
    mark.add_argument("--result", required=True, choices=("sent", "not-sent", "unknown"))
    mark.add_argument("--min-gap", type=int, default=64)
    mark.add_argument("--max-gap", type=int, default=80)
    tag = commands.add_parser("note")
    tag.add_argument("--run", required=True)
    tag.add_argument("--candidate-id", required=True)
    tag.add_argument("--result", required=True, choices=("skipped", "review"))
    fix = commands.add_parser("reconcile")
    fix.add_argument("--token", required=True)
    fix.add_argument("--result", required=True, choices=("sent", "not-sent"))
    fix.add_argument("--manual-confirmed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "profile-check":
            ok, reason, fields = profile_check(Path(args.profile))
            output(state="ready" if ok else "blocked", reason=reason, company=fields.get("company"), position=fields.get("position"))
            return
        with connect(args.db) as db:
            {"start": start, "status": status, "runs": recent_runs, "control": control, "gate": gate, "candidate-begin": candidate_begin,
             "electronic-opened": electronic_opened, "candidate-finish": candidate_finish,
             "watch": watch, "unresolved": unresolved_items, "reserve": reserve,
             "resolve": resolve, "note": note, "reconcile": reconcile}[args.command](db, args)
    except (OSError, ValueError, sqlite3.Error) as exc:
        output(state="error", reason=str(exc))
        sys.exit(2)


if __name__ == "__main__":
    main()
