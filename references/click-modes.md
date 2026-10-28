# 点击方式开关

所有页面点击统一按本轮 `use_mouse_trajectory` 分流，默认值为 `false`；未指定时统一采用 Win32 UIA `InvokePattern.Invoke()`。适用于打开/切换电子简历、选择页签、打招呼及打开聊天小窗；不得在各步骤自行选择另一种点击方式。仅在用户明确开启 `true` 后才使用拟人鼠标模式。

推荐页已观察到的“下一位”箭头可复用 UIA 定位模式：`ControlType=Group`、`ClassName=turn-btn next`，名称可能为空。此模式只固定类名，不固定 RuntimeId、矩形、Index 或句柄。每次切换前仍须从当前可见推荐 Document 重新查询唯一箭头，沿 UIA 祖先核对它属于当前电子简历浮层及其候选人；检查可见、启用和 InvokePattern 后，经 `safe_action.py --action invoke` 调用一次。结果以 c-resume 文档或可见页面状态变化核验，不能只凭 `dispatched` 继续；不再比对候选姓名。

| 配置 | 点击方式 | 鼠标移动 |
| --- | --- | --- |
| `false`（默认，含未指定） | 对最新定位的 Win32 UIA 控件调用 `InvokePattern.Invoke()` | 不移动鼠标，不发送鼠标按下/抬起；不调用 `move-click.ps1`、`idle_mouse.py`、`SetCursorPos` 或其他鼠标点击替代方式 |
| `true`（用户明确开启） | 沿用 [鼠标轨迹](mouse-trajectory.md)：最新 UIA 定位与命中复核后调用 `scripts/move-click.ps1` | 保留原拟人轨迹、点击后移动及等待时移动 |

所有点击均经 `safe_action.py`：默认显式使用 `--action invoke`，脚本省略 `--action` 时也默认为 `invoke`；用户开启拟人轨迹后才使用 `--action mouse --mouse-args <json>`。不得将 UIA 调用失败视为开启鼠标模式的授权。

本开关只决定点击方式，不改变发送授权、岗位/话术核验、同事去重、简历证据、评分、归档与账本 `gate` / `reserve` 要求。窗口可见性、最小化停机及键盘输入焦点要求仍按运行流程执行；切换为 UIA 不表示已验证后台或最小化发送可用。

## 关闭拟人轨迹时的 UIA 点击

1. 每次操作前检查 `gate`，只在本次实际 BOSS Document 和当前候选人的局部子树中定向查找目标。核对文档 URL、候选人身份、目标名称/类名、`IsEnabled` 与当前页面状态。页面跳转、滚动或布局改变后重新定位，不复用旧控件。名称为空的可调用 Group 仅在目标 JSON 同时提供实测 `class_name` 与本次 `runtime_id` 时允许；守卫逐项精确匹配两者并继续核验候选人祖先和文档 URL。
2. 检查目标是否支持 `InvokePattern`。候选人外层 `ListItem.card-item` 可能仅支持 `ScrollItemPattern`；应在已确认的该卡片内定向查找可调用的 `Group`，例如实测的 `ClassName=card-inner common-wrap css-type-1`，并沿 UIA 祖先确认它属于同一候选人卡片。若其 Name 为空，须将空 Name、精确 `class_name` 和 `runtime_id` 一并交给 `safe_action.py` 的守卫核验。不要把外层卡片不支持 Invoke 误判为内部控件也不支持。
3. 打招呼时必须定位当前候选人的实际“打招呼”按钮，核对身份、名称与类名；不得用名称为空的聊天包装容器代替已核验按钮。举报、不合适、删除以及 `btn-report`、`btn-quxiao` 仍禁止调用，不因使用 UIA 而绕过物理点击脚本中的保护。
4. `TryGetCurrentPattern(InvokePattern.Pattern, ...)` 返回支持后，发送前仍须取得 `reserve=ready` 并再次通过 `gate`；每个动作只调用一次 `Invoke()`。UIA 点击用目标元素及其祖先关系核验身份，不依赖屏幕坐标或 `AutomationElement.FromPoint`，不调用鼠标拟人 skill。
5. 调用正常返回仅表示接口调用完成。打开简历后定向核验 `c-resume` 文档；发送后核验该候选人的已发送状态/消息。核验不明时停止，发送结果按 `unknown` 处理，不重复调用，不自动改用鼠标或 CUA。找不到目标、不支持 Invoke、控件失效或调用异常时同样停止并说明原因。
6. 调用前后分别记录带时区的 `clickStartedAt`、`clickEndedAt`，与鼠标模式使用相同字段，另记 `clickMethod=uia_invoke`。这两个时间是实际 UIA 调用边界，不是已成功打开或发送的证明；只有定向核验成功后才用于候选人开始/离开计时和后续记账。核验失败保留未完成，不编造结果。

### 保留 UIA 动作的原始计时字符串

Windows PowerShell 的 `ConvertFrom-Json` 会把 ISO 8601 字段自动转换为本地 `DateTime`。随后将属性传给 `--ended-at` 会变成区域格式（如 `10/27/2026 17:41:23`），丢失时区/精度并被账本拒绝。安全动作输出中的 `output` 本身是嵌套 JSON 字符串；不要再把这段字符串交给 `ConvertFrom-Json` 取时间。

从原始嵌套输出提取时间文本并原样传递：

```powershell
$action = $actionRaw | ConvertFrom-Json
$match = [regex]::Match([string]$action.output, '"clickEndedAt"\s*:\s*"([^"]+)"')
if (-not $match.Success) { throw "safe_action 未返回原始 clickEndedAt；保留动作输出并停止计时记账。" }
$clickEndedAt = $match.Groups[1].Value
# 用原始 ISO 8601 字符串调用 finalize-timing 和 candidate-finish；不要先转成 DateTime。
```

若当前 `safe_action` 输出没有被保存，不能用错误消息中区域化、已丢失精度的时间反推原值；停止后续候选人操作并保留未完成计时，待从原始动作输出恢复。

UIA 调用示例（`$target` 必须已按上述步骤完成定位、归属和门禁核验）：

```powershell
$invoke = $null
if (-not $target.TryGetCurrentPattern(
    [System.Windows.Automation.InvokePattern]::Pattern, [ref]$invoke)) {
    throw "目标不支持 UIA InvokePattern；停止，不回退鼠标点击。"
}
$clickStartedAt = Get-Date -Format o
$invoke.Invoke()
$clickEndedAt = Get-Date -Format o
[pscustomobject]@{
    clickMethod = "uia_invoke"
    clickStartedAt = $clickStartedAt
    clickEndedAt = $clickEndedAt
}
# 然后进行一次定向结果核验；不要仅凭 Invoke 返回记录成功。
```

关闭轨迹时等待使用普通计时等待，不运行圆周移动。聊天小窗内的多句话术仍按原有键盘发送规则执行：先确认前台和焦点，再逐句粘贴、回车、核验；不因 UIA 能调用按钮就向其他前台窗口发送按键。


## 简历键盘导航

Canvas 简历未暴露姓名时，下一位/上一位箭头可使用本轮 UIA 实测的 `candidate_scope_runtime_id`（`lib-standard-resume` 浮层）及 `navigation_resume_runtime_id`（当前唯一可见 c-resume Document）绑定。守卫从简历 Document 经有界 RawViewWalker 验证其属于同一浮层；仅允许 `turn-btn next/prev` 的导航 Invoke，不适用于发送。safe_action 仍核验当前账本候选键、generation、状态和截止。跨 iframe 的局部 FindAll 可能漏掉 Document，不能把它直接判为空；可复用窗口内已定向枚举的 Documents 并核对原始祖先。

当 resume 浮层右侧箭头不可见时，可用 `safe_action.py --action key` 导航：`--key Right` 下一份，`Left` 上一份，`Escape` 回到卡片列表。仅允许这三个键；派发仍须通过当前运行 gate、候选人账本绑定、generation 和共享互斥锁。目标 JSON 绑定当前 BOSS `Document` 的 RuntimeId 与 URL，执行前确认当前焦点属于该 Document；不调用 `SetFocus()` 或强制抢焦点。焦点不在 BOSS 页面时停止。按键后定向核验 `c-resume` 文档或卡片列表状态；结果不明不重复按键。键盘导航不用于发送招呼或聊天消息。
