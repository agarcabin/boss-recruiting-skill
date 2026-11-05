# 命令入口

正常运行：通用启动或菜单1→project_registry.py menu（六项主菜单）；菜单2或主菜单第2项→project_registry.py list（企业→岗位）。明确岗位的招呼指令→quick_start.py --prompt→完成启动步骤并核对BOSS岗位→quick_start.py --plan <plan> --start-direct→launch_progress.py --run <run>→workflow_runner.py --run <run> --launch。仅给人数先选岗位；旧await_filters计划兼容--confirm-filters。

workflow_runner.py --status读取检查点；运行内暂停/继续/结束由统一控制器处理。调试单步命令及参数使用ledger.py、candidate_log.py、boss_safe_actions.py、stop_controller.py的--help，不能把调试入口作为绕过同事/规则/限速的途径。

记录、发送、核验、收藏、计时与导出由主执行器续接，不因聊天重试而重复打开或发消息。停止前先持久请求停止，再补写相关唯一日表；--output-root不能另造已登记的同岗日表。


当前1.4.0补充规则以 [v1.4.0执行口径](v1.4.0-policy.md) 为准。
