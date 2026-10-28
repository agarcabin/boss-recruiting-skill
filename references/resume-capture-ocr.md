# 电子简历长截图与 RapidOCR

## 适用场景

BOSS 电子简历 `c-resume` 的 UIA 信息只有概略内容，不能覆盖完整职业经历。启用电子简历判断时，每名候选人的生产评分都以长截图和本地 RapidOCR 取得的完整正文为依据。流程固定为：

`打开电子简历 -> c-resume 文档核验 -> resume-detail-wrap / div#resume 映射核验 -> UIA 内层滚动 -> 分屏截图 -> 拼接长图 -> RapidOCR 分块识别 -> 本地真伪与完整性核对 -> 评分`

UIA 用于定位页面、控件与滚动容器；不能用 UIA 概览代替简历正文，也不能因为 UIA 显示部分经历就跳过长截图。按用户要求不做姓名与卡片身份交叉核对；OCR 姓名仅用于候选人记录。简历文档缺失或正文无法读取时仍暂停该候选人。不得改用 DOM、整页 AX、Playwright `evaluate`/`domSnapshot`、JavaScript、CDP、远程 OCR 或剪贴板拖选抓取简历。

长截图由固定可视区域拼接，不得按 UIA Document 的数千像素高度直接截图。

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

调用前必须已成功 `candidate-begin` 且核验简历打开并登记 `electronic-opened`。入口核对当前活跃候选键、运行状态、generation、截止及未使用过的输出目录，再分别经 `managed_helper.py` 采集、OCR；每阶段前后复核门禁。采集失败、未到底、证据缺失、OCR失败或中途停止都非零退出，后续阶段不启动。成功只返回 `ready_for_assessment` 和本地证据路径，不评分、不记发送、不自动重试。截图已留存但流程失败时保留目录供诊断，不复用其中旧文件冒充成功。

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

`PythonPath` 用于长图拼接和 OCR；`SafetyPythonPath` 仅用于调用 `run_safety.py` 检查同一账本、运行号和 generation。默认两者相同。若便携 Python 的用户数据目录与启动运行的 Python 隔离，显式将 `SafetyPythonPath` 指向启动运行时使用的 Python，并继续把 `PythonPath` 指向便携运行时；采集仍须通过 `managed_helper.py`，不能跳过账本检查。

脚本只在当前 `c-resume` Document 的有限 UIA 范围内寻找简历滚动容器。优先使用 `ClassName=resume-detail-wrap`，并兼容用户批注所指 `div#resume` 在 UIA 中映射为 `AutomationId=resume` 的页面；若正文节点自身不支持 ScrollPattern，再检查其有限祖先链中唯一可滚动的 `resume-detail-wrap`。必要时也接受 c-resume Document 本身支持纵向 ScrollPattern。多个同优先级候选或找不到滚动容器时记录明确原因，不滚动推荐列表。

UIA 读取及 Win32 截图不得调用 `SetFocus()` 或强制把 BOSS 切到前台。先按 UIA 页面层级和实际 URL 找正确 c-resume Document；屏幕当前可见时用 Win32 截图。若该文档仍无可访问正文，保留页面状态并 review/不发送，不能 DOM/网页脚本读取、刷新或强制聚焦。

- 使用 UIA ScrollPattern，不向宿主页面发送物理滚轮。
- 每屏滚动约可视高度的 75%。
- 到达 `VerticalScrollPercent=100` 才视为完成。
- 保存固定视口截图，并按实际滚动偏移拼接 `resume-long.png`。
- 左侧固定返回箭头在拼接时从空白边栏清除。
- 同时写入 `resume-capture.json`，记录页数、偏移、尺寸、滚动百分比和底部确认状态。
- 拼接成功后默认删除逐屏截图；只在异常排查时加 `-KeepPages`。

以下任一情况立即停止，不自动恢复：

- `c-resume` Document 消失。
- `resume-detail-wrap` 或其 ScrollPattern 消失。
- 推荐 iframe 回到加载态或浏览器标签页重建。
- 未达到底部却无法继续增加滚动百分比。

区分真实文档消失与`FindAll`漏项：采集首次锁定唯一可见c-resume后，若后续文档枚举漏掉它，仅允许只读验证同一个缓存元素的存活、可见、URL及最多35层RawView祖先仍属于原窗口。全部通过才沿用；不重新派发上一次滚动。元素失效、URL/RuntimeId变化、多份可见简历或祖先归属失败立即报错，不能据此自动重采集。此兼容路径尚需在后续获授权的实际运行中验证，不宣称已消除所有页面消失问题。

停止后若仍能控制本次自动化标签页，立即关闭它停止可能发生的刷新；无法关闭或用户正在操作时，请用户完整关闭并重新打开内置浏览器，再重新打开同一份电子简历。

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

该数字只是一次本地样本，不保证所有排版均有相同准确率。评分前必须核对公司和职位连续性、任职时间、职责、业绩数字、教育和页脚；无法确认时不得声称完整率 100%。

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

`<企业>-<岗位>-投递记录.xlsx` 最后一列“查看简历”链接到对应长图。已发送候选人若尚未归档，状态为 `pending`；`saved` 或经说明记录为 `missing` 前，不得处理下一名候选人。长截图或 OCR 确实无法取得时使用：

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
