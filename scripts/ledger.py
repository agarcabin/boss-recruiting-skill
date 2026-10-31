"""Local, privacy-minimal ledger for one-at-a-time BOSS greeting runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
import coworker_progress
import recruiting_rules
import run_safety
import run_targets
from datetime import datetime, timedelta, timezone
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


DEFAULT_TARGET = 150
DEFAULT_MAX_VIEWS = 300
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
    columns = {row[1] for row in db.execute("PRAGMA table_info(runs)")}
    if "max_views" not in columns:
        db.execute("ALTER TABLE runs ADD COLUMN max_views INTEGER NOT NULL DEFAULT 300")
    db.executescript("""CREATE TABLE IF NOT EXISTS candidate_visits (
        run_id TEXT NOT NULL, candidate_id TEXT NOT NULL, candidate_hash TEXT NOT NULL,
        ordinal INTEGER NOT NULL, PRIMARY KEY(run_id,candidate_hash));
        CREATE INDEX IF NOT EXISTS visits_candidate ON candidate_visits(run_id,candidate_id,ordinal);""")
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
        fields["_warnings"] = "岗位未审核，仅提醒，不阻止运行"
    required_sections = ("页面核验", "企业与岗位事实", "自动筛选条件", "评分规则", "加分项", "待人工确认", "固定招呼话术", "冲突与待确认", "来源")
    if any(f"## {title}" not in content for title in required_sections):
        fields["_warnings"] = fields.get("_warnings", "") + "; 岗位章节不完整"
    if re.search(r"(?m)^\s*-\s*\[\s*\]", content):
        fields["_warnings"] = fields.get("_warnings", "") + "; 岗位配置存在未解决事项"
    for title in ("页面核验", "企业与岗位事实", "自动筛选条件", "评分规则", "固定招呼话术"):
        section = re.search(rf"(?ms)^## {title}\s*\n(.*?)(?=^## |\Z)", content)
        if section and re.search(r"待确认|尚未确认|待审核|需确认|未决", section.group(1)):
            fields["_warnings"] = fields.get("_warnings", "") + "; 岗位内容有待确认事项"
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
    reason = run_safety.quantity_reason(db, args.run) if state == "running" else None
    active = active_progress(db, args.run)
    output(state="draining" if reason and active and state == "running" else state,
           may_continue=state == "running" and (not reason or active is not None),
           may_start_candidate=state == "running" and not reason, drain_reason=reason,
           generation=run_row(db,args.run)["generation"])


def run_candidate_hash(db, run_id, candidate_id):
    row = db.execute("SELECT candidate_hash FROM candidate_visits WHERE run_id=? AND candidate_id=? ORDER BY ordinal DESC LIMIT 1", (run_id, candidate_id)).fetchone()
    if row:
        return row[0]
    run = run_row(db, run_id)
    return candidate_hash(run_namespace(run), candidate_id)


def ensure_candidate(db, run_id, candidate_id, started_at=None, new_visit=False):
    """Accounting is automatic; a previous visit is never an exclusion rule."""
    active = active_progress(db, run_id)
    digest = run_candidate_hash(db, run_id, candidate_id)
    if active and active['candidate_hash'] == digest and not new_visit:
        return active
    stamp = iso(now())
    if active:
        db.execute("UPDATE candidate_progress SET finished_at=? WHERE run_id=? AND candidate_hash=?", (stamp, run_id, active['candidate_hash']))
        db.execute("INSERT INTO run_audit(run_id,at,event,detail) VALUES (?,?,?,?)", (run_id,stamp,'candidate_auto_closed','next candidate; optional report/timing may be incomplete'))
    reason = run_safety.quantity_reason(db, run_id)
    if reason:
        raise ValueError(reason)
    ordinal = db.execute("SELECT COALESCE(MAX(ordinal),0)+1 FROM candidate_progress WHERE run_id=?", (run_id,)).fetchone()[0]
    digest = uuid.uuid4().hex + uuid.uuid4().hex
    try:
        started = iso(parse_timestamp_argument(started_at, now()))
    except (ValueError, TypeError):
        started = stamp
    db.execute("INSERT INTO candidate_visits VALUES (?,?,?,?)", (run_id,candidate_id,digest,ordinal))
    db.execute("INSERT INTO candidate_progress VALUES (?,?,?,?,?,?)", (run_id,digest,ordinal,started,None,None))
    return active_progress(db,run_id)


def run_namespace(run, fields=None):
    if run["candidate_namespace"]:
        return run["candidate_namespace"]
    if fields is None:
        _, _, fields = profile_check(Path(run["profile_path"]))
    return fields.get("candidate_namespace") or f"{fields.get('company','')}-{fields.get('position','')}"


def active_progress(db: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM candidate_progress WHERE run_id=? AND finished_at IS NULL", (run_id,)).fetchone()


def candidate_begin(db, args):
    active = ensure_candidate(db,args.run,args.candidate_id,getattr(args,'started_at',None),getattr(args,'new_visit',False))
    output(state='started_candidate',current_candidate_number=active['ordinal'],candidate_started_at=active['started_at'])


def electronic_opened(db, args):
    active = ensure_candidate(db,args.run,args.candidate_id)
    db.execute("UPDATE candidate_progress SET electronic_opened_at=COALESCE(electronic_opened_at,?) WHERE run_id=? AND candidate_hash=?",(iso(now()),args.run,active['candidate_hash']))
    output(state='electronic_opened',current_candidate_number=active['ordinal'])


def candidate_finish(db,args):
    digest = run_candidate_hash(db,args.run,args.candidate_id)
    row = db.execute("SELECT * FROM candidate_progress WHERE run_id=? AND candidate_hash=?",(args.run,digest)).fetchone()
    if row is None:
        output(state='finished_candidate',warnings=['没有候选人登记；已略过可选收尾'])
        return
    stamp = iso(now())
    supplied = getattr(args,'ended_at',None)
    if supplied:
        try: stamp = iso(parse_time(supplied))
        except (ValueError,TypeError): pass
    db.execute("UPDATE candidate_progress SET finished_at=COALESCE(finished_at,?) WHERE run_id=? AND candidate_hash=?",(stamp,args.run,digest))
    output(state='finished_candidate',current_candidate_number=row['ordinal'],candidate_ended_at=stamp)


def start(db,args):
    path = Path(args.profile).resolve()
    if not path.is_relative_to(PROFILE_ROOT.resolve()):
        output(state='blocked',reason='profile_outside_skill_profiles'); return
    ok,reason,fields = profile_check(path)
    if not ok:
        output(state='blocked',reason=reason); return
    target,views=run_targets.resolve(getattr(args,'target',None),getattr(args,'max_views',None))
    if not isinstance(target,int) or target < 1 or not isinstance(views,int) or views < 1 or not 0 <= args.min_score <= 100:
        raise ValueError('target/max_views must be positive integers; min_score 0..100')
    rules = recruiting_rules.snapshot(path,fields,getattr(args,'greeting_mode',None))
    binding = None
    warnings = [fields['_warnings']] if fields.get('_warnings') else []
    if getattr(args,'stop_binding',None):
        import stop_controller
        try: binding = stop_controller.load_binding(Path(args.stop_binding))
        except (ValueError,OSError) as exc: warnings.append('optional stop binding: '+str(exc))
    at = iso(now()); run_id = uuid.uuid4().hex
    db.execute("INSERT INTO runs(run_id,started_at,deadline_at,target,profile_path,profile_hash,min_score,max_views) VALUES (?,?,?,?,?,?,?,?)",(run_id,at,'',target,str(path),profile_hash(path),args.min_score,views))
    db.execute("UPDATE runs SET candidate_namespace=?,evaluation_mode=?,rule_snapshot=?,stop_binding=? WHERE run_id=?",(rules['namespace'],rules['mode'],json.dumps(rules,ensure_ascii=False),json.dumps(binding) if binding else None,run_id))
    db.execute("INSERT INTO run_control(run_id,state,updated_at) VALUES (?,?,?)",(run_id,'running',at))
    output(state='started',run_id=run_id,company=fields['company'],position=fields['position'],greeting_mode=rules['greeting_mode'],min_score=args.min_score,target=target,max_views=views,deadline_at=None,warnings=warnings,chat_title=f"{fields['company']} {fields['position']} - {now().astimezone(timezone(timedelta(hours=8))).date().isoformat()}",startup_actions=['set_current_chat_title','collapse_chat_sidebar','confirm_login_prompt_if_present'])


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
        details = {"run_id": args.run, "target": row["target"], "min_score": row["min_score"], "greeting_mode": recruiting_rules.run_greeting_mode(row),
                   "run_state": control_state(db, args.run),
                   "started_at": row["started_at"], "deadline_at": row["deadline_at"], "run_expired": False,
                   "elapsed_seconds": elapsed, "elapsed_display": f"{elapsed // 3600:02d}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",
                   "current_candidate_number": active["ordinal"] if active else None, "current_stage": current_stage,
                   "candidates_started": progress["started"], "candidates_completed": progress["finished"], "view_remaining": max(0, row["max_views"]-progress["started"]),
                   "electronic_resume_opened_candidates": progress["electronic_opened"], "greetings_sent": counts.get("sent", 0)}
    import greeting_rate
    output(state="status", rolling_sent=rolling_count(db, at), rolling_remaining=None, unresolved=unresolved(db), next_allowed_at=None, counts=counts, rate_limit=greeting_rate.status(db,at), **details)


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
        expired = False
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
            if state == "stopped":
                return
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return


def reserve(db,args):
    import greeting_rate
    with greeting_rate.transaction(db):
        return _reserve(db,args)


def _reserve(db,args):
    run = run_row(db,args.run)
    ok,reason,fields = profile_check(Path(run['profile_path']))
    if not ok:
        output(state='blocked',reason=reason); return
    if profile_hash(Path(run['profile_path'])) != run['profile_hash']:
        output(state='blocked',reason='profile_changed_since_start'); return
    digest = run_candidate_hash(db,args.run,args.candidate_id)
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='assessments'").fetchone()
    assessment = db.execute("SELECT * FROM assessments WHERE run_id=? AND candidate_hash=?",(args.run,digest)).fetchone() if exists else None
    if not assessment or assessment['decision']!='greet' or not assessment_eligible(run,assessment):
        output(state='blocked',reason='assessment_not_eligible'); return
    if assessment['evaluation_mode']!='card':
        coworker = coworker_progress.evaluate(json.loads(assessment['coworker_progress'] or '{}'),now())
        if not coworker['may_continue']:
            output(state='blocked',reason=coworker['reason']); return
    if db.execute("SELECT COUNT(*) FROM candidates WHERE run_id=? AND status='sent'",(args.run,)).fetchone()[0] >= run['target']:
        output(state='blocked',reason='run_target_reached'); return
    previous=db.execute('SELECT * FROM candidates WHERE candidate_hash=?',(digest,)).fetchone()
    if previous and previous['status']=='sent':
        output(state='already_sent',token=previous['token']);return
    if previous and previous['status']=='pending':
        import greeting_rate
        rate=greeting_rate.claim(db,digest)
        if rate['state']=='rate_limited':output(**rate);return
        output(state='ready',token=previous['token'],reused=True);return
    import greeting_rate
    rate=greeting_rate.claim(db,digest)
    if rate['state']=='rate_limited':output(**rate);return
    token=uuid.uuid4().hex;stamp=iso(now())
    if previous:
        db.execute("""CREATE TABLE IF NOT EXISTS message_attempt_history (
            token TEXT PRIMARY KEY,run_id TEXT NOT NULL,candidate_hash TEXT NOT NULL,
            message_index INTEGER NOT NULL,status TEXT NOT NULL,generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
        db.execute('CREATE INDEX IF NOT EXISTS attempt_history_candidate ON message_attempt_history(candidate_hash,message_index,created_at)')
        db.execute('INSERT OR IGNORE INTO message_attempt_history SELECT * FROM message_attempts WHERE run_id=? AND candidate_hash=? AND message_index=1',(args.run,digest))
        db.execute("UPDATE candidates SET status='pending',token=?,updated_at=? WHERE candidate_hash=?",(token,stamp,digest))
    else:
        db.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)',(digest,run_namespace(run,fields),args.run,'pending',token,stamp,None,stamp))
    db.execute('INSERT INTO message_attempts VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(run_id,candidate_hash,message_index) DO UPDATE SET token=excluded.token,status=excluded.status,created_at=excluded.created_at,updated_at=excluded.updated_at',(token,args.run,digest,1,'pending',run['generation'],stamp,stamp))
    output(state='ready',token=token,warnings=[fields['_warnings']] if fields.get('_warnings') else [])


def resolve(db,args):
    row=db.execute('SELECT * FROM message_attempts WHERE token=?',(args.token,)).fetchone()
    history_exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='message_attempt_history'").fetchone()
    historical=False
    if row is None and history_exists:
        row=db.execute('SELECT * FROM message_attempt_history WHERE token=?',(args.token,)).fetchone();historical=bool(row)
    if row is None:
        output(state='not_found',reason='record_not_found');return
    stamp=iso(now());table='message_attempt_history' if historical else 'message_attempts'
    db.execute('UPDATE '+table+' SET status=?,updated_at=? WHERE token=?',(args.result,stamp,args.token))
    sent=db.execute("SELECT updated_at FROM message_attempts WHERE candidate_hash=? AND message_index=1 AND status='sent' ORDER BY updated_at LIMIT 1",(row['candidate_hash'],)).fetchone()
    if sent is None and history_exists:
        sent=db.execute("SELECT updated_at FROM message_attempt_history WHERE candidate_hash=? AND message_index=1 AND status='sent' ORDER BY updated_at LIMIT 1",(row['candidate_hash'],)).fetchone()
    if sent:
        db.execute("UPDATE candidates SET status='sent',sent_at=COALESCE(sent_at,?),updated_at=? WHERE candidate_hash=?",(sent[0],stamp,row['candidate_hash']))
    elif not historical:
        db.execute('UPDATE candidates SET status=?,updated_at=? WHERE token=?',(args.result,stamp,args.token))
    db.execute("DELETE FROM settings WHERE key='next_allowed_at'")
    output(state=args.result,next_allowed_at=None,requires_manual_reconciliation=False)


def note(db,args):
    run=run_row(db,args.run)
    digest=run_candidate_hash(db,args.run,args.candidate_id)
    active=db.execute('SELECT * FROM candidate_progress WHERE run_id=? AND candidate_hash=?',(args.run,digest)).fetchone()
    if active is None:active=ensure_candidate(db,args.run,args.candidate_id)
    digest=active['candidate_hash']; stamp=iso(now())
    previous=db.execute('SELECT 1 FROM candidates WHERE candidate_hash=?',(digest,)).fetchone()
    if not previous:
        db.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)',(digest,run_namespace(run),args.run,args.result,None,stamp,None,stamp))
    output(state='noted',result=args.result)


def reconcile(db,args):
    # Compatibility command: recorded outcomes can be corrected without manual-confirmed.
    resolve(db,args)


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
    begin.add_argument("--stop-binding", type=Path, help="Optional chat stop binding; never required to start")
    begin.add_argument("--target", type=int, default=DEFAULT_TARGET)
    begin.add_argument("--max-views", type=int, help="If omitted, max(300, greeting target)")
    begin.add_argument("--duration-min", type=int, help="Deprecated compatibility argument; ignored")
    begin.add_argument("--min-score", type=int, default=70)
    begin.add_argument("--greeting-mode", choices=("single", "triple"), help="Override this run's greeting mode; new projects default to single")
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
    begin_candidate.add_argument("--new-visit",action="store_true",help="A genuine new opening; never use for retry/sync")
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
    mark.add_argument("--min-gap", type=int, default=0)
    mark.add_argument("--max-gap", type=int, default=0)
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
            output(state="ready" if ok else "blocked", reason=reason, warnings=fields.get("_warnings"), company=fields.get("company"), position=fields.get("position"))
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
