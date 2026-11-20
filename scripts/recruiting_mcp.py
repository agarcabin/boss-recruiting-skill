"""Local MCP control plane for the recruiting workflow.

The recruiting runner and the overlay remain the data plane (SQLite + workflow
files). This server gives the agent typed access to the same state instead of
hand-written paths and response files.
"""
from __future__ import annotations

import json
import os
import base64
import inspect
import shutil
import sqlite3
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any, Union, get_args, get_origin

SKILL_ROOT = Path(
    os.environ.get("BOSS_SKILL_ROOT", str(Path(__file__).resolve().parents[1]))
)
RUNTIME_PYTHON = SKILL_ROOT / "runtime" / "win-x64" / "python" / "python.exe"
if not RUNTIME_PYTHON.is_file():
    RUNTIME_PYTHON = Path(sys.executable)
LEDGER_SCRIPT = SKILL_ROOT / "scripts" / "ledger.py"
_LOCAL_APP_DATA = Path(
    os.environ.get("USERPROFILE") or str(Path.home())
) / "AppData" / "Local"
STATE_DIR = Path(
    os.environ.get("BOSS_STATE_DIR")
    or (_LOCAL_APP_DATA / "Codex" / "recruiting-greetings")
)
DB_PATH = STATE_DIR / "ledger.sqlite3"
WORKFLOW_ROOT = STATE_DIR / "workflow"

TOOLS: dict[str, Any] = {}


class _ToolRegistry:
    def tool(self):
        def register(function):
            TOOLS[function.__name__] = function
            return function

        return register


mcp = _ToolRegistry()


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=20, factory=_ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 20000")
    return db


def _skill_json(script: str, *args: str, timeout: int = 60) -> dict[str, Any]:
    run_env = os.environ.copy()
    run_env["LOCALAPPDATA"] = str(_LOCAL_APP_DATA)
    run_env["BOSS_STATE_DIR"] = str(STATE_DIR)
    completed = subprocess.run(
        [str(RUNTIME_PYTHON), str(SKILL_ROOT / "scripts" / script), *map(str, args)],
        cwd=str(SKILL_ROOT / "scripts"),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        timeout=timeout,
        env=run_env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode:
        raise ValueError((completed.stderr or completed.stdout or script + "_failed")[-1200:])
    return json.loads(completed.stdout)


def _pwsh() -> str:
    host = shutil.which("pwsh")
    if not host:
        bundled = (
            Path.home()
            / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe"
        )
        if bundled.is_file():
            host = str(bundled)
    if not host:
        raise ValueError("pwsh_required_for_mcp_start")
    return host


def _ps_json(
    script: str, *args: str, timeout: int = 40, env: dict[str, str] | None = None
) -> dict[str, Any]:
    run_env = os.environ.copy()
    run_env["LOCALAPPDATA"] = str(_LOCAL_APP_DATA)
    run_env["BOSS_STATE_DIR"] = str(STATE_DIR)
    if env:
        run_env.update(env)
    completed = subprocess.run(
        [
            _pwsh(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-STA",
            "-File",
            str(SKILL_ROOT / "scripts" / script),
            *map(str, args),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        timeout=timeout,
        env=run_env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode:
        raise ValueError((completed.stderr or completed.stdout or script + "_failed")[-1200:])
    return json.loads(completed.stdout)


def _active_runs(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute(
        """SELECT r.run_id,r.profile_path,r.target,rc.state
           FROM runs r JOIN run_control rc ON rc.run_id=r.run_id
           WHERE r.stop_reason IS NULL AND rc.state!='stopped'"""
    ).fetchall()
    return [
        {
            "run_id": str(row["run_id"]),
            "company_position": f"{Path(str(row['profile_path'])).parent.name} - {Path(str(row['profile_path'])).stem}",
            "target": int(row["target"]),
            "control": str(row["state"]),
        }
        for row in rows
    ]


def _close_overlay(run_id: str) -> dict[str, Any]:
    if not run_id.replace("_", "").replace("-", "").isalnum():
        raise ValueError("invalid_run_id")
    script = (
        "$p=Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\";"
        "$hits=@($p|Where-Object {$_.CommandLine -like '*progress_window.py*' -and "
        f"$_.CommandLine -like '*{run_id}*'}});"
        "foreach($h in $hits){Stop-Process -Id $h.ProcessId -Force};"
        "$hits.Count|ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [_pwsh(), "-NoProfile", "-Command", script],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode:
        return {"state": "warning", "reason": (completed.stderr or "overlay_close_failed")[-300:]}
    try:
        count = int(completed.stdout.strip() or 0)
    except ValueError:
        count = 0
    return {"state": "closed" if count else "absent", "closed": count}


def _cursor_values(db: sqlite3.Connection, run: sqlite3.Row) -> dict[str, Any]:
    rid = str(run["run_id"])
    phase, payload = _workflow(db, rid)
    request_file = payload.get("request_file")
    response_file = payload.get("response_file")
    request_mtime = (
        Path(request_file).stat().st_mtime_ns
        if request_file and Path(request_file).is_file()
        else 0
    )
    counts = _counts(db, rid)
    return {
        "control": _control_state(db, rid),
        "phase": phase,
        "sent": counts["sent"],
        "skipped": counts["skipped"],
        "review": counts["review"],
        "stop": run["stop_reason"],
        "handoff": bool(
            request_file
            and Path(request_file).is_file()
            and not (response_file and Path(response_file).is_file())
        ),
        "request": f"{request_file}:{request_mtime}",
    }


def _cursor_encode(values: dict[str, Any]) -> str:
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def _cursor_decode(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        result = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (TypeError, ValueError):
        try:
            result = json.loads(value)
        except (TypeError, ValueError):
            return None
    return result if isinstance(result, dict) else None


def _latest_run_id(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT run_id FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if not row:
        raise ValueError("no_recruiting_run")
    return str(row["run_id"])


def _run_row(db: sqlite3.Connection, run_id: str | None) -> sqlite3.Row:
    rid = run_id or _latest_run_id(db)
    row = db.execute("SELECT * FROM runs WHERE run_id=?", (rid,)).fetchone()
    if not row:
        raise ValueError("run_not_found")
    return row


def _counts(db: sqlite3.Connection, run_id: str) -> dict[str, int]:
    result = {"sent": 0, "skipped": 0, "review": 0, "other": 0}
    for row in db.execute(
        "SELECT status, COUNT(*) AS n FROM candidates WHERE run_id=? GROUP BY status",
        (run_id,),
    ):
        key = str(row["status"])
        result[key if key in result else "other"] += int(row["n"])
    return result


def _watchdog(db: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = db.execute(
        "SELECT value FROM settings WHERE key=?", ("chat_watchdog/" + run_id,)
    ).fetchone()
    if not row:
        return {}
    try:
        return json.loads(row["value"])
    except (TypeError, ValueError):
        return {}


def _workflow(db: sqlite3.Connection, run_id: str) -> tuple[str | None, dict[str, Any]]:
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='workflow_state'"
    ).fetchone():
        return None, {}
    row = db.execute(
        "SELECT phase,payload FROM workflow_state WHERE run_id=?", (run_id,)
    ).fetchone()
    if not row:
        return None, {}
    try:
        payload = json.loads(row["payload"])
    except (TypeError, ValueError):
        payload = {}
    return row["phase"], payload


def _control_state(db: sqlite3.Connection, run_id: str) -> str:
    row = db.execute("SELECT state FROM run_control WHERE run_id=?", (run_id,)).fetchone()
    return str(row["state"]) if row else "unknown"


def _status(db: sqlite3.Connection, run: sqlite3.Row) -> dict[str, Any]:
    rid = str(run["run_id"])
    phase, payload = _workflow(db, rid)
    profile = Path(str(run["profile_path"]))
    return {
        "run_id": rid,
        "company_position": f"{profile.parent.name} - {profile.stem}",
        "profile_path": str(run["profile_path"]),
        "target": int(run["target"]),
        "max_views": int(run["max_views"]),
        "control": _control_state(db, rid),
        "stop_reason": run["stop_reason"],
        "finalized_at": run["finalized_at"],
        "report_path": run["report_path"],
        "counts": _counts(db, rid),
        "phase": phase,
        "handoff_kind": payload.get("handoff_kind"),
        "request_file": payload.get("request_file"),
        "response_file": payload.get("response_file"),
        "notice_wait": payload.get("notice_wait"),
        "watchdog": _watchdog(db, rid),
    }


def _pending_handoff(db: sqlite3.Connection, run: sqlite3.Row) -> dict[str, Any] | None:
    rid = str(run["run_id"])
    phase, payload = _workflow(db, rid)
    request_file = payload.get("request_file")
    response_file = payload.get("response_file")
    if not request_file or not Path(request_file).is_file():
        return None
    if response_file and Path(response_file).is_file():
        return None
    try:
        request = json.loads(Path(request_file).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeError):
        return None
    return {
        "run_id": rid,
        "phase": phase,
        "kind": payload.get("handoff_kind") or request.get("kind"),
        "request_file": str(request_file),
        "response_file": str(response_file) if response_file else None,
        "request": request,
    }


def _signature(db: sqlite3.Connection, run: sqlite3.Row) -> str:
    rid = str(run["run_id"])
    phase, payload = _workflow(db, rid)
    request_file = payload.get("request_file")
    response_file = payload.get("response_file")
    request_mtime = Path(request_file).stat().st_mtime_ns if request_file and Path(request_file).is_file() else 0
    response_exists = bool(response_file and Path(response_file).is_file())
    return "|".join(
        [
            rid,
            _control_state(db, rid),
            str(phase),
            str(request_file),
            str(request_mtime),
            str(response_exists),
            json.dumps(_counts(db, rid), sort_keys=True),
            str(run["stop_reason"]),
        ]
    )


def _expected_id(request: dict[str, Any]) -> tuple[str | None, str | None]:
    evidence = request.get("evidence") or {}
    if request.get("kind") in ("overall_review", "misjudgment_review"):
        return "request_id", evidence.get("request_id")
    if request.get("kind") in ("filter_notice", "coworker_notice"):
        return "notice_id", evidence.get("notice_id")
    return None, None


@mcp.tool()
def recruiting_runs(limit: int = 5) -> dict[str, Any]:
    """List recent recruiting runs with control state and greeting counts."""
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (max(1, min(limit, 20)),)
        ).fetchall()
        return {
            "state": "read",
            "runs": [
                {
                    "run_id": str(row["run_id"]),
                    "company_position": f"{Path(str(row['profile_path'])).parent.name} - {Path(str(row['profile_path'])).stem}",
                    "target": int(row["target"]),
                    "control": _control_state(db, str(row["run_id"])),
                    "stop_reason": row["stop_reason"],
                    "counts": _counts(db, str(row["run_id"])),
                    "started_at": row["started_at"],
                }
                for row in rows
            ],
        }


@mcp.tool()
def recruiting_status(run_id: str | None = None) -> dict[str, Any]:
    """Return one run's control state, phase, counts, report and GPT monitor."""
    with _connect() as db:
        run = _run_row(db, run_id)
        return {"state": "read", **_status(db, run)}


@mcp.tool()
def recruiting_handoff(run_id: str | None = None) -> dict[str, Any]:
    """Read the pending AI handoff for a run, if any."""
    with _connect() as db:
        run = _run_row(db, run_id)
        pending = _pending_handoff(db, run)
        if pending:
            return {"state": "pending", **pending}
        return {"state": "none", **_status(db, run)}


@mcp.tool()
def recruiting_respond(run_id: str, response: dict[str, Any]) -> dict[str, Any]:
    """Write one validated response for the current pending handoff."""
    with _connect() as db:
        run = _run_row(db, run_id)
        pending = _pending_handoff(db, run)
        if not pending:
            raise ValueError("no_pending_handoff")
        key, expected = _expected_id(pending["request"])
        if key and expected and response.get(key) != expected:
            raise ValueError(f"{key}_mismatch")
        if not isinstance(response, dict) or not response:
            raise ValueError("empty_response")
        path = Path(pending["response_file"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, path)
        return {
            "state": "accepted",
            "run_id": run_id,
            "kind": pending["kind"],
            "response_file": str(path),
        }


@mcp.tool()
def recruiting_control(run_id: str, action: str) -> dict[str, Any]:
    """Pause, resume or stop a run through the existing ledger controller."""
    if action not in ("pause", "resume", "stop"):
        raise ValueError("action_must_be_pause_resume_or_stop")
    completed = subprocess.run(
        [
            str(RUNTIME_PYTHON),
            str(LEDGER_SCRIPT),
            "control",
            "--run",
            run_id,
            "--action",
            action,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if completed.returncode:
        raise ValueError((completed.stderr or completed.stdout or "control_failed")[-800:])
    try:
        result = json.loads(completed.stdout)
    except ValueError:
        result = {"state": "unknown", "output": completed.stdout[-800:]}
    return {"state": "read", "run_id": run_id, "action": action, "result": result}


def _name_match(expected: str, observed: str | None) -> bool:
    if not observed:
        return False
    expected, observed = expected.strip(), observed.strip()
    return bool(expected and observed and (expected in observed or observed in expected))


def _wait_stopped(db: sqlite3.Connection, run_id: str, seconds: int = 25) -> sqlite3.Row:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        run = _run_row(db, run_id)
        if run["stop_reason"]:
            return run
        time.sleep(1)
    return _run_row(db, run_id)


@mcp.tool()
def recruiting_start(
    company: str,
    position: str,
    target: int,
    chat_title: str | None = None,
    replace_existing: bool = False,
    allow_page_mismatch: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Prepare and start one recruiting run in a single call.

    The caller must set the Codex chat title first. This tool preflights the
    active run, chat window, BOSS page, and then starts the runner and overlay.
    Set dry_run=True to validate without creating a run or sending greetings.
    """
    target = max(1, min(int(target), 150))
    prompt = f"帮我打{company} {position} {target} 个"
    prepared = _skill_json("quick_start.py", "--prompt", prompt)
    if prepared.get("state") != "ready_to_start":
        return {
            "state": "blocked",
            "reason": "job_not_unique",
            "prompt": prompt,
            "prepared_state": prepared.get("state"),
            "menu_text": prepared.get("menu_text"),
        }
    plan_title = prepared.get("chat_title") or chat_title
    plan_file = prepared.get("plan_file")
    if not plan_file:
        return {"state": "blocked", "reason": "startup_plan_missing", "prompt": prompt}
    if chat_title and chat_title != plan_title:
        return {
            "state": "blocked",
            "reason": "chat_title_mismatch",
            "required_chat_title": plan_title,
            "provided_chat_title": chat_title,
        }
    with _connect() as db:
        active = _active_runs(db)
    try:
        resolved = _ps_json(
            "resolve-recruiting-window.ps1", "-ChatTitle", str(plan_title)
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        resolved = {"state": "unavailable", "reason": str(exc)[-300:]}
    if resolved.get("state") != "resolved":
        return {
            "state": "blocked",
            "reason": "chat_title_mismatch",
            "required_chat_title": plan_title,
            "provided_chat_title": chat_title,
            "window": resolved,
            "active_runs": active,
        }
    hwnd = int(resolved["window"]["hwnd"])
    binding = SKILL_ROOT / "runtime" / f"mcp-binding-{int(time.time())}.json"
    try:
        bound = _ps_json(
            "bind-boss-browser.ps1",
            "-WindowHandle",
            str(hwnd),
            "-ChatTitle",
            str(plan_title),
            "-OutputFile",
            str(binding),
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {
            "state": "blocked",
            "reason": "boss_binding_failed",
            "chat_title": plan_title,
            "detail": str(exc)[-600:],
            "active_runs": active,
        }
    try:
        page = _ps_json(
            "workflow-uia.ps1",
            "-Action",
            "PageJob",
            "-WindowHandle",
            str(hwnd),
            env={"BOSS_BROWSER_BINDING": str(binding)},
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        page = {"state": "unknown", "reason": str(exc)[-300:], "display_name": None}
    page_name = page.get("display_name")
    page_mismatch = bool(
        page_name
        and not (_name_match(company, page_name) and _name_match(position, page_name))
    )
    warnings = []
    if not page_name:
        warnings.append("无法读取 BOSS 右上角岗位名称，未阻止启动")
    if page_mismatch and not allow_page_mismatch:
        return {
            "state": "blocked",
            "reason": "boss_page_job_mismatch",
            "required": f"{company} / {position}",
            "observed": page_name,
            "page": page,
            "active_runs": active,
        }
    if dry_run:
        return {
            "state": "ready",
            "dry_run": True,
            "prompt": prompt,
            "plan_file": plan_file,
            "chat_title": plan_title,
            "binding_file": str(binding),
            "window": resolved.get("window"),
            "page": page,
            "page_mismatch": page_mismatch,
            "active_runs": active,
            "warnings": warnings,
        }
    if active:
        if not replace_existing:
            return {
                "state": "blocked",
                "reason": "active_run",
                "active_runs": active,
                "hint": "先结束现有运行，或传 replace_existing=true",
            }
        for item in active:
            _skill_json("ledger.py", "control", "--run", item["run_id"], "--action", "stop")
            with _connect() as db:
                _wait_stopped(db, item["run_id"])
            _close_overlay(item["run_id"])
    started = _skill_json(
        "quick_start.py", "--plan", str(plan_file), "--start-direct", timeout=90
    )
    if started.get("state") != "started" or not started.get("run"):
        return {"state": "blocked", "reason": "start_failed", "started": started}
    run_id = started["run"]["run_id"]
    try:
        overlay = _skill_json(
            "launch_progress.py", "--run", run_id, "--chat-title", str(plan_title), timeout=60
        )
        runner = _skill_json(
            "workflow_runner.py",
            "--run",
            run_id,
            "--browser-binding",
            str(binding),
            "--launch",
            timeout=60,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        try:
            _skill_json("ledger.py", "control", "--run", run_id, "--action", "stop")
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        _close_overlay(run_id)
        return {
            "state": "blocked",
            "reason": "runner_launch_failed",
            "run_id": run_id,
            "chat_title": plan_title,
            "detail": str(exc)[-600:],
        }
    return {
        "state": "started",
        "run_id": run_id,
        "chat_title": plan_title,
        "binding_file": str(binding),
        "overlay": overlay,
        "runner": runner,
        "page": page,
        "page_mismatch": page_mismatch,
        "warnings": warnings,
    }


@mcp.tool()
def recruiting_finish(run_id: str, open_report: bool = False) -> dict[str, Any]:
    """Stop a run, close its overlay, and return the final report path."""
    with _connect() as db:
        run = _run_row(db, run_id)
        control = _control_state(db, run_id)
    if control != "stopped" or not run["stop_reason"]:
        _skill_json("ledger.py", "control", "--run", run_id, "--action", "stop")
        with _connect() as db:
            run = _wait_stopped(db, run_id)
    overlay = _close_overlay(run_id)
    report = run["report_path"]
    opened = False
    if open_report and report and Path(str(report)).is_file():
        os.startfile(str(report))
        opened = True
    with _connect() as db:
        status = _status(db, _run_row(db, run_id))
    return {
        "state": "finished" if run["stop_reason"] else "stopping",
        "open_report": opened,
        "overlay": overlay,
        **status,
    }


@mcp.tool()
def recruiting_candidates(
    run_id: str | None = None, status: str = "all", limit: int = 50
) -> dict[str, Any]:
    """List assessed candidates with decision, score and reason for review."""
    if status not in ("all", "sent", "skipped", "review"):
        raise ValueError("status_must_be_all_sent_skipped_or_review")
    limit = max(1, min(int(limit), 200))
    with _connect() as db:
        run = _run_row(db, run_id)
        rid = str(run["run_id"])
        rows = db.execute(
            """SELECT a.candidate_hash,a.candidate_name,a.decision,a.overall_score,
                      a.cons,a.eligibility_json,a.updated_at,c.status
               FROM assessments a
               LEFT JOIN candidates c
                 ON c.run_id=a.run_id AND c.candidate_hash=a.candidate_hash
               WHERE a.run_id=?
               ORDER BY a.updated_at DESC""",
            (rid,),
        ).fetchall()
        items = []
        seen = set()
        for row in rows:
            key = str(row["candidate_hash"])
            if key in seen:
                continue
            seen.add(key)
            observed = str(row["status"] or row["decision"] or "unknown")
            if status != "all" and observed != status:
                continue
            reason = row["cons"] or ""
            try:
                eligibility = json.loads(row["eligibility_json"] or "{}")
                reason = eligibility.get("summary") or eligibility.get("trigger") or reason
            except (TypeError, ValueError):
                pass
            items.append(
                {
                    "name": row["candidate_name"],
                    "status": observed,
                    "decision": row["decision"],
                    "score": row["overall_score"],
                    "reason": reason,
                    "updated_at": row["updated_at"],
                }
            )
            if len(items) >= limit:
                break
        return {
            "state": "read",
            "run_id": rid,
            "counts": _counts(db, rid),
            "items": items,
        }


@mcp.tool()
def recruiting_wait(
    run_id: str | None = None,
    timeout_seconds: int = 45,
    events: list[str] | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Wait for key events or a pending handoff, with an opaque cursor.

    events defaults to handoff, sent and control. Use phase to also return on
    phase changes. A pending handoff is always returned so the agent cannot
    leave a run waiting for an answer.
    """
    timeout_seconds = max(1, min(int(timeout_seconds), 45))
    allowed = {"handoff", "sent", "control", "phase", "stop"}
    if isinstance(events, str):
        events = [item.strip() for item in events.split(",") if item.strip()]
    events = list(dict.fromkeys(events or ["handoff", "sent", "control"]))
    if any(item not in allowed for item in events):
        raise ValueError("events_must_be_handoff_sent_control_phase_or_stop")
    with _connect() as db:
        run = _run_row(db, run_id)
        rid = str(run["run_id"])
        baseline = _cursor_decode(cursor) or _cursor_values(db, run)
        pending = _pending_handoff(db, run)
        if pending:
            return {
                "state": "handoff",
                "cursor": _cursor_encode(_cursor_values(db, run)),
                **pending,
            }
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(1)
            run = _run_row(db, rid)
            pending = _pending_handoff(db, run)
            current = _cursor_values(db, run)
            if pending:
                return {"state": "handoff", "cursor": _cursor_encode(current), **pending}
            changed = (
                ("sent" in events and current["sent"] != baseline.get("sent"))
                or ("control" in events and current["control"] != baseline.get("control"))
                or ("phase" in events and current["phase"] != baseline.get("phase"))
                or ("stop" in events and current["stop"] != baseline.get("stop"))
            )
            if changed:
                return {"state": "changed", "cursor": _cursor_encode(current), **_status(db, run)}
            baseline = current
        return {
            "state": "timeout",
            "timeout_seconds": timeout_seconds,
            "cursor": _cursor_encode(_cursor_values(db, run)),
            **_status(db, run),
        }


def _schema_for_type(annotation):
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is float:
        return {"type": "number"}
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        for item in get_args(annotation):
            if item is not type(None):
                return _schema_for_type(item)
        return {}
    if origin in (list, tuple, set):
        args = get_args(annotation)
        item = _schema_for_type(args[0]) if args else {}
        return {"type": "array", "items": item}
    if origin is dict or annotation is dict:
        return {"type": "object"}
    return {}


def _tool_specs():
    specs = []
    for name, function in TOOLS.items():
        signature = inspect.signature(function)
        properties = {}
        required = []
        for parameter_name, parameter in signature.parameters.items():
            if parameter_name in ("self", "cls"):
                continue
            properties[parameter_name] = _schema_for_type(parameter.annotation)
            if parameter.default is inspect.Parameter.empty:
                required.append(parameter_name)
        specs.append(
            {
                "name": name,
                "description": (inspect.getdoc(function) or name).strip(),
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return specs


def _send(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()


def _serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "parse_error"},
                }
            )
            continue
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion") or "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "recruiting-control", "version": "1.0.0"},
            }
        elif method in (
            "notifications/initialized",
            "notifications/cancelled",
            "notifications/roots/list_changed",
        ):
            continue
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": _tool_specs()}
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            function = TOOLS.get(name)
            if function is None:
                result = {
                    "content": [{"type": "text", "text": "unknown_tool: " + str(name)}],
                    "isError": True,
                }
            else:
                try:
                    value = function(**arguments)
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(value, ensure_ascii=False, default=str),
                            }
                        ],
                        "isError": False,
                    }
                except Exception as exc:  # noqa: BLE001 - surfaced to the MCP client
                    result = {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    }
        elif method in ("logging/setLevel", "resources/list", "prompts/list"):
            result = {"resources": []} if method == "resources/list" else {"prompts": []} if method == "prompts/list" else {}
        else:
            if request_id is not None:
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "method_not_found"},
                    }
                )
            continue
        if request_id is not None:
            _send({"jsonrpc": "2.0", "id": request_id, "result": result})


if __name__ == "__main__":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    _serve()
