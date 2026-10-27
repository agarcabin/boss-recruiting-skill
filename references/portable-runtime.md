# 便携运行环境与首次配置

压缩包是完整 skill，不是安装程序。解压后应看到：

```text
boss-recruiting/
  SKILL.md
  agents/
  references/
  scripts/
  profiles/
  runtime/
    win-x64/
      python/
      PACKAGE_MANIFEST.json
      requirements.txt
      THIRD_PARTY_NOTICES.md
```

`runtime/win-x64/python/` 是完整 Python 3.12 运行环境，已经包含 RapidOCR、ONNX Runtime、OpenCV、NumPy、openpyxl、pypdf、Tk 等依赖和本地 RapidOCR 模型。正常运行不需要联网，也不需要执行 `pip install`。

## 首次解压位置

Windows 推荐解压到：

```text
C:\Users\<用户名>\.codex\skills\boss-recruiting
```

最终确认该目录直接存在：

```text
SKILL.md
runtime\win-x64\python\python.exe
```

不要把 `runtime` 拆出去，也不要只复制 `SKILL.md` 和 `scripts`。不要直接从只读 U 盘运行；先复制到本机用户目录，避免模型缓存、临时文件和权限问题。

## 首次自检

在 PowerShell 中运行：

```powershell
cd "$env:USERPROFILE\.codex\skills\boss-recruiting"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_runtime.ps1
```

成功时会显示：

- Python 版本
- RapidOCR 版本
- ONNX Runtime 版本
- OpenCV 版本
- 三个本地 OCR 模型

只做机器可读检查时：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify_runtime.ps1 -Json
```

选择首页“4. 测试项目”时，使用便携 Python 运行标准化测试：

```powershell
.\runtime\win-x64\python\python.exe .\scripts\standard_test.py --output-root "$env:TEMP\boss-recruiting-standard-test"
```

测试项目会依据报告检查 Python、OCR、办公文件库、输出目录、账本和鼠标/UIA 工具；浏览器坐标按 [标准化测试](standard-test.md) 做只读校准。普通项目不要求先运行此报告。

## 运行规则

便携包存在时，所有 Python 脚本优先使用：

```text
<skill>\runtime\win-x64\python\python.exe
```

不要改用系统 `python`、Windows 自带 OCR、外部 OCR API，也不要重新下载模型。电子简历流程使用：

```powershell
.\runtime\win-x64\python\python.exe .\scripts\resume_image_pipeline.py rapidocr `
  --image <resume-long.png> `
  --text-output <resume.ocr.txt> `
  --json-output <resume.ocr.json> `
  --tile-height 1200 `
  --overlap 150
```

完整的简历采集、长图拼接、OCR 和已发送候选人归档规则见 [长截图与 RapidOCR](resume-capture-ocr.md)。

## 迁移与更新

- 复制整个 `boss-recruiting` 目录，禁止只复制运行器或项目文件。
- 目标电脑必须是 Windows x64；`onnxruntime` 和 `python312.dll` 是平台专用二进制。
- 更新 skill 时先保留 `profiles/` 和招聘输出目录，再替换代码与 `runtime/`。
- 若 Windows 路径长度受限，启用长路径支持或解压到较短的 `%USERPROFILE%\.codex\skills`。
- `PACKAGE_MANIFEST.json` 记录运行时版本、文件数和模型哈希；更新运行时后必须重新生成。
- 测试项目通过 `verify_runtime.ps1` 和标准化测试评估本机环境。普通投递直接按流程运行；实际需要的运行库或页面能力若不可用，按对应错误停下处理。
