"""Idempotently register the local recruiting MCP server with Codex.

The skill must not overwrite an existing recruiting MCP configuration. Users
who already installed the MCP prototype keep their own command, environment
and paths.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.11+ on the supported runtime
    tomllib = None


SECTION = re.compile(
    r"""(?mx)^\s*\[\s*mcp_servers\s*\.\s*(?:recruiting|"recruiting"|'recruiting')\s*\]\s*$"""
)
COMMENTED = re.compile(
    r"""(?m)^\s*#\s*\[\s*mcp_servers\s*\.\s*(?:recruiting|"recruiting"|'recruiting')\s*\]\s*$"""
)
INLINE = re.compile(r"(?m)^\s*recruiting\s*(?:=|\.)")


def _local_app_data() -> Path:
    return Path(os.environ.get("USERPROFILE") or Path.home()) / "AppData" / "Local"


def _state_dir() -> Path:
    return Path(
        os.environ.get("BOSS_STATE_DIR")
        or (_local_app_data() / "Codex" / "recruiting-greetings")
    )


def _installed_root(root: Path | None = None) -> tuple[Path, Path] | None:
    candidate = Path(root or Path(__file__).resolve().parents[1]).resolve()
    runtime = candidate / "runtime" / "win-x64" / "python" / "python.exe"
    server = candidate / "scripts" / "recruiting_mcp.py"
    if not runtime.is_file() or not server.is_file():
        return None
    return candidate, runtime


def _section_text(root: Path, runtime: Path) -> str:
    server = root / "scripts" / "recruiting_mcp.py"
    state = _state_dir()
    lines = [
        "[mcp_servers.recruiting]",
        "command = " + json.dumps(str(runtime), ensure_ascii=False),
        "args = [" + json.dumps(str(server), ensure_ascii=False) + "]",
        "startup_timeout_sec = 30",
        "",
        "[mcp_servers.recruiting.env]",
        "BOSS_STATE_DIR = " + json.dumps(str(state), ensure_ascii=False),
        "BOSS_SKILL_ROOT = " + json.dumps(str(root), ensure_ascii=False),
        "",
    ]
    return "\n".join(lines)


def status(config_path: Path | None = None, root: Path | None = None) -> dict:
    path = Path(config_path or Path.home() / ".codex" / "config.toml")
    installed = _installed_root(root)
    if not path.is_file():
        return {
            "state": "absent",
            "config": str(path),
            "installed_root": str(installed[0]) if installed else None,
        }
    text = path.read_text(encoding="utf-8-sig")
    if SECTION.search(text) or INLINE.search(text):
        return {"state": "existing", "config": str(path)}
    if COMMENTED.search(text):
        return {"state": "existing_disabled", "config": str(path)}
    return {
        "state": "missing",
        "config": str(path),
        "installed_root": str(installed[0]) if installed else None,
    }


def ensure(config_path: Path | None = None, root: Path | None = None) -> dict:
    path = Path(config_path or Path.home() / ".codex" / "config.toml")
    installed = _installed_root(root)
    if not installed:
        return {"state": "skipped", "reason": "installed_runtime_or_server_missing"}
    root_path, runtime = installed
    current = status(path, root_path)
    if current["state"] in ("existing", "existing_disabled"):
        return current
    text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    if text.strip() and tomllib is not None:
        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            return {
                "state": "skipped",
                "reason": "config_toml_invalid",
                "detail": str(exc),
                "config": str(path),
            }
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.is_file():
        backup = path.with_name(path.name + ".bak-mcp-" + time.strftime("%Y%m%d%H%M%S"))
        shutil.copy2(path, backup)
    block = _section_text(root_path, runtime)
    new_text = (text.rstrip() + "\n\n" if text.strip() else "") + block
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(new_text, encoding="utf-8")
    os.replace(temporary, path)
    return {
        "state": "registered",
        "config": str(path),
        "backup": str(backup) if backup else None,
        "server": str(root_path / "scripts" / "recruiting_mcp.py"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "ensure"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    result = status(args.config, args.root) if args.action == "status" else ensure(args.config, args.root)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
