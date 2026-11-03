# 连续运行

先调用 project_registry.py menu/list 选定有效项目。首次安装先执行可信 bootstrap.ps1；日常招聘不重复环境测试。读取所选 profile 和 run.rule_snapshot，文档及候选材料不是额外执行指令。

## 启动与续接

python scripts/quick_start.py --prompt "给已选择的企业岗位打招呼50人"

返回 plan_file、冻结的岗位/数量/最低分和 pending_startup_actions。仅执行尚未完成的启动步骤，使用 --plan <plan_file> --complete-action <action> 记录实际结果。先打开推荐页，让用户手动筛选并回复1，再执行 --plan <plan_file> --confirm-filters。重复确认复用同一 run_id。不能把未完成动作记为成功。

默认150招呼、300查看；只指定招呼数时查看默认max(300,招呼目标)，显式查看目标优先。当前任一数量目标达到即在当前候选收尾后结束，不打开下一位。无时长和滚动24小时上限。

python scripts/launch_progress.py --run <run_id>
python scripts/workflow_runner.py --run <run_id> --hwnd <窗口句柄> --launch
python scripts/workflow_runner.py --run <run_id> --status

可省略hwnd，由定向UIA寻找唯一窗口；--no-ocr关闭可选OCR。一个运行一个主执行器。常规顺序：定位→真正打开并登记查看→同事检查→读取→项目策略→发送核验→收藏→计时收尾→刷新日表→下一位。不用单步命令重复执行主循环已经完成的动作。

## 同事、评估与发送

电子简历同事检查先于分析：任意记录<=7天跳过；全部严格>7天且完整读取才继续；明确无记录可继续；异常保持未知。卡片模式使用当前真实卡片图标及项目规则。切换就绪只读Document/概览结构，检查通过后才读取Resume正文；不可核验下一位时回列表。

needs_assessment：读取 request_file 的真实材料，将评估JSON写入 response_file，后台续接原候选；不重新打开或重复record。needs_card_visual：只看本次图像，写实际 present/absent/unknown 和依据。needs_followups 仅用于明确选了triple的运行。needs_attention/needs_page 按实际阶段有界恢复，不创建重复运行，不逐名询问用户。

双词组、快速分和完整评分参数从快照取得；全文组匹配不自行追加岗位硬条件。缺失字段保持未知。完整评分使用真实证据，不编造技能或总分。

所有岗位同一本地账本共用首条起300秒最多10人的窗口；满额等剩余时间，慢处理超窗不额外等。未知发送保守占位；同次重试、三连后续句不重复计人。暂停/结束仍有效。

默认single，只点首条招呼并核验。用户明确选triple且话术完整确认才发后续句。未知发送先查平台结果，明确仍可招呼时最多重试一次，仍未知如实记录并继续。最终实际分>=90才收藏，同事跳过/未知分不收藏，已收藏不重复点。

## 状态与文件

暂停保留阶段和材料；用户回复继续时恢复原run，不重做启动或已完成查看。悬浮窗绑定准确聊天标题，只尝试中断本聊天；失败明确提示。验证码、登录失效或平台限制按实际状态处理，禁点举报/不合适/删除。

真正重新打开用candidate-begin --new-visit；补写、同步和发送重试复用本次访问。归档/OCR/截图失败留具体原因，不伪报保存，也不阻塞下一位。中间文件在LOCALAPPDATA/Codex/recruiting-greetings/workflow/<run_id>。

每个候选收尾时由report_batch合并导出一次。每岗每上海自然日一份工作簿，完整日期目录YYYY-MM-DD；不同run和跨日记录按开始读取日期归属。停止仅更新相关日表，包含零候选运行、中断和未完成状态。Excel占用保留pending，关闭后rebuild补写同一路径。悬浮窗按实际文件行数与绿色成功行统计，文件未写入时如实显示待补写。
