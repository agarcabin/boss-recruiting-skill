> 2026-10-27现行口径：先按 [evaluation-modes.md](evaluation-modes.md) 分流。card不打开电子简历、不做OCR及详情同事检查；resume保留下文对应流程。所有外部动作经safe_action.py，不裸调用UIA Invoke/按键/鼠标；历史示例仅作底层技术参考。

# 同事沟通进度去重（2026-10-26用户指定）

## 唯一的平台同事时间规则

打开当前候选人电子简历，读取右下角“同事沟通进度”，不要读取“我的沟通进度”。只用显示顺序第一位同事的发起沟通时间；不按时间重新排序，不采用第二位同事，也不限定同事沟通过的岗位与当前岗位相同。用户本次明确指定：

- 首条时间严格早于当前时间减7天（超过168小时）：重复跳过，不评分、不发送。
- 7天内或恰好7天：继续本岗位评估；“继续”不等于立即发送。
- 面板明确显示没有同事沟通记录：继续。
- 面板没找到、未确认选中了同事页签、时间缺失/模糊/未来或面板没有位于顶部：未核验，不等同于无记录；不自动发送。页面异常仍按停机规则处理。

无时区的完整日期时间按北京时间UTC+08:00解释。只接受带年份且有时分的时间，不猜测“昨天”或缺少年份的日期。本规则优先于岗位文件中历史“近7天已沟通跳过/备选”及本地姓名去重说明；不用修改历史已确认岗位文件。

## 定向读取与判定

先以最新UIA定向核实并按需选择“同事沟通进度”页签；需要点击时，先检查gate，再按[点击方式开关](click-modes.md)执行：拟人轨迹开启用原鼠标流程，关闭用UIA InvokePattern，不移动鼠标。不得仅因截图上曾显示该页签就传已确认。随后运行只读提取器：

```powershell
pwsh -NoProfile -File scripts/read-coworker-progress.ps1 -WindowHandle <当前HWND> -CoworkerTabConfirmed |
  Set-Content -LiteralPath <当前候选人-coworker.json> -Encoding utf8
python scripts/coworker_progress.py --input <当前候选人-coworker.json>
```

提取器只在唯一可见的BOSS文档里定位“同事沟通进度”标题，限制最多6层小范围祖先、面板内最多120个文本节点；不提升为整页扫描。按控件纵向位置选第一条“向Ta发起沟通”，只取该条日期。默认文档URL模式是`*zhipin.com/web/chat/recommend*`；实测文档不同时使用本轮定向UIA实际返回的URL模式，不猜测URL、不导航或刷新补救。提取器只读、不点击、不滚动，不使用CUA、DOM或网页脚本。尚需在实际页面验证UIA暴露情况；定位失败返回unavailable，不能伪造空记录。

观测JSON契约只有三项：

```json
{"state":"first_record","first_greeting_at":"2026-06-05 09:22","evidence":"UIA：同事沟通进度首条，实际控件文本与时间"}
```

`state`为`first_record`、`empty`或`unavailable`。只有实际明确读到空记录才使用`empty`；`evidence`必须描述本次当前候选人的定向观察，不能照抄示例。

## 逐人留痕

电子简历打开并取得姓名后，先用稳定ID和进入点击时间运行`candidate-begin`并调用`electronic-opened`，使同事去重跳过者也计入查看人数。然后执行上述读取/判定。

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

平台稳定ID的发送账本、当前运行身份校验、发送结果unknown禁止重试等保护保持不变，不能借关闭姓名去重重复点击发送。
