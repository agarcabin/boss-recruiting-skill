> 2026-10-27现行口径：先按 [evaluation-modes.md](evaluation-modes.md) 分流。card不打开电子简历、不做OCR及详情同事检查；resume保留下文对应流程。所有外部动作经safe_action.py，不裸调用UIA Invoke/按键/鼠标；历史示例仅作底层技术参考。

# Windows UI Automation 页面读取与控件调用

UI Automation 通过 Windows Accessibility Provider 读取 Chromium 为页面生成的可访问性控件树，不是截图，也不经过 AI 视觉或 OCR。读取结果来自控件语义属性和几何信息，例如控件类型、名称、ClassName、AutomationId、Enabled、Offscreen 和 BoundingRectangle。电子简历正文例行使用本地长截图与 RapidOCR；其他截图用于歧义复核、发送前视觉确认和异常取证。

点击默认统一使用 UIA，按[点击方式开关](click-modes.md)分流：`use_mouse_trajectory=false`（默认，含未指定）调用目标控件的 `InvokePattern.Invoke()`，不移动鼠标；只有用户明确开启 `true` 时才使用拟人鼠标点击。以下涉及坐标、`FromPoint`、轨迹和物理点击的条款只适用于鼠标模式；UIA 模式核验目标元素及其候选人祖先归属，不做坐标命中测试。两种模式均须定向定位、通过门禁并核验结果。

页面内容读取顺序固定为：

1. 使用定向 UIA 查询页面控件、概要文本、文档 URL 与几何信息；UIA 取得的简历概览不足以用于完整评分。
2. 启用电子简历判断时，每名候选人的简历正文均按 [长截图与 RapidOCR](resume-capture-ocr.md) 采集；评分前核对完整性。关闭电子简历判断时，不得推测未读取的正文。
3. BOSS 页面一律禁止使用 CUA，包括 `cua_repl` 的 `getState`、`listTabs`、`getTab`、`getScreenshot`、`getAXState`、点击、按键、滚动、导航及等价封装。CUA 截图和页面绑定也可能触发刷新，即使只是只读确认也不得使用。
4. 禁止用 DOM 快照、整页 AX、内置浏览器 `getAXState`、Playwright `evaluate`/`domSnapshot`、页面 JavaScript、CDP、剪贴板拖选或源码抓取读取页面内容。这些行为可能触发刷新。
5. 一旦观察到自动刷新、候选区重置、Document 消失或控件数量异常归零，立即停止操作；不得通过 CUA 继续控制页面，也不得重试或重载。由用户手工完整关闭并重新打开浏览器，确认恢复后再继续定向 UIA 核验。

## 禁止 CUA 与整页 AX 抓取

不要对 BOSS 推荐页执行 CUA 标签页绑定、CUA 截图、整页可访问性树抓取、整页 AX 序列化或内置浏览器的整页 `getAXState`。2026-10-22 已复现：未点击、未滚动、未使用鼠标控制，仅执行 CUA 标签页绑定和截图，推荐页就从 4 张候选人卡片变为“BOSS 加载中”，`推荐牛人` Document 随即消失。该问题不需要点击岗位或“打招呼”即可发生，不能把它当作平台正常刷新。看到 `Cua.AgentCursorOverlay` 蓝色辅助光标即应立即停止。

需要打开 BOSS 时，由用户手工操作，或使用 Codex 中明确非 CUA 的页面打开入口。需要截图取证时，只能使用 Win32 截屏或本 Skill 的本地简历采集脚本。

必须使用 Win32 UIA 从 Codex 顶层窗口向下定位：

1. 定位 `Document: BOSS直聘`。
2. 在其中定位 `Document: 推荐牛人`。
3. 仅在 `推荐牛人` 子树中按 `ControlType`、`Name`、`NameLike` 或 `ClassName` 查询目标控件。

推荐列表与电子简历可能同时存在，且都由 Chromium 暴露为 `Document`。用 `uia-query.ps1 -DocumentName "BOSS直聘" -DocumentUrlLike "*c-resume*"` 定向确认当前简历文档并采集正文；按用户要求不做简历姓名与卡片姓名的交叉核对，也不逐人请求用户身份确认。候选账本身份沿用当前卡片顺序、已核验的 UIA 控件归属及项目内候选键。不得使用 DOM 或 CUA 补读页面。

## 本机实测页面层级与控件归属（2026-10-27）

用户在 BOSS 页面留下的批注确认，同一视觉浮层中的控件分属不同 iframe，不能只按屏幕位置猜文档：

| 功能 | 浏览器层级 / URL | 已观察到的页面控件 | 操作定位约定 |
| --- | --- | --- | --- |
| 推荐卡片列表 | 推荐页 `https://www.zhipin.com/web/chat/recommend`；推荐 iframe `https://www.zhipin.com/web/frame/recommend/?jobid=...`。Win32 UIA 有时把卡片挂在 `Document: BOSS直聘` 主 URL 下 | `ListItem` / `ClassName=card-item`，卡片容器类如 `candidate-card-wrap css-type-1` | 先按实际 UIA `DocumentUrl` 选唯一可见文档，再核对当前候选人完整 Name 与 viewed 状态 |
| 悬浮电子简历正文 | 推荐 iframe 内嵌套的 `https://www.zhipin.com/web/frame/c-resume/?source=recommend`；用户批注确认该 frame 内的 `div#resume` 是简历正文区域 | 浏览器节点 `div#resume`；UIA 不一定直接映射 DOM `id`，可映射为 `AutomationId=resume`，滚动容器也可能表现为 `ClassName=resume-detail-wrap` | 只从当前 c-resume Document 定向查找；采集脚本先查已知 wrapper，再查 `AutomationId=resume` 及其滚动父级。不得用推荐卡片摘要替代简历正文，也不得用 DOM 读取正文 |
| 悬浮简历的打招呼按钮 | 用户批注显示按钮属于父级推荐 iframe `.../web/frame/recommend/?jobid=...`，不属于 c-resume 正文 frame | 页面节点 `div.button-chat-wrap.resumeGreet > span.btn-doc > div.button-list > button.btn-v2.btn-v2-new`；UIA 应以当前实际可见文档中 `Button` / `Name=打招呼` 定位 | 即使按钮视觉上在简历浮层右侧，也回到推荐文档核验按钮；核对候选人祖先、按钮类名和发送状态，不能在 c-resume 文档里因找不到而改点列表同名按钮 |
| 简历浮层“下一位” | 打开简历时的推荐主 Document；用户批注及本机 UIA 观察到 `Group` / `ClassName=turn-btn next`，名称可为空 | `turn-btn next` 是可复用的类名模式，不是可长期保存的控件句柄 | 每次在当前可见推荐 Document 中重新定位且要求唯一、可见、启用、支持 Invoke；从当前浮层/候选人祖先确认归属并绑定本次 RuntimeId。不得跨候选人复用旧 RuntimeId。Invoke 后核验 c-resume 文档或可见页面状态变化；`dispatched` 不代表已切换，不再比对候选姓名。 |

以上 URL、CSS selector 与 DOM `#resume` 来自用户浏览器批注，是页面层级说明，不是允许使用 DOM/网页脚本的授权。Chromium 嵌入方式可能令 UIA Document 名称或 URL 所在层变化；每次仍以当前定向 UIA 返回值为准。发现 `found 0` 时，先对已存在的外层推荐 Document、推荐 iframe、c-resume iframe分别做一次控件类型和名称/类名窄查；如页面未打开简历，先确认当前状态，不能把 c-resume 缺席当成异常刷新。

访问 UIA 与截图时不调用 `AutomationElement.SetFocus()`、`SetForegroundWindow()` 或其他强制聚焦手段。先在当前焦点不变的情况下尝试正确 Document URL、父/子 UIA 层和精确类名/AutomationId 查询；页面已经可见时可用 Win32 截图核对。若仍无法取得简历正文，保留原因并将该候选人记为 review/不发送，不能切换为 DOM、CUA、刷新或强制聚焦。

推荐页的可访问性文档 URL 会随 BOSS/Chromium 的嵌入方式变化，不能假定“推荐牛人”总在 `*frame/recommend*` 子文档中。2026-10-22 实测，页面主 URL `https://www.zhipin.com/web/chat/recommend` 对应的 `Document: BOSS直聘` 本身就包含“推荐牛人”、岗位标题和候选卡片；用 `*frame/recommend*` 查询返回 0，是 URL 过滤器不匹配，不代表页面不可见或推荐内容不存在。

## 安全调用器的 Document 范围复核

若查询已在某个子 `Document` 中找到目标，但 `guarded-uia-action.ps1` 报 `target_runtime_id_not_found`，先检查是否发生了“查询在局部 Document 中、调用器却从窗口根节点查 RuntimeId”的范围不一致。不要因此改用裸 `Invoke()`、坐标点击、鼠标或 CUA。

安全调用器按以下顺序恢复：

1. 从目标 JSON 读取必填 `document_url`，在当前窗口 UIA 树中定向枚举 `Document`，读取其 `ValuePattern` URL，并要求 URL 与目标值精确相等且只命中一个文档。
2. 只在该唯一 `Document` 子树内重新匹配 RuntimeId，并同时复核名称、提供时的 `class_name`、可见/启用状态、候选人祖先及文档归属；目标必须仍支持所需 UIA Pattern。
3. 匹配唯一且所有既有运行门禁通过后，才允许经 `safe_action.py` 执行一次操作。`document_url` 不唯一、目标已过期或候选人祖先不符时，保留错误并停止该动作。
4. 操作后做一次定向状态核验；若结果仍不明确，不重复调用。记录触发问题、文档范围及修复验证，并把通用修复同步到本 Skill 与更新日志。

该修复解决的是 UIA 查询范围不一致，不放宽目标身份、用户授权、运行门禁、去重或结果核验，也不构成跳过复核的理由。

若定向查询因窄 URL 过滤器返回 `found 0`，先将这视为定位条件可能不匹配：在不导航、不刷新、不使用 CUA、不强制聚焦的前提下，对同一页面按上述页面层级对已存在的外层推荐 Document、推荐 iframe、c-resume iframe分别做一次定向回查，并限制 `ControlType`、名称/类名和结果数量。记录返回的 `documentUrl`，之后在实际含目标控件的 Document 中查询；若当前没有打开简历，c-resume 缺席属正常状态。若页面已打开简历但子树空，使用只读 RawViewWalker 在该 c-resume Document 的有限层级内查看 UIA 映射，再按 `AutomationId=resume` / `ClassName=resume-detail-wrap` 精确查找。只有确认真正加载重置、主文档消失或候选控件异常归零时才进入停机流程；不得强制聚焦、重载或用 CUA 补查。

热态实测中，定位 `推荐牛人` Document 约 19 ms，查询全部“打招呼”按钮平均约 17 ms。单独运行 `uia-query.ps1` 的端到端耗时通常约 0.4–0.9 秒，主要来自 PowerShell 启动和 UIAutomation 初始化。需要连续核验时，优先在同一个 PowerShell 进程内缓存 Document 节点后重复查询。

## 最小读取流程

实际执行时遵守以下约束：

1. 每次页面操作前只查询当前操作所需的控件，不抓取整页。
2. 每次页面操作后只做一次定向核验；确认 Document 名称、岗位标题、候选人控件数量和目标控件状态。
3. 不并发发起多个 UIA 查询，不在无必要时轮询。
4. 页面跳转、刷新或布局变化后，旧的控件句柄、坐标和 RuntimeId 全部作废。
5. 查询候选人时优先使用：
   - `ControlType=Button, Name=打招呼`
   - `ControlType=ListItem, ClassName=card-item`
   - `ControlType=Text, NameLike=*岗位关键词*`

以下情况均视为页面异常重置，立即停止测试和操作：

- `推荐牛人` Document 消失或 URL 变为 `about:blank`
- 推荐 iframe 的 `jobid=null`
- 候选人“打招呼”按钮数量在未执行删除、筛选或滚动操作时异常归零
- 页面重新出现“加载中，请稍候”且账号、岗位或 Document 同步丢失

发生异常后不得自动点击、重试或重载。记录最后一个动作、异常前后的 Document/岗位/按钮数量，并立即关闭仍可控的本次自动化标签页。无法关闭或用户正在操作时，请用户完整关闭内置浏览器，而不是最小化；用户重新打开并确认恢复后，再继续定向 UIA 核验。

## 快速读取顺序

`Get-Process.MainWindowHandle=0`时不要猜句柄或假定进程名必为Codex。可用只读入口：

```text
pwsh -NoProfile -File scripts/resolve-recruiting-window.ps1 -ChatTitle <本聊天实际常驻标题>
```

该入口只枚举桌面顶层Codex/ChatGPT窗口并定向匹配可见应用Document标题及app URL，必须唯一才返回句柄；不聚焦、不点击。随后仍用`bind-codex-stop.ps1`完成聊天工具栏、scope及停止按钮核验，不能把窗口发现结果当作发送授权。窗口被遮挡或用户切到其他聊天时，保持停机/暂停规则。

1. 缓存顶层窗口句柄，避免每次重新枚举窗口。若 `Get-Process` 未返回窗口句柄或 `MainWindowHandle` 为 0，使用 Win32 `GetForegroundWindow` 取得当前前台窗口 HWND，再以 `AutomationElement.FromHandle` 定向定位 BOSS 文档；不要因此改用 CUA。
2. 从窗口根节点定位一次 `Document`，例如 `BOSS直聘`，后续只在该文档子树内查询。
3. 优先使用 `scripts/uia-query.ps1` 的带过滤查询：
   - `ControlType`：`Button`、`ListItem`、`Text`、`Document`
   - `Name`：精确名称，如 `打招呼`、`推荐牛人`
   - `ClassName`：如 `btn-greet`、`boss-popup__close`
4. 不要每次从顶层窗口枚举全部后代；这种全树查询通常比截图更慢。
5. 同一页面状态内复用已定位的文档节点和控件；页面跳转、加载完成或刷新后再重新定位。
6. 页面滚动时优先使用 `ScrollPattern` 和 `ScrollItemPattern.ScrollIntoView`，不要反复截图后目测滚动。
7. 鼠标模式点击前使用 `AutomationElement.FromPoint` 或最新的控件矩形做命中复核；命中目标与预期控件不一致时停止。UIA 模式按[点击方式开关](click-modes.md)复核实际目标与祖先归属、检查 Invoke 支持后调用一次，不用屏幕命中代替控件身份核验。
8. 除电子简历正文的例行长截图外，只在以下场景截图：
   - 页面结构与控件树不一致
   - 点击发送、举报、删除等高风险动作前
   - 异常或结果不明时留证

## 卡片点击命中复核（2026-10-22）

本节坐标和轨迹检查用于 `use_mouse_trajectory=true`。关闭轨迹时，在已核验的 `card-item` 内定向定位支持 Invoke 的内部控件（例如 `card-inner common-wrap css-type-1`），按[点击方式开关](click-modes.md)调用；打开简历后的核验、同事去重与不重试要求两种模式相同。

- 在用 `AutomationElement.FromPoint` 做坐标命中测试的 PowerShell 进程内，先调用 `user32!SetProcessDPIAware()`。未设置 DPI awareness 时，实测命中会落到页面大小的匿名 `Group`；设置后仍可能先返回内层 `Group`，不能把它直接当作卡片。
- 从命中元素沿 `TreeWalker.RawViewWalker` 向上检查祖先，直到找到 `ControlType.ListItem` 且 `ClassName=card-item`；核对该 ListItem 的完整 `Name` 含预期候选人姓名，并与当前可见卡片摘要一致。未找到或姓名不符时不点击。
- 点击坐标取最新矩形内的可见安全位置；移动轨迹的起点也须处于窗口内容安全区并留出边距，避免随机假起步越出边界。先 `-DryRun` 检查轨迹，再做一次物理点击，点击后只进行一次定向核验。
- 用户完成推荐页人工审核并回复 `1` 后，按当前筛选列表顺序用 UIA 检查候选卡片状态，从第一个明确未查看的卡片开始。先按候选姓名 `Text` 定位 `ListItem`（`ClassName=card-item`），再**在该 ListItem 的子树内**用有界 `RawViewWalker` 查找唯一的包装节点；已观测结构为 `li.card-item > div.candidate-card-wrap...`，所以 `candidate-card-wrap` 是卡片内部子节点，不是 ListItem 的祖先。只检查当前候选卡片，深度最多 8 层、节点最多 300 个。包装节点 `ClassName` 含 `has-viewed` token 时视为已查看并跳过；唯一包装节点可读且不含该 token 才视为未查看。不得单凭文字灰色或颜色判断；包装节点未暴露、匹配不唯一或状态冲突时暂停请用户确认。拟人轨迹模式仍须通过 UIA 矩形与 `FromPoint` 确认目标属于该卡片，轨迹全程位于浏览器内容边界内。点击后只需确认 `c-resume` 文档出现；不做姓名比对，也不逐人请求用户确认。简历正文仍按[长截图与 RapidOCR](resume-capture-ocr.md)读取并评分；文档未出现时暂停该候选人，不重试打开。右侧箭头不可见时，可通过受门禁的 Right/Left/Escape 按键导航，详见[点击方式开关](click-modes.md)。简历打开后按[同事去重](coworker-dedup.md)读取右下角“同事沟通进度”的首条时间：严格早于7天才跳过，恰好7天或7天内继续，读取失败不当作空记录。

## 快速查询命令

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass `
  -File scripts/uia-query.ps1 `
  -WindowHandle <HWND> `
  -DocumentName "BOSS直聘" `
  -DocumentUrlLike "*zhipin.com/web/chat/recommend*" `
  -ControlType Button `
  -Name "打招呼" `
  -VisibleOnly `
  -Limit 20
```

查询候选卡片摘要时可使用 `-ControlType ListItem -NameLike "*候选人姓名*"`。避免不带名称、类名或控件类型的全树查询。

### `uia-query.ps1` 的 NameLike-only 查询

`NameLike` 由脚本在目标 Document 子树中做本地通配匹配，不能直接转换成 UIA 精确名称条件。只传 `-NameLike` 时条件集合为空；旧代码仍构造 `AndCondition`，PowerShell 会报“找不到适当的构造函数”。脚本现在在这种情况下使用 `Condition.TrueCondition`，再按必填的窄 `NameLike` 过滤；如果查询卡片状态，优先同时传 `-ControlType ListItem -ClassName card-item`，并核对卡片内部 `candidate-card-wrap` 的完整类名。不要把 0 条或构造函数错误解读成候选人不在页面。

只核对列表数量或控件位置时可加 `-Compact`（默认名称最多 96 字符，可用 `-NameChars` 调整），省去 ValuePattern 和其他详细字段。`nameTruncated=true` 表示名称不完整；紧凑结果不得用于稳定 ID 判断、发送目标确认或点击前命中复核，这些场景仍使用完整的定向查询。默认输出格式不变。

## PowerShell 查询示例

```powershell
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$hwnd)

$nameCondition = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::NameProperty,
  "推荐牛人"
)
$typeCondition = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
  [System.Windows.Automation.ControlType]::Document
)
$document = $root.FindFirst(
  [System.Windows.Automation.TreeScope]::Descendants,
  (New-Object System.Windows.Automation.AndCondition($nameCondition, $typeCondition))
)
```

仅查询按钮名称：

```powershell
$condition = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::NameProperty,
  "打招呼"
)
$buttons = $document.FindAll(
  [System.Windows.Automation.TreeScope]::Descendants,
  $condition
)
```

## 页面刷新时的处理

- 页面 URL、岗位标题或文档节点变化时，旧控件句柄作废。
- 重新定位文档和控件，不沿用旧坐标。
- 若控件树连续出现“正在加载中”或文档内容反复重置，停止当前运行。
- 若候选人控件数量异常归零，停止并请求用户完整关闭、重新打开内置浏览器；不要自动复原。
- UI Automation 的 `RuntimeId` 只在当前页面会话内有效，不能替代平台候选人 ID。

## 遮挡、最小化与虚拟化

- 页面被其他窗口遮挡但未最小化时，已生成的 UIA 节点通常仍可读取，`InvokePattern` 也可能可用；但这不是实际发送可用的充分条件。
- 页面最小化、标签完全隐藏或 Chromium 暂停渲染时，可访问性节点可能缺失或失效；此时停止操作。
- 列表虚拟化区域之外的候选人可能不存在于 UIA 树中，必须使用 `ScrollPattern` 或 `ScrollItemPattern.ScrollIntoView` 后再查询。
- 底层控件被弹窗、蒙层或其他模态界面遮挡时，即使 UIA 能调用 `InvokePattern`，也不得发送。
- 实际发送必须同时满足：Codex 最大化、内置浏览器可见、目标控件来自当前可见 UIA 层、账本 `gate` 和发送前复查均通过；鼠标模式另须 `AutomationElement.FromPoint` 命中复核一致，UIA 模式另须目标元素/候选人祖先归属核验一致且支持 `InvokePattern`。点击开关不放宽遮挡、最小化或模态遮挡下的发送要求。
