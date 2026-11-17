> 1.0.13新增功能及命令见[plan-features.md](plan-features.md)，包括同事前置、收藏、快速启动、今日表格统计和防息屏。

> 2026-10-27现行口径：先按 [evaluation-modes.md](evaluation-modes.md) 分流。card不打开电子简历、不做OCR及详情同事检查；resume保留下文对应流程。操作入口见click-modes.md；不要求每次gate/reserve/token，运行控制以control-policy.md为准。

# 同事沟通进度去重（2026-10-26用户指定）

## 唯一的平台同事时间规则

打开当前候选人电子简历，读取右下角“同事沟通进度”，不要读取“我的沟通进度”。检查面板内各条同事发起沟通时间，不限定同事沟通过的岗位与当前岗位相同。2026-11-02更新：

- 任意一条联系距今不超过7天（168小时，包含恰好7天）：重复跳过，不评分、不发送。
- 完整检查的所有联系都严格超过7天：继续本岗位评估；“继续”不等于立即发送。旧单条记录缺少完整性声明时先重新查询，不凭旧首条时间放行。
- 面板明确显示没有同事沟通记录：继续。
- 用户2026-10-27明确指定“如果没找到，那就是没打过”。当前BOSS页面及文档有效，在主推荐/推荐iframe/简历iframe中完成分层定向查询后仍未找到同事进度，记录 `state:not_found, lookup_completed:true` 并继续；保留实际查询证据，不改写成明确空面板的 `empty`。
- 已找到面板但未确认选中同事页签、任一时间缺失/模糊/未来，或存在未读取的滚动/隐藏记录，以及文档缺失/异常：`unavailable`，不自动发送。不能把技术异常当作“未找到记录”。

无时区的完整日期时间按北京时间UTC+08:00解释。只接受带年份且有时分的时间，不猜测“昨天”或缺少年份的日期。本规则优先于岗位文件中历史“近7天已沟通跳过/备选”及本地姓名去重说明；不用修改历史已确认岗位文件。

## 浏览器插件读取与判定

1.4.16-beta 使用后台 UIA 定向读取同事面板、按需 Invoke “同事沟通进度”并核实已选中，再读取实际时间与完整性。不读取“我的沟通进度”，不产生浏览器交接，也不自动前置窗口。查询、点击和重试合计5秒；超过5秒，或面板不可读/读取失败，都立即静默继续，不创建对话回执、不逐人提醒，也不能改写为无记录。

查询、点击和重试累计5秒；超过5秒统一记录超时并静默继续，不逐人提示。

返回 state 为 records、兼容旧 first_record、empty、not_found 或 unavailable。实际记录采用 records:[{greeting_at,evidence}] 及 records_complete:true/false；完整查找确实无面板才返回 not_found、lookup_completed:true。明确读到空面板才返回 empty。任何未读滚动/隐藏记录、模糊时间或文档失联都如实记录，不伪造完整。

```json
{"state":"records","records":[{"greeting_at":"2026-10-20 09:22","evidence":"实际记录原文"}],"records_complete":true,"lookup_completed":true,"evidence":"本次实际观察"}
```

可用 coworker_progress.py 在本地判定结果，它不执行页面动作。阈值以当前岗位与运行快照为准；配置0时不查询。原有近期记录优先跳过及未知逐人通知规则保留。

## 逐人留痕

电子简历打开并取得姓名后，用原始候选标识登记本次访问（可由记录入口自动补齐），并按实际情况调用`electronic-opened`，使同事去重跳过者也计入查看人数。然后执行上述读取/判定。

判定skip时不做OCR或岗位评分，使用：

```text
python scripts/candidate_log.py coworker-skip --run <run_id> --candidate-id <稳定标识> --candidate-name <当前姓名> --input <coworker.json>
python scripts/ledger.py note --run <run_id> --candidate-id <稳定标识> --result skipped
python scripts/candidate_log.py sync --run <run_id> --candidate-id <稳定标识>
```

报表显示“重复跳过”、综合分留空，不将未评分者伪装为低分。正常离开时仍调用finalize-timing与candidate-finish，不停整轮；计入最终重复跳过数量。

判定continue后才按电子简历流程OCR与评分，将同一个真实观测对象放入评估JSON的`coworker_progress`。`record`拒绝缺少检查、任意同事联系不超过7天或检查不可读的greet；`reserve`会在发送前按当时的时间重新判断7天边界。普通评分或其他条件仍独立核对。

## 本地Excel/同名去重默认关闭

Excel继续输出，本地assessments历史仍保存，但不读取Excel文件或因本地历史同名就跳过。`lookup-name`默认返回`state=disabled`，不打开数据库。仅在用户明确要求启用时才使用：

```text
python scripts/candidate_log.py lookup-name --name <姓名> --enable-local-excel-dedup
```

稳定ID仅用于记账，不作历史去重；unknown不阻塞后续，允许重新读取页面后按当前状态有界重试，实际成功以页面证据为准。
