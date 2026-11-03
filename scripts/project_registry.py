"""Discover, register, import, and export portable recruiting project profiles."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = SKILL_ROOT / "profiles"
PACKAGE_FORMAT = "boss-recruiting-project/v1"
MANIFEST_FORMAT = "boss-recruiting-manifest/v1"
MAX_ARCHIVE_BYTES = 5 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_FILES = 20
PROJECT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def output(**items: object) -> None:
    print(json.dumps(items, ensure_ascii=False))


def installed_metadata():
    text=(SKILL_ROOT/'SKILL.md').read_text(encoding='utf-8-sig')
    match=re.search(r'(?m)^  version:\s*["\']?([0-9.]+)',text)
    if not match:raise ValueError('skill_version_missing')
    updated=re.search(r'(?m)^  updated_at:\s*["\']?(\d{4}-\d{2}-\d{2})',text)
    if not updated:raise ValueError('skill_updated_at_missing')
    return dict(version=match[1],updated_at=updated[1])


def installed_version():
    return installed_metadata()['version']


def latest_run_readonly(db_path: Path | None = None):
    import ledger
    path=Path(db_path) if db_path is not None else ledger.DEFAULT_DB
    if not path.is_file():
        return None
    with contextlib.closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=20)) as db:
        db.row_factory=sqlite3.Row
        captured=io.StringIO()
        with contextlib.redirect_stdout(captured):
            ledger.recent_runs(db,argparse.Namespace())
        runs=json.loads(captured.getvalue())['items']
    return runs[0] if runs else None


def build_home_menu(projects, latest_run, metadata=None):
    if latest_run and not any(str(item.get('profile'))==str(latest_run.get('profile_path')) for item in projects):latest_run=None
    metadata=metadata if metadata is not None else installed_metadata()
    project_count=len({str(p['company']) for p in projects})
    position_count=len(projects)
    if latest_run:
        states={'running':'运行中','paused':'已暂停','login_required':'需要登录',
                'stopped':'已结束','expired':'已结束'}
        state=states.get(latest_run.get('run_state'),'状态未知')
        company=latest_run.get('company') or '企业未知'
        position=latest_run.get('position') or '岗位未知'
        sent=latest_run.get('greetings_sent')
        progress=f'成功招呼 {sent} 人' if sent is not None else '成功招呼人数未知'
        last=f'{company}｜{position}；{state}，{progress}'
    else:
        last='暂无记录'
    title='杰博人力创新招聘组自动打招呼 Skill'
    items=[f'1. 继续上次项目（{last}）',
           f'2. 查看已有项目（已有 {project_count} 个项目，{position_count} 个岗位）',
           '3. 创建新的项目',
           f"4. 更新项目（当前版本 {metadata['version']} - 更新日期 {metadata['updated_at'].replace('-','/')}）",
           '5. 测试配置环境','6. 退出打招呼']
    return dict(state='menu',menu_title=title,menu_items=items,menu_item_1=items[0],
                menu_text=title+'\n\n'+'\n'.join(items),project_count=project_count,
                position_count=position_count,latest_run=latest_run,**metadata)


def front_matter(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", content, re.S)
    if not match:
        raise ValueError(f"front_matter_missing:{path}")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def make_project_id(company: str, position: str) -> str:
    digest = hashlib.sha256(f"{company}\0{position}".encode("utf-8")).hexdigest()[:16]
    return f"project-{digest}"


def normalized_project_id(value: str, company: str, position: str) -> str:
    value = value.strip().lower()
    if not value:
        return make_project_id(company, position)
    if not PROJECT_ID.fullmatch(value):
        raise ValueError("project_id must use lowercase letters, digits, and hyphens")
    return value


def read_project(profile: Path) -> dict[str, object]:
    profile = profile.resolve()
    import project_vault
    if not project_vault.readable(profile):raise ValueError('project_data_locked')
    fields = front_matter(profile)
    if fields.get("schema") != "boss-greeting-profile/v1":
        raise ValueError("profile_schema_mismatch")
    company, position = fields.get("company", "").strip(), fields.get("position", "").strip()
    if not company or not position:
        raise ValueError("profile_identity_missing")
    metadata_path = profile.parent / "project.json"
    metadata: dict[str, object] = {}
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
    project_id = str(metadata.get("project_id") or make_project_id(company, position))
    if not PROJECT_ID.fullmatch(project_id):
        project_id = make_project_id(company, position)
    greeting_mode = fields.get('greeting_mode', metadata.get('greeting_mode', 'single'))
    if greeting_mode not in ('single', 'triple'):
        raise ValueError('invalid_greeting_mode')
    return {"project_id": project_id, "company": company, "position": position,
            "greeting_mode": greeting_mode,
            "approval": fields.get("approval", "pending"), "profile": str(profile),
            "metadata": str(metadata_path), "display_name": f"{company} - {position}"}


def register_project(profile: Path, project_id: str = "") -> dict[str, object]:
    profile = profile.resolve()
    project = read_project(profile)
    metadata_path = profile.parent / "project.json"
    existing: dict[str, object] = {}
    if metadata_path.is_file():
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    requested_id = project_id.strip() or str(existing.get("project_id", ""))
    digest = normalized_project_id(requested_id, str(project["company"]), str(project["position"]))
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metadata = {**{key:existing[key] for key in ("candidate_namespace","evaluation_mode","trigger_policy","display_order","origin","active","retired","rules") if key in existing}, "format": PACKAGE_FORMAT, "project_id": digest,
                "company": project["company"], "position": project["position"], "greeting_mode": project["greeting_mode"],
                "profile_schema": "boss-greeting-profile/v1", "profile": profile.name,
                "created_at": existing.get("created_at", stamp), "updated_at": stamp}
    metadata.setdefault('origin','user')
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    project.update(project_id=digest, metadata=str(metadata_path))
    return project


def list_projects(root: Path = PROJECTS_ROOT) -> list[dict[str, object]]:
    root = root.resolve()
    if not root.is_dir():
        return []
    projects: list[dict[str, object]] = []
    for profile in root.rglob("*.md"):
        try:
            import project_vault
            if not project_vault.selectable(profile):continue
            projects.append(read_project(profile))
        except (OSError, ValueError):
            continue
    return sorted(projects, key=lambda item: (str(item["company"]).casefold(), int(json.loads(Path(str(item["metadata"])).read_text(encoding="utf-8-sig")).get("display_order",999)) if Path(str(item["metadata"])).is_file() else 999, str(item["position"]).casefold()))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export_project(profile: Path, destination: Path) -> dict[str, object]:
    profile = profile.resolve()
    project = register_project(profile)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    profile_bytes = profile.read_bytes()
    metadata_path = Path(str(project["metadata"]))
    metadata_bytes = metadata_path.read_bytes()
    names = {"project.json": metadata_bytes, profile.name: profile_bytes}
    manifest = {"format": MANIFEST_FORMAT, "package_schema": PACKAGE_FORMAT,
                "project_id": project["project_id"], "company": project["company"],
                "position": project["position"], "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "files": {name: sha256(content) for name, content in names.items()}}
    with tempfile.NamedTemporaryFile(prefix=".project-", suffix=".zip", dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for name, content in names.items():
                archive.writestr(name, content)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"state": "exported", "project_id": project["project_id"], "archive": str(destination),
            "sha256": sha256(destination.read_bytes())}


def safe_member(name: str) -> str:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
        raise ValueError("unsafe_archive_path")
    return path.name


def import_project(archive_path: Path, root: Path = PROJECTS_ROOT, overwrite: bool = False) -> dict[str, object]:
    archive_path = archive_path.resolve()
    root = root.resolve()
    if not archive_path.is_file() or archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("archive_missing_or_too_large")
    with ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if not 3 <= len(infos) <= MAX_ARCHIVE_FILES:
            raise ValueError("archive_file_count_invalid")
        contents: dict[str, bytes] = {}
        for info in infos:
            name = safe_member(info.filename)
            if name in contents or info.is_dir() or info.file_size > MAX_FILE_BYTES:
                raise ValueError("archive_entry_invalid")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("archive_symlink_not_allowed")
            contents[name] = archive.read(info)
    if "manifest.json" not in contents or "project.json" not in contents:
        raise ValueError("archive_manifest_missing")
    try:
        manifest = json.loads(contents.pop("manifest.json").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("archive_manifest_invalid") from exc
    if manifest.get("format") != MANIFEST_FORMAT or manifest.get("package_schema") != PACKAGE_FORMAT:
        raise ValueError("archive_format_mismatch")
    project_id = str(manifest.get("project_id", ""))
    if not PROJECT_ID.fullmatch(project_id):
        raise ValueError("archive_project_id_invalid")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or set(expected) != set(contents):
        raise ValueError("archive_file_list_mismatch")
    for name, content in contents.items():
        if expected.get(name) != sha256(content):
            raise ValueError(f"archive_checksum_mismatch:{name}")
    markdown = [name for name in contents if name.lower().endswith(".md")]
    if len(markdown) != 1:
        raise ValueError("archive_profile_count_invalid")
    profile_bytes = contents[markdown[0]]
    with tempfile.TemporaryDirectory(prefix=".import-", dir=root if root.exists() else None) as temp:
        temporary = Path(temp)
        (temporary / "project.json").write_bytes(contents["project.json"])
        (temporary / markdown[0]).write_bytes(profile_bytes)
        read_project(temporary / markdown[0])
        import project_vault
        if not project_vault.selectable(temporary / markdown[0]):raise ValueError('project_archived_or_locked')
    destination = root / project_id
    if destination.exists() and not overwrite:
        raise ValueError("project_already_exists")
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".import-project-", dir=root))
    try:
        (staging / "project.json").write_bytes(contents["project.json"])
        (staging / markdown[0]).write_bytes(profile_bytes)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    imported = read_project(destination / markdown[0])
    return {"state": "imported", "project_id": imported["project_id"],
            "profile": imported["profile"], "company": imported["company"], "position": imported["position"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECTS_ROOT)
    parser.add_argument("--db", type=Path, help="Read-only ledger path for the home menu")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("menu")
    register = commands.add_parser("register")
    register.add_argument("--profile", type=Path, required=True)
    register.add_argument("--project-id", default="")
    export = commands.add_parser("export")
    export.add_argument("--profile", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    importer = commands.add_parser("import")
    importer.add_argument("--archive", type=Path, required=True)
    importer.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "list":
            items=list_projects(args.root)
            output(state="projects", items=items,**installed_metadata(),
                   project_count=len({str(item['company']) for item in items}),position_count=len(items),
                   menu_item_1='1. 继续上次项目（企业｜岗位；运行状态，成功招呼 x 人）')
        elif args.command == "menu":
            output(**build_home_menu(list_projects(args.root),latest_run_readonly(args.db)))
        elif args.command == "register":
            output(state="registered", project=register_project(args.profile, args.project_id))
        elif args.command == "export":
            output(**export_project(args.profile, args.output))
        else:
            output(**import_project(args.archive, args.root, args.overwrite))
    except (OSError, ValueError, sqlite3.Error) as exc:
        output(state="error", reason=str(exc))
        sys.exit(2)


if __name__ == "__main__":
    main()
