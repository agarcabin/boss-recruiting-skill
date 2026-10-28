# 现行模式与新增命令

优先遵循 [evaluation-modes.md](evaluation-modes.md)。新策略start必须带--stop-binding <本聊天绑定.json>；默认150人/300查看/240分钟/滚动24小时150人。以下旧命令示例适用于其各自证据模式，不得用于要求普工打开或归档电子简历。

```text
powershell -NoProfile -File scripts/capture-card.ps1 -WindowHandle <hwnd> -CandidateName <姓名> -OutputDirectory <证据目录>
python scripts/safe_action.py --run <id> --generation <gate值> --target <定向UIA目标.json> --token <首句或后续句token> --action invoke
python scripts/run_safety.py message-begin --run <id> --candidate-id <id> --message-index 2
python scripts/run_safety.py message-resolve --token <token> --result sent
python scripts/run_safety.py message-reconcile --token <token> --result not-sent --manual-confirmed
python scripts/stop_controller.py --run <id> --stop
```

# 账本与简报命令

从 Skill 根目录运行。优先把示例中的 `python` 换成 `runtime/win-x64/python/python.exe`；悬浮窗使用同目录的 `pythonw.exe`。本次运行的 `--min-score` 以用户确认值为准。对同一运行，`candidate_log.py --output-root` 保持一致。

## 开始与评估

所有PowerShell脚本优先用`pwsh`执行。找不到窗口句柄时使用`resolve-recruiting-window.ps1 -ChatTitle <实测聊天标题>`只读发现，再完成停止绑定。简历采集与OCR使用`capture_resume.py --run <id> --candidate-id <键> --hwnd <实测句柄> --output-dir <新目录>`，详见[长截图与RapidOCR](resume-capture-ocr.md)。不要复用此前聊天的临时编排脚本或硬编码运行号、句柄和候选人顺序。

```text
python scripts/ledger.py start --profile <已确认岗位文件> --target 5 --duration-min 60 --min-score <本次门槛>
pythonw.exe scripts/progress_window.py --run <run_id>
python scripts/ledger.py gate --run <run_id>
python scripts/ledger.py candidate-begin --run <run_id> --candidate-id <平台标识> --started-at <进入点击.clickStartedAt>
python scripts/ledger.py electronic-opened --run <run_id> --candidate-id <平台标识>
python scripts/candidate_log.py record --run <run_id> --input <候选人评估.json>
```

本地Excel/历史姓名去重默认关闭；普通运行不执行姓名查重。只有用户明确开启时使用`lookup-name --name <姓名> --enable-local-excel-dedup`，默认调用只返回disabled且不打开数据库。电子简历打开后、评分前按[同事去重](coworker-dedup.md)用定向UIA取得当前“同事沟通进度”的首条，生成小型观测JSON，再运行：

```text
python scripts/coworker_progress.py --input <当前候选人-coworker.json>
```

早于7天返回skip，恰好7天/7天内或明确无记录返回continue；未读到、时间不完整等返回review，不冒充无记录。skip用下列命令记入当前企业岗位报表，不做OCR/评分：

```text
python scripts/candidate_log.py coworker-skip --run <run_id> --candidate-id <稳定标识> --candidate-name <当前姓名> --input <coworker.json>
python scripts/ledger.py note --run <run_id> --candidate-id <稳定标识> --result skipped
python scripts/candidate_log.py sync --run <run_id> --candidate-id <稳定标识>
```

之后照常离开、finalize-timing、candidate-finish。continue时将同一个观测对象放入评估JSON的coworker_progress再record，发送前reserve会重新校验该时间。具体UIA读取及JSON契约见同事去重引用。

`electronic-opened` 仅在电子简历确实打开后调用。评估 JSON 不填 `ended_at`；`record` 先写入评分和简历证据，判断时长暂显示“待完成”。推荐列表不能替代电子简历评分。

## 判定与发送

`skip` 或 `review`：运行 `ledger.py note --run <run_id> --candidate-id <平台标识> --result skipped/review`，然后运行 `candidate_log.py sync --run <run_id> --candidate-id <平台标识>`。

符合本次分数门槛、岗位硬条件和去重条件时：

```text
python scripts/ledger.py reserve --run <run_id> --candidate-id <平台标识>
python scripts/ledger.py gate --run <run_id>
<取得 ready 后，核对当前可见目标，执行一次发送点击并核验结果>
python scripts/ledger.py resolve --token <token> --result sent
python scripts/candidate_log.py sync --run <run_id> --candidate-id <平台标识>
```

`reserve` 返回 `ready` 后、实际发送点击前必须再次检查 `gate`。所有点击按[点击方式开关](click-modes.md)执行：默认 `use_mouse_trajectory=false`（含未指定），通过 `safe_action.py --action invoke` 使用 UIA `InvokePattern.Invoke()`，不运行鼠标移动；仅在用户明确开启 `true` 时才通过 `--action mouse` 使用 `move-click.ps1`。记录相同的 `clickStartedAt` / `clickEndedAt` 并核验结果。实际发送和多段话术顺序按 [投递运行流程](run-workflow.md)；结果不明记 `unknown` 并停止，不重复点击。`resolve` 的结果须与页面核验一致。

发送成功后，简历证据若尚未归档，使用 `candidate_log.py archive-resume --run <run_id> --candidate-id <平台标识> --image <resume-long.png> --ocr-text <resume.ocr.txt> --ocr-json <resume.ocr.json>`。打印电子简历 PDF 后使用 `candidate_log.py archive --run <run_id> --candidate-id <平台标识> --pdf <打印文件.pdf>`。仅在确实无法取得时分别使用 `missing-resume --reason <具体原因>` 或 `missing-pdf --reason <具体原因>`；不能伪造文件。

## 离开与补时

发送、同步和必要归档完成后，点击切换下一人或离开末位详情。将这次点击的同一个结束时间依次交给：

```text
python scripts/candidate_log.py finalize-timing --run <run_id> --candidate-id <平台标识> --ended-at <离开点击.clickEndedAt>
python scripts/ledger.py candidate-finish --run <run_id> --candidate-id <平台标识> --ended-at <离开点击.clickEndedAt>
```

下一人的 `candidate-begin --started-at` 使用同一次切换的 `clickStartedAt`。没有离开点击时保留“待完成”，不编造时间。`finalize-timing` 对同一时间可安全重复调用，不同时间会拒绝覆盖。

## 恢复与修复

掉线后运行 `ledger.py control --run <run_id> --action login-required --reason session_expired`；若伴随风控提示，原因用 `risk_logout`。用户亲自登录后，核对账号、企业、岗位、城市、筛选、当前候选人和平台结果；先处理 `ledger.py unresolved`，再运行 `ledger.py control --run <run_id> --action login-confirmed --manual-confirmed`。普通 `resume` 不能跳过登录等待，超时或限制仍在时不恢复发送。

`reserve` 返回 `report_not_synced`、`report_not_written`、`resume_archive_pending` 或 `pdf_archive_pending` 时，先修复简报与归档。工作簿写入中断可在关闭 Excel 后运行 `candidate_log.py rebuild`；重建指定日期使用 `rebuild --day YYYY-MM-DD`。原文件在 Excel 中占用时可用 `rebuild --day YYYY-MM-DD --output-file <新文件名.xlsx>` 生成带企业和岗位前缀的同目录副本，关闭原工作簿后再重建原文件。rebuild按日期及企业/岗位分别重建，不把多个岗位合并到一张表；返回reports列表和首个report以兼容旧调用。重建与同步都会保留“触发方式”和“招呼结果”的单元格值，但将简报中的两列设为隐藏。直接关闭进度窗口不改变运行状态；点击“结束”并确认后写入 `stopped`。
