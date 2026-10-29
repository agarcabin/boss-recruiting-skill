> 1.0.14日常执行以[连续运行](continuous-workflow.md)为准：冻结启动计划、主循环、重试复用本次访问、一次导出、表格缓存和美康快速分支。下文旧单步流程只作接口说明。

> 1.0.13新增功能及命令见[plan-features.md](plan-features.md)，包括同事前置、收藏、快速启动、今日表格统计和防息屏。

# 投递进度悬浮窗

`python.exe scripts/launch_progress.py --run <id> --output-root <目录>`，创建运行后仍须确认悬浮窗可见。

控制口径见 [control-policy.md](control-policy.md)。无自然截止和滚动额度，按本次target/max_views判断数量完成；查看预计基线使用当前max_views。暂停与结束仍可用，不要求绑定Codex停止按钮；有绑定时才尝试额外中断模型回合，无绑定如实显示not_bound。

结束由独立控制器处理：写停止状态、取消本轮登记helper、生成结束快照、关闭悬浮窗并显示Excel。报表或归档欠缺不阻止停止，也不伪造成功或完整证据。状态/按钮文字和计数失败应如实报告。
