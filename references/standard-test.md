# 新电脑标准化测试

此测试只属于首页的“4. 测试项目”，不作为普通项目开始投递的前置条件。用户选择测试项目后，运行 `scripts/standard_test.py` 生成本机报告；该脚本不发送招呼、不打开或保存真实候选人简历。报告放在桌面 `自动投递记录/标准化测试/`，文件名含电脑名与日期。

1. 先用 `scripts/verify_runtime.ps1` 确认完整包内的 `runtime/win-x64/python/python.exe` 和三个 RapidOCR 模型；再用该便携 Python 运行 `scripts/standard_test.py`。检查 Python/openpyxl/pypdf、RapidOCR、ONNX Runtime、OpenCV、桌面写入、临时账本、招聘流程测试、Codex 最大化、PowerShell 7、点击轨迹 dry run、点击后 1 秒随机移动支持情况和等待鼠标圆周轨迹 dry run。任何自动检查失败都记入报告。
2. 在已打开的 Codex 内置浏览器上做**只读坐标校准**：选择一个不会触发发送、删除或提交的控件，取得真实 Win32 顶层窗口句柄、物理屏幕坐标和浏览器内容物理边界。核对截图与物理坐标转换，再运行 `scripts/move-click.ps1 -DryRun`；只有实际观察确认坐标落在该控件内、窗口句柄属于当前窗口后，才可带 `--browser-verified --browser-evidence "<简短实测记录>"` 重新生成报告。浏览器返回的 opaque window ID 不能直接当 Win32 HWND。无法完成映射则报告保持“待核验”。
3. 阅读报告的每一项并向用户汇报。失败或待核验项只阻止测试项目中的后续 5 人试投，按结果修复或标明限制；不阻止用户从普通项目直接开始已授权的投递。报告只证明本机当时环境状态，不证明平台不会限制发送。

```text
python scripts/standard_test.py
python scripts/standard_test.py --browser-verified --browser-evidence "窗口句柄、浏览器物理边界和安全控件中心已现场核验；dry run 坐标吻合"
```
