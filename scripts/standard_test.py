"""Create a local, non-sending readiness report for the recruiting skill."""

from __future__ import annotations
import workspace_paths

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def check(name, action):
    try:
        detail = action()
        return {"name": name, "status": "通过", "detail": str(detail)}
    except Exception as exc:
        return {"name": name, "status": "失败", "detail": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=workspace_paths.desktop_dir())
    parser.add_argument("--browser-verified", action="store_true")
    parser.add_argument("--browser-evidence", default="")
    args = parser.parse_args()
    if args.browser_verified and len(args.browser_evidence.strip()) < 15:
        parser.error("--browser-verified requires specific --browser-evidence")
    skill = Path(__file__).resolve().parents[1]
    ledger = skill / "scripts" / "ledger.py"
    folder = workspace_paths.records_dir(args.output_root) / "标准化测试"
    checks = []
    checks.append(check("Python 与 Excel 库", lambda: __import__("openpyxl").__version__))
    checks.append(check("PDF 解析库", lambda: __import__("pypdf").__version__))
    checks.append(check("RapidOCR", lambda: importlib.metadata.version("rapidocr")))
    checks.append(check("ONNX Runtime", lambda: importlib.metadata.version("onnxruntime")))
    checks.append(check("OpenCV", lambda: __import__("cv2").__version__))

    def portable_runtime_test():
        python = skill / "runtime" / "win-x64" / "python" / "python.exe"
        models = skill / "runtime" / "win-x64" / "python" / "Lib" / "site-packages" / "rapidocr" / "models"
        required = [
            models / "PP-OCRv6_det_small.onnx",
            models / "PP-OCRv6_rec_small.onnx",
            models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
        ]
        if not python.is_file():
            raise RuntimeError("便携 Python 缺失")
        missing = [path.name for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"RapidOCR 模型缺失: {', '.join(missing)}")
        return f"{python}；当前测试解释器={sys.executable}"

    checks.append(check("便携运行时", portable_runtime_test))

    def window_test():
        import tkinter as tk
        root = tk.Tk()
        try:
            root.withdraw()
            root.update()
            return f"Tk {root.tk.call('info', 'patchlevel')} 可创建窗口"
        finally:
            root.destroy()

    checks.append(check("进度窗口", window_test))

    def project_package_test():
        import project_registry
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "profiles" / "source"
            source.mkdir(parents=True)
            profile = source / "profile.md"
            profile.write_text("""---
schema: boss-greeting-profile/v1
company: Test Company
position: Sales
approval: approved
approved_by: owner
approved_at: 2026-10-20
---
## 页面核验
Test.
## 企业与岗位事实
Test.
## 自动筛选条件
Test.
## 评分规则
Test.
## 加分项
Test.
## 待人工确认
None.
## 固定招呼话术
Approved test greeting.
## 冲突与待确认
无
## 来源
Test.
""", encoding="utf-8")
            project_registry.register_project(profile, "standard-test")
            archive = root / "standard-test.boss-project.zip"
            project_registry.export_project(profile, archive)
            imported = project_registry.import_project(archive, root / "imported")
            assert imported["project_id"] == "standard-test"
            assert project_registry.list_projects(root / "imported")[0]["company"] == "Test Company"
        return "项目登记、SHA-256 分享包和导入通过"

    checks.append(check("项目包导入导出", project_package_test))

    def desktop_test():
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as tmp:
            path = Path(tmp) / "test.xlsx"
            from openpyxl import Workbook, load_workbook
            wb = Workbook()
            wb.active["A1"] = "通过"
            wb.save(path)
            reopened = load_workbook(path, read_only=True)
            try:
                assert reopened.active["A1"].value == "通过"
            finally:
                reopened.close()
        return str(folder)

    checks.append(check("桌面目录与 XLSX 读写", desktop_test))

    def ledger_test():
        import importlib.util
        spec = importlib.util.spec_from_file_location("recruiting_ledger_test", ledger)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            db = module.connect(Path(tmp) / "ledger.sqlite3")
            assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
            db.close()
        return "临时 SQLite 创建、读取成功"

    checks.append(check("招聘账本", ledger_test))

    def workflow_test():
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(skill / "scripts"), "-p", "test_*.py"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or "unittest failed")[-800:])
        return "候选人记录（含判断时长与绿黄行配色）、限额、恢复和简历/PDF 归档测试通过"

    checks.append(check("招聘流程测试", workflow_test))
    checks.append(check("PowerShell 7", lambda: shutil.which("pwsh") or (_ for _ in ()).throw(RuntimeError("pwsh 未安装或未在 PATH"))))

    def browser_adapter_test():
        import browser_bridge
        import workflow_browser
        sample = dict(provider='browser-plugin', browser='iab', tab_id='offline-test',
                      url='https://www.zhipin.com/web/chat/recommend')
        browser_bridge.validate_binding(sample)
        if not callable(workflow_browser.HybridAdapter):
            raise RuntimeError('HybridAdapter missing')
        return 'HybridAdapter与插件标签页绑定格式可用；未执行页面操作'

    checks.append(check('浏览器插件交接', browser_adapter_test))
    checks.append({'name': '当前聊天浏览器插件标签页', 'status': '通过' if args.browser_verified else '待核验',
                   'detail': args.browser_evidence.strip() if args.browser_verified else
                             '需通过浏览器插件核实当前聊天iab标签页、实际BOSS URL及只读快照；不需要HWND或桌面坐标'})
    passed = all(item["status"] == "通过" for item in checks)
    cn = timezone(timedelta(hours=8))
    stamp = datetime.now(cn)
    host = socket.gethostname().replace("/", "_").replace("\\", "_")
    report = folder / f"{host}-{stamp:%Y%m%d-%H%M%S}-标准化测试.md"
    lines = ["# BOSS 招聘 Skill 标准化测试", "", f"- 电脑：{host}", f"- 时间：{stamp.isoformat(timespec='seconds')}",
             f"- 系统：{platform.platform()}", f"- Python：{sys.executable}", f"- 结果：{'通过' if passed else '未通过'}", "",
             "| 检查项 | 状态 | 详情 |", "|---|---|---|"]
    for item in checks:
        lines.append(f"| {item['name']} | {item['status']} | {item['detail'].replace('|', '/').replace(chr(10), ' ')} |")
    lines += ["", "未执行真实发送；本报告不代表平台授权或发送成功率。", ""]
    folder.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"state": "passed" if passed else "not_ready", "report": str(report), "checks": checks}, ensure_ascii=False))


if __name__ == "__main__":
    main()
