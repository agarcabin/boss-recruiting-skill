# 点击方式开关

所有页面点击统一按本轮 `use_mouse_trajectory` 分流，默认值为 `false`；未指定时统一采用 Win32 UIA `InvokePattern.Invoke()`。适用于打开/切换电子简历、选择页签、打招呼及打开聊天小窗；不得在各步骤自行选择另一种点击方式。仅在用户明确开启 `true` 后才使用拟人鼠标模式。

| 配置 | 点击方式 | 鼠标移动 |
| --- | --- | --- |
| `false`（默认，含未指定） | 对最新定位的 Win32 UIA 控件调用 `InvokePattern.Invoke()` | 不移动鼠标，不发送鼠标按下/抬起；不调用 `move-click.ps1`、`idle_mouse.py`、`SetCursorPos` 或其他鼠标点击替代方式 |
| `true`（用户明确开启） | 沿用 [鼠标轨迹](mouse-trajectory.md)：最新 UIA 定位与命中复核后调用 `scripts/move-click.ps1` | 保留原拟人轨迹、点击后移动及等待时移动 |

所有点击均经 `safe_action.py`：默认显式使用 `--action invoke`，脚本省略 `--action` 时也默认为 `invoke`；用户开启拟人轨迹后才使用 `--action mouse --mouse-args <json>`。不得将 UIA 调用失败视为开启鼠标模式的授权。

本开关只决定点击方式，不改变发送授权、岗位/话术核验、同事去重、简历证据、评分、归档与账本 `gate` / `reserve` 要求。窗口可见性、最小化停机及键盘输入焦点要求仍按运行流程执行；切换为 UIA 不表示已验证后台或最小化发送可用。

## 关闭拟人轨迹时的 UIA 点击

1. 每次操作前检查 `gate`，只在本次实际 BOSS Document 和当前候选人的局部子树中定向查找目标。核对文档 URL、候选人身份、目标名称/类名、`IsEnabled` 与当前页面状态。页面跳转、滚动或布局改变后重新定位，不复用旧控件。
2. 检查目标是否支持 `InvokePattern`。候选人外层 `ListItem.card-item` 可能仅支持 `ScrollItemPattern`；应在已确认的该卡片内定向查找可调用的 `Group`，例如实测的 `ClassName=card-inner common-wrap css-type-1`，并沿 UIA 祖先确认它属于同一候选人卡片。不要把外层卡片不支持 Invoke 误判为内部控件也不支持。
3. 打招呼时必须定位当前候选人的实际“打招呼”按钮，核对身份、名称与类名；不得用名称为空的聊天包装容器代替已核验按钮。举报、不合适、删除以及 `btn-report`、`btn-quxiao` 仍禁止调用，不因使用 UIA 而绕过物理点击脚本中的保护。
4. `TryGetCurrentPattern(InvokePattern.Pattern, ...)` 返回支持后，发送前仍须取得 `reserve=ready` 并再次通过 `gate`；每个动作只调用一次 `Invoke()`。UIA 点击用目标元素及其祖先关系核验身份，不依赖屏幕坐标或 `AutomationElement.FromPoint`，不调用鼠标拟人 skill。
5. 调用正常返回仅表示接口调用完成。打开简历后定向核验 `c-resume` 文档；发送后核验该候选人的已发送状态/消息。核验不明时停止，发送结果按 `unknown` 处理，不重复调用，不自动改用鼠标或 CUA。找不到目标、不支持 Invoke、控件失效或调用异常时同样停止并说明原因。
6. 调用前后分别记录带时区的 `clickStartedAt`、`clickEndedAt`，与鼠标模式使用相同字段，另记 `clickMethod=uia_invoke`。这两个时间是实际 UIA 调用边界，不是已成功打开或发送的证明；只有定向核验成功后才用于候选人开始/离开计时和后续记账。核验失败保留未完成，不编造结果。

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
