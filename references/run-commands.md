# 命令入口

正常运行：project_registry.py menu/list → quick_start.py --prompt →完成启动步骤→用户筛选并回复1→quick_start.py --plan <plan> --confirm-filters → launch_progress.py --run <run> → workflow_runner.py --run <run> --launch。

workflow_runner.py --status读取检查点；运行内暂停/继续/结束由统一控制器处理。调试单步命令及参数使用ledger.py、candidate_log.py、boss_safe_actions.py、stop_controller.py的--help，不能把调试入口作为绕过同事/规则/限速的途径。

记录、发送、核验、收藏、计时与导出由主执行器续接，不因聊天重试而重复打开或发消息。停止前先持久请求停止，再补写相关唯一日表；--output-root不能另造已登记的同岗日表。
