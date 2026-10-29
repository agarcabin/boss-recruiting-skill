# 点击方式

现行控制口径见 [control-policy.md](control-policy.md)。默认use_mouse_trajectory=false，使用Win32 UIA Invoke；用户明确开启true后才用拟人鼠标，不自动切换模式。CUA/DOM禁用规则不变。

用本次定向UIA取得目标RuntimeId和窗口句柄，交给safe_action。不再对名称、类名、候选人祖先、活跃候选键、generation、deadline和token作前置匹配。RuntimeId用于寻址，元素不存在或不支持Invoke仍会返回真实工具错误；不能凭猜测操作。

```text
python scripts/safe_action.py --run <id> --target <当前UIA目标.json> --action invoke
python scripts/safe_action.py --run <id> --target <当前Document.json> --action key --key Right
```

token与generation为兼容参数，可省略。招呼动作仍按已记录的岗位匹配、同事检查及本次数量目标执行；token仅是自动记账引用，不是操作凭据。

导航键Right/Left/Escape要求焦点已在相应BOSS Document，不抢焦点。加载异常可在焦点正确时用Refresh刷新一次，再重新定向读取页面。不允许用键盘导航发送消息。

single不执行继续沟通或追加文本；triple的文本操作要求真实聊天输入框已有焦点。举报、不合适、删除及btn-report/btn-quxiao禁用不变。

动作返回dispatched只代表已派发。成功以平台可读状态为准，unknown不再阻塞后续或要求人工核销。重新读取平台状态后明确仍可招呼可重试一次。

保留clickStartedAt/clickEndedAt原始ISO字符串用于可选计时，缺失时不补造点击时间，也不阻止下一位。普通窗口遮挡可后台Invoke，截图须取得真实内容。
