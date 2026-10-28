# 投递运行流程

现行判定、证据、三句与终止的完整契约见 [评估模式](evaluation-modes.md)。本文件仅保留入口和异常共用约束。

1. 先选择企业再选岗位；AGV岗位顺序海康、华睿、凯乐士、极智嘉。pending不创建运行；approved仍检查完整审核条件。
2. 先取得本聊天可靠stop binding；普通运行start --target 150 --duration-min 240 --min-score 70 --stop-binding <json>。测试项目才按standard-test.md进行5人试投。只读测试不代表发送授权。
3. 打开BOSS仅用明确非CUA入口或人工打开。人工调整并检查推荐页后回复1即本轮发送授权，不再逐人确认。
4. 创建运行立即启动python.exe scripts/launch_progress.py --run <id>；确认可见后才开始候选人操作。默认use_mouse_trajectory=false，页面点击统一经safe_action.py --action invoke调用UIA；仅用户明确开启true才走鼠标模式，详见click-modes.md。门禁及定向UIA按evaluation-modes.md，不裸调用Invoke/Enter/move-click。
5. card项目从列表逐张读取并截图；resume项目打开电子简历、同事检查后，用 `capture_resume.py` 串行完成长截图与OCR再评估。record -> reserve/skip-note -> 三句核验 -> sync -> 本模式适用的证据归档 -> finalize-timing -> candidate-finish。阶段必须顺序执行并检查退出码及JSON状态；`blocked`即使退出码0也停止依赖步骤，不能用PowerShell分号无条件串联。截图/OCR失败不启动后续步骤，准备失败不采集。
6. 数量达到150招呼或300查看后只收完当前人；手动或自然4小时到期立即停止新动作。由独立控制器中断回合、关闭悬浮窗、打开最终Excel。

保持60秒最小首句间隔，通常随机80–100秒；不得为数量跳过证据、门禁或发送核验。名称/性别不推断；不能编造薪资、待遇、公司主体。页面刷新、验证码、风控、退出登录、Document消失等旧异常仍立即停止，不自动重试或重载。pending/unknown先人工核实，不重发。

候选人candidate_seen正常记录重复跳过并继续，不因该项暂停全轮。本地Excel历史同名查重默认关闭，稳定身份账本去重保留。简历模式同事去重仍按coworker-dedup.md；卡片模式明确不适用。

悬浮窗用launch_progress.py启动，独立于会被取消的agent工具进程job；无法独立启动则不进行候选人操作。控制器自身不登记为可取消的OCR/helper。
