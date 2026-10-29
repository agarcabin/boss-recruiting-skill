> 1.0.13新增功能及命令见[plan-features.md](plan-features.md)，包括同事前置、收藏、快速启动、今日表格统计和防息屏。

> 2026-10-27现行口径：先按 [evaluation-modes.md](evaluation-modes.md) 分流。card不打开电子简历、不做OCR及详情同事检查；resume保留下文对应流程。操作入口见click-modes.md；不要求每次gate/reserve/token，运行控制以control-policy.md为准。

# 同事沟通进度去重（2026-10-26用户指定）

## 唯一的平台同事时间规则

打开当前候选人电子简历，读取右下角“同事沟通进度”，不要读取“我的沟通进度”。只用显示顺序第一位同事的发起沟通时间；不按时间重新排序，不采用第二位同事，也不限定同事沟通过的岗位与当前岗位相同。用户本次明确指定：

- 首条时间严格早于当前时间减7天（超过168小时）：重复跳过，不评分、不发送。
- 7天内或恰好7天：继续本岗位评估；“继续”不等于立即发送。
- 面板明确显示没有同事沟通记录：继续。
- 用户2026-10-27明确指定“如果没找到，那就是没打过”。当前BOSS页面及文档有效，在主推荐/推荐iframe/简历iframe中完成分层定向查询后仍未找到同事进度，记录 `state:not_found, lookup_completed:true` 并继续；保留实际查询证据，不改写成明确空面板的 `empty`。
- 已找到面板但未确认选中同事页签、首条时间缺失/模糊/未来或面板不在顶部，以及文档缺失/异常：`unavailable`，不自动发送。不能把技术异常当作“未找到记录”。

无时区的完整日期时间按北京时间UTC+08:00解释。只接受带年份且有时分的时间，不猜测“昨天”或缺少年份的日期。本规则优先于岗位文件中历史“近7天已沟通跳过/备选”及本地姓名去重说明；不用修改历史已确认岗位文件。

## 定向读取与判定

先以最新UIA定向核实并按需选择“同事沟通进度”页签；需要点击时，按[点击方式开关](click-modes.md)执行：拟人轨迹开启用原鼠标流程，关闭用UIA InvokePattern，不移动鼠标。不得仅因截图上曾显示该页签就传已确认。随后运行只读提取器：

```powershell
pwsh -NoProfile -File scripts/read-coworker-progress.ps1 -WindowHandle <当前HWND> -CoworkerTabConfirmed |
  Set-Content -LiteralPath <当前候选人-coworker.json> -Encoding utf8
python scripts/coworker_progress.py --input <当前候选人-coworker.json>
```

提取器先在唯一可见的BOSS文档里定向定位“同事沟通进度”标题；无标题时，在实际存在的主推荐、推荐iframe和简历iframe分别定向复查并按RuntimeId去重。面板读取限制最多6层小范围祖先、120个文本节点；不提升为整页扫描。按控件纵向位置选第一条“向Ta发起沟通”，只取该条日期。默认文档URL模式是`*zhipin.com/web/chat/recommend*`；实测文档不同时使用本轮UIA实际返回的URL模式。提取器只读、不点击、不滚动，不使用CUA、DOM、网页脚本、导航或刷新；完整查找确实未发现标题才返回not_found，文档/数据异常返回unavailable。

观测JSON契约示例：

```json
{"state":"first_record","first_greeting_at":"2026-06-05 09:22","evidence":"UIA：同事沟通进度首条，实际控件文本与时间"}
```

`state`为`first_record`、`empty`、`not_found`或`unavailable`。`not_found`必须有`lookup_completed:true`及实际查询证据；只有明确读到空面板才用`empty`。`evidence`描述当前候选人的实际观察，不能照抄示例。旧`unavailable`历史记录不自动改判。

页签未找到时可省略 `-CoworkerTabConfirmed`：提取器只读检查实际存在的文档，完整查找仍无标题才输出 `not_found`。标题存在但未确认选中时返回 `unavailable`；不得虚传已确认。URL匹配不到唯一可见起始文档也返回 `unavailable`。

## 逐人留痕

电子简历打开并取得姓名后，用原始候选标识登记本次访问（可由记录入口自动补齐），并按实际情况调用`electronic-opened`，使同事去重跳过者也计入查看人数。然后执行上述读取/判定。

判定skip时不做OCR或岗位评分，使用：

```text
python scripts/candidate_log.py coworker-skip --run <run_id> --candidate-id <稳定标识> --candidate-name <当前姓名> --input <coworker.json>
python scripts/ledger.py note --run <run_id> --candidate-id <稳定标识> --result skipped
python scripts/candidate_log.py sync --run <run_id> --candidate-id <稳定标识>
```

报表显示“重复跳过”、综合分留空，不将未评分者伪装为低分。正常离开时仍调用finalize-timing与candidate-finish，不停整轮；计入最终重复跳过数量。

判定continue后才按电子简历流程OCR与评分，将同一个真实观测对象放入评估JSON的`coworker_progress`。`record`拒绝缺少检查、首条超过7天或检查不可读的greet；`reserve`会在发送前按当时的时间重新判断7天边界。普通评分或其他条件仍独立核对。

## 本地Excel/同名去重默认关闭

Excel继续输出，本地assessments历史仍保存，但不读取Excel文件或因本地历史同名就跳过。`lookup-name`默认返回`state=disabled`，不打开数据库。仅在用户明确要求启用时才使用：

```text
python scripts/candidate_log.py lookup-name --name <姓名> --enable-local-excel-dedup
```

稳定ID仅用于记账，不作历史去重；unknown不阻塞后续，允许重新读取页面后按当前状态有界重试，实际成功以页面证据为准。
