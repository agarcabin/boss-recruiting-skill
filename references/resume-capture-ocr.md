# 电子简历长截图与 RapidOCR

## 适用场景

长截图与本地RapidOCR是可选的简历读取工具，用户已删除其强制前置要求。同事检查仍须在简历分析前完成；根据实际读取的内容判断，未读部分记未知。UIA概要不等于完整简历，不能虚报完整性，但内容足以支持判断时不因缺少长图/OCR而阻止运行。

采集工具可保持自身文件/拼图校验，失败仅表示本次采集未完成，不要求整轮停止。控制口径见 [control-policy.md](control-policy.md)。CUA、DOM、网页脚本、CDP限制保持。

## 运行环境

完整 skill 已自带 `runtime/win-x64/python/`、RapidOCR、ONNX Runtime、OpenCV 和本地模型，不需要联网或安装依赖。首次使用先按 [便携运行环境与首次配置](portable-runtime.md) 运行 `scripts/verify_runtime.ps1`。

所有命令优先使用：

```text
<skill>\runtime\win-x64\python\python.exe
```

## 采集长截图

生产流程优先使用串行入口 `scripts/capture_resume.py`，不再把候选人准备、截图和OCR用分号串起来：

```text
<包内python> scripts/capture_resume.py --run <run_id> --candidate-id <当前候选键> --hwnd <实测句柄> --output-dir <新的候选人工作目录>
```

调用不再要求预先登记、活跃候选键或截止门禁；选用该工具时仍使用全新目录，避免把旧图误认为当前内容。输出只表示采集结果，不发送。失败可按真实已读取内容继续评估，不编造缺失证据。

PowerShell统一优先使用 `pwsh`。Python动作与串行采集入口通过 `powershell_host.py` 选择PATH或Codex自带PowerShell 7；仅ASCII或有UTF-8 BOM的脚本才允许回退Windows PowerShell，避免中文无BOM脚本被误解析。原始PowerShell命令用于定向诊断，不作为失败后自动重跑整条流水线的入口。

先用定向 UIA 查询确认 `c-resume` Document 存在，并取得当前浏览器窗口句柄。运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/resume_capture.ps1 `
  -WindowHandle <窗口句柄> `
  -OutputDir "<本次候选人本地工作目录>" `
  -PythonPath "<skill>\runtime\win-x64\python\python.exe" `
  -SafetyPythonPath "<可读取本轮账本的 Python；默认与 PythonPath 相同>" `
  -Run <run_id> -LedgerDb <ledger.sqlite3> -Generation <gate_generation>
```

`PythonPath` 用于长图拼接和 OCR；`SafetyPythonPath` 仅用于调用 `run_safety.py` 检查同一账本、运行号和 generation。默认两者相同。若便携 Python 的用户数据目录与启动运行的 Python 隔离，显式将 `SafetyPythonPath` 指向启动运行时使用的 Python，并继续把 `PythonPath` 指向便携运行时；可使用managed_helper.py登记helper，便于结束时取消。

脚本只在当前 `c-resume` Document 的有限 UIA 范围内寻找简历滚动容器。优先使用 `ClassName=resume-detail-wrap`，并兼容用户批注所指 `div#resume` 在 UIA 中映射为 `AutomationId=resume` 的页面；若正文节点自身不支持 ScrollPattern，再检查其有限祖先链中唯一可滚动的 `resume-detail-wrap`。必要时也接受 c-resume Document 本身支持纵向 ScrollPattern。多个同优先级候选或找不到滚动容器时记录明确原因，不滚动推荐列表。

UIA 读取及 Win32 截图不得调用 `SetFocus()` 或强制把 BOSS 切到前台。先按 UIA 页面层级和实际 URL 找正确 c-resume Document；屏幕当前可见时用 Win32 截图。若该文档仍无可访问正文，保留页面状态并 review/不发送，不能使用DOM/网页脚本或强制聚焦；可按控制策略有界恢复页面。

- 使用 UIA ScrollPattern，不向宿主页面发送物理滚轮。
- 每屏滚动约可视高度的 75%。
- 到达 `VerticalScrollPercent=100` 才视为完成。
- 保存固定视口截图，并按实际滚动偏移拼接 `resume-long.png`。
- 左侧固定返回箭头在拼接时从空白边栏清除。
- 同时写入 `resume-capture.json`，记录页数、偏移、尺寸、滚动百分比和底部确认状态。
- 拼接成功后默认删除逐屏截图；只在异常排查时加 `-KeepPages`。

以下情况表示本次采集失败，可依控制策略恢复或使用实际可读内容继续：

- `c-resume` Document 消失。
- `resume-detail-wrap` 或其 ScrollPattern 消失。
- 推荐 iframe 回到加载态或浏览器标签页重建。
- 未达到底部却无法继续增加滚动百分比。

区分真实文档消失与`FindAll`漏项：采集首次锁定唯一可见c-resume后，若后续文档枚举漏掉它，仅允许只读验证同一个缓存元素的存活、可见、URL及最多35层RawView祖先仍属于原窗口。全部通过才沿用；不重新派发上一次滚动。元素失效、URL/RuntimeId变化、多份可见简历或祖先归属失败立即报错，不能据此自动重采集。此兼容路径尚需在后续获授权的实际运行中验证，不宣称已消除所有页面消失问题。

采集失败保留真实诊断信息；不再要求自动关闭整个浏览器或必须人工重开后才继续。

## RapidOCR

使用长图控制流、分块识别：

```powershell
& "<skill>\runtime\win-x64\python\python.exe" scripts/resume_image_pipeline.py rapidocr `
  --image "<目录>/resume-long.png" `
  --text-output "<目录>/resume.ocr.txt" `
  --json-output "<目录>/resume.ocr.json" `
  --tile-height 1200 `
  --overlap 150
```

默认裁成约 1200 像素高的块，相邻块重叠 150 像素。每块独立 OCR，文字框转换为长图绝对 Y 坐标后本地合并、去重。不要把整张长图缩放到检测模型的小尺寸后一次识别。

截图由本地脚本拼接并交给本地 RapidOCR。分析时优先把 OCR 文字整理成覆盖完整职业轨迹的精简文本或结构化事实，再交给模型；除非确有必要，不把整张或长截图直接输入多模态模型。对长简历，这通常能减少图像输入 token 和上传/视觉解析耗时；实际速度取决于图片长度、OCR 耗时和模型接口，短简历也可能因 OCR 环节而没有明显提速。OCR 可能丢失版面关系、表格或低清文字，所以先在本地核对章节连续性和关键字段，必要时仅针对难辨区域复查截图。完整图片和 OCR 原文只保存在本地；模型只接收完成判断所需的文字与证据，避免重复传入整份材料。

当前本机实测：

- 测试长图：`851 x 4008`
- 分块数：`4`
- 长图采集：`3.508 秒`
- RapidOCR 耗时：`4.0932 秒`
- 原始文字行：`119`
- 去重后文字行：`101`
- 平均行置信度：`0.9930`
- 六个不同任职时间段、教育经历和页脚均被识别

该数字只是一次本地样本，不保证所有排版均有相同准确率。根据实际可读字段判断，缺失项记未知，不把章节完整性作为继续条件；无法确认时不得声称完整率 100%。

## 所有 OCR 候选人的证据归档

每名做过 OCR 的候选人都必须保存简历证据，不论 `greet`、`review` 还是 `skip`。正常流程由 `candidate_log.py record` 的 `resume_evidence` 自动复制；已有评估记录需要补归档时执行：

```powershell
& "<skill>\runtime\win-x64\python\python.exe" scripts/candidate_log.py --output-root "<桌面路径>" archive-resume `
  --run <run_id> `
  --candidate-id <平台稳定标识> `
  --image "<目录>/resume-long.png" `
  --ocr-text "<目录>/resume.ocr.txt" `
  --ocr-json "<目录>/resume.ocr.json"
```

归档到：

```text
桌面/自动投递记录/<月日>/
  <企业>-<岗位>-投递记录.xlsx
  简历图片/
    姓名-标识摘要.png
  简历OCR/
    姓名-标识摘要.ocr.txt
    姓名-标识摘要.ocr.json
```

`<企业>-<岗位>-投递记录.xlsx` 最后一列“查看简历”在有长图时链接到对应文件。尚未归档时如实保留 `pending`，不阻止处理下一名候选人。长截图或 OCR 无法取得时可记录原因：

```powershell
& "<skill>\runtime\win-x64\python\python.exe" scripts/candidate_log.py --output-root "<桌面路径>" missing-resume `
  --run <run_id> `
  --candidate-id <平台稳定标识> `
  --reason "<具体原因>"
```

图片、OCR JSON 和完整 OCR 文本属于候选人敏感资料：

- 只保存在本地招聘输出目录。
- 不进入项目分享包。
- 不附加到普通简报可见页。
- 不发送到外部 OCR API。
- 每名候选人使用独立临时工作目录。
- 无论判定结果如何，`record` 成功写入今日 `简历图片/` 和 `简历OCR/` 后即可删除临时工作目录。
- 逐屏 `resume-page-*.png` 只用于拼接和异常排查，不进入最终归档；拼接与核对成功后即可删除。
