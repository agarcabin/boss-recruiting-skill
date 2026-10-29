# 招呼方式开关

用户于2026-10-28指定两种方式，当前全部岗位默认使用单次打招呼；新建、旧配置缺省及导入缺省的岗位也默认单次。此规则优先于岗位正文中的旧三句话术流程，固定话术原文保留供三连式使用。

| 选项 | 配置值 | 执行行为 |
| --- | --- | --- |
| 单次打招呼（默认） | `single` | reserve后仅点一次“打招呼”，定向核验平台首条招呼成功并resolve；不点“继续沟通/继续打招呼”，不开聊天小窗，不发送第二、三句。完成同步、适用证据归档后直接切换下一份简历或卡片，记录切换时间并结束当前候选人。 |
| 三连式打招呼 | `triple` | 保持既有方式：点“打招呼”并核验首句，点“继续沟通”打开聊天小窗，按已审核话术分别发送第二句介绍和第三句索简历；逐句取token、核验、记账。 |

## 对话入口与配置

选择approved岗位后展示“招呼方式：单次打招呼（默认），可切换三连式打招呼”。用户未要求切换时直接沿用默认，不额外增加确认步骤，不改变首页六项编号。用户说“单次打招呼”或“三连式打招呼”即本次方式选择，不等同于实际发送授权。

岗位默认值保存在其 `project.json` 的 `greeting_mode`；岗位front matter可指定同名字段。新运行的优先级：本轮明确选择 `--greeting-mode` > 岗位front matter > project.json > `single`。可用命令：

```text
python scripts/ledger.py start --profile <已审核岗位.md> --stop-binding <本聊天绑定.json> --greeting-mode single
python scripts/ledger.py start --profile <已审核岗位.md> --stop-binding <本聊天绑定.json> --greeting-mode triple
python scripts/ledger.py status --run <id>
```

start将实际方式写入本轮 `rule_snapshot.greeting_mode`，start/status返回实际值；导出/重新登记保留岗位默认方式。本轮选择不自动覆盖岗位默认值。此开关只选用原已审核话术的发送段数，不改筛选条件、话术原文或approval。

## 执行与兼容

- `single` 只产生首句attempt，candidate-finish仅要求第1句sent；禁止为第2/3句取token，safe_action拦截继续沟通、继续打招呼及追加文本发送。无需凑齐三句或伪造第2/3句状态。
- `triple` 按顺序尝试已选话术，如实记录各句状态；未完成后续句不阻止进入下一位。发送结果不明记unknown，不阻塞后续；重新查询后明确可招呼时允许一次重试；证据、去重、授权、间隔、停止和归档约束不变。
- 已有运行保持冻结快照；旧快照未含该字段时按原三连式处理，不回写历史或活动运行。用户要把旧运行改为单次时，先正常结束，再以 `single` 新开运行；未决消息不再阻塞新运行。
