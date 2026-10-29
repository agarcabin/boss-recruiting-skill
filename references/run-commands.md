> 1.0.14日常执行以[连续运行](continuous-workflow.md)为准：冻结启动计划、主循环、重试复用本次访问、一次导出、表格缓存和美康快速分支。下文旧单步流程只作接口说明。

> 1.0.13新增功能及命令见[plan-features.md](plan-features.md)，包括同事前置、收藏、快速启动、今日表格统计和防息屏。

# 运行命令（1.0.12）

优先包内runtime/win-x64/python/python.exe。控制策略见 [control-policy.md](control-policy.md)。

```text
python scripts/ledger.py start --profile <岗位.md>
python scripts/ledger.py start --profile <岗位.md> --target 500 --max-views 1200 --min-score 70
python scripts/launch_progress.py --run <id>
python scripts/ledger.py status --run <id>
python scripts/ledger.py gate --run <id>
python scripts/ledger.py candidate-begin --run <id> --candidate-id <原始候选标识>
python scripts/ledger.py electronic-opened --run <id> --candidate-id <原始候选标识>
python scripts/candidate_log.py record --run <id> --input <评估.json>
python scripts/safe_action.py --run <id> --target <本次UIA目标.json> --action invoke
python scripts/ledger.py resolve --token <动作返回的记账引用> --result sent
python scripts/candidate_log.py sync --run <id> --candidate-id <原始候选标识>
python scripts/ledger.py candidate-finish --run <id> --candidate-id <原始候选标识>
python scripts/ledger.py control --run <id> --action pause
python scripts/ledger.py control --run <id> --action resume
python scripts/stop_controller.py --run <id> --stop
```

默认150招呼/300查看；只指定招呼数时，查看默认max(300,招呼目标)，明确查看数优先。--duration-min兼容接收但忽略；旧deadline、滚动额度及next_allowed_at不执行。--stop-binding可选，不强制探测；--generation及动作--token可省略。保留reserve命令供已有调用记账，不要求先reserve再发送。

候选登记可由record自动补齐。未完成旧候选人的计时/归档不阻止新候选人；重复遇到的同一候选标识产生独立访问，不做历史去重。unknown记录不阻塞运行，reconcile/message-reconcile不要求manual-confirmed。

电子简历打开先按 [同事去重](coworker-dedup.md) 读取观察，再分析真实简历内容。resume_evidence可省略，keyword_text须来自真实读取；长截图/OCR可选，不能把未读内容写成已确认。报表/归档失败记警告，后续可用candidate_log.py rebuild补写。

可选采集：`capture_resume.py --run <id> --candidate-id <id> --hwnd <hwnd> --output-dir <全新目录>`。采集工具的失败不意味着整轮必须停止，可改用已实际读到的内容判断。账号登录/验证码仍由用户处理。
