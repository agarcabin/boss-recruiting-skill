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

推荐列表与电子简历可能同时存在，且都由 Chromium 暴露为 `Document`。读取当前打开的电子简历身份时，用 `uia-query.ps1 -DocumentName "BOSS直聘" -DocumentUrlLike "*c-resume*"` 明确选择实际 URL 含 `c-resume` 的文档，再在该文档内查询姓名；不要把推荐卡片姓名当作当前打开的电子简历姓名。

推荐页的可访问性文档 URL 会随 BOSS/Chromium 的嵌入方式变化，不能假定“推荐牛人”总在 `*frame/recommend*` 子文档中。2026-10-22 实测，页面主 URL `https://www.zhipin.com/web/chat/recommend` 对应的 `Document: BOSS直聘` 本身就包含“推荐牛人”、岗位标题和候选卡片；用 `*frame/recommend*` 查询返回 0，是 URL 过滤器不匹配，不代表页面不可见或推荐内容不存在。

若定向查询因窄 URL 过滤器返回 `found 0`，先将这视为定位条件可能不匹配：在不导航、不刷新、不使用 CUA 的前提下，对同一可见页面用 `-DocumentName "BOSS直聘" -DocumentUrlLike "*zhipin.com/web/chat/recommend*"` 做一次定向回查，并限制 `ControlType`、名称和结果数量。记录返回的 `documentUrl`，之后在该实际 Document 中查询“推荐牛人”或目标控件。仅当 UIA 已实际显示子文档 URL 含 `frame/recommend` 时才使用该 URL 模式；若主 URL 定向回查也找不到 BOSS 文档，或出现加载重置、候选控件异常归零等异常，再按停机规则处理，不得重载或用 CUA 补查。

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
- 用户完成推荐页人工审核并回复 `1` 后，直接点击第一张当前可见的 `card-item`，点击前不截图判断姓名颜色或是否已查看。仍须通过 UIA 控件矩形和 `FromPoint` 命中确认点击位置属于卡片，且轨迹全程位于浏览器内容边界内。点击后定向查询 `c-resume` 文档；未出现时不重试，暂停并请用户手动打开电子简历。本地Excel/历史同名去重默认关闭；简历打开后按[同事去重](coworker-dedup.md)定向读取右下角“同事沟通进度”的首条时间。超过7天跳过，恰好7天或7天内继续，读取失败不当作空记录。

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
