# 评估模式与触发规则（2026-10-27）

当前唯一可执行口径；历史岗位规则不能覆盖本文件。词表及AGV权重的机器配置为 [recruiting-rules.json](recruiting-rules.json)，record和reserve共同使用 scripts/recruiting_rules.py。

## 项目与底线

岗位front matter指定 evaluation_mode: card/resume 与 trigger_policy: worker/meikang/agv_advanced/agv_basic。无配置的历史项目采用legacy原评分口径。项目元数据与每轮快照保存candidate_namespace，改显示名不重算身份。

- worker：8个普通岗位，包括铆工，统一列表规则；不保留旧学历、工龄、图纸、技能、地点、班次或最低分拦截。优势或期望任一正向命中即招呼。优势60、期望40，同组不重复，仅作记录。
- meikang：按当前已审核岗位底线和缺项口径执行。2026-10-28用户批准：本人明确的医药/IVD/医疗器械/耗材海外销售实战经历可作为沟通能力初筛依据，未写英语商务能力不单独拦截或扣分；记录为经历推定，不虚写直接语言证明，明确英语不能工作仍拦截。其他年限、渠道、学历和地点条件独立判断。底线允许且（行业组和业务组各命中1词，或综合分>=本轮min_score）即招呼。
- agv_advanced（海康、华睿）：四品牌任一工作经历（brand_work）与任何AGV经历（agv）分别判断，可以来自不同经历，不要求品牌工作属于AGV；另要求独立实施、乙方实施、带队现场实施、常年出差。任一要求明确不符拦截，未知允许；AGV60、独立10、乙方10、带队10、出差5、任何证书5，满分100，未知0分，品牌工作不另计分，离职不加分。删除旧generic_agv_experience额外20分。
- agv_basic（凯乐士、极智嘉）：AGV经历或乙方实施经历，任一项有效命中即可招呼，只有乙方实施经历也可以；两项都明确不符才拦截，未知允许。一项failed不阻止另一项有效命中，也不能凭failed项的关键词触发。AGV65、乙方25、任何证书5、明确离职5，满分100，未知0分；乙方关键词须有本人正向实施/部署/调试/交付语境。
- AGV的requirement_states逐项使用met/unknown/failed，不能伪造已满足；证书不按数量累加。规则配置version=3适用于新运行，既有version=2快照沿用旧判断与旧权重，不改写历史运行。
- 双通道默认70分且同时生效；关键词通道不受最低分拦截，保留实际低分，不改成70绕门禁。关键词仅本人正向经历/意向，否定及广告引用不命中；AGV需经验语境，品牌裸词、证书、离职不单独触发。record读取本地OCR原文核实，reserve重用同一判断函数。

## 普工证据与流程

1. gate确认may_start_candidate后，定向UIA定位当前可见card-item；用capture-card.ps1保存card.png和card.uia.json（姓名、完整Name、优势、期望、列表沟通状态、URL、矩形、时间）。截图遮挡或身份不明不发送。字段缺失不猜测，不OCR补读，不打开电子简历。
2. candidate-begin在实际读取卡片时登记；未命中skip，无法读字段review；关键词命中greet。列表明确已沟通或账本命中则跳过；不检查详情同事记录。
3. 评估JSON包含card与card_evidence:{image,uia_json}、electronic_resume_enabled:false、实际started_at。record计算分数与触发原因、复制证据至当天名片图片目录并写Excel；原resume/PDF状态均not_applicable，而非missing。
4. 保留三句：列表默认招呼、既有第二句介绍、第三句索简历。称谓从卡片明确姓名/称谓读取，无证据用您好。只开聊天小窗，不开电子简历。
5. 本轮候选人处理完成后，用真实读取/完成时间finalize-timing并candidate-finish；timing_source=card_read，不编造详情切换点击。两种模式均按账本去重；稳定ID优先，无ID使用姓名+规范化静态卡片摘要的项目内临时键，不含按钮状态、在线时间等易变项；碰撞不发。

## 简历模式

美康与AGV继续本地长截图+RapidOCR、章节检查、同事去重；保留美康pdf_required:false。其他简历模式按原PDF归档制度。只有简历模式可以委派复杂OCR文本评估；不得将普工卡片变成简历OCR流程。

## 安全发送与三句状态

所有点击、UIA Invoke和键盘发送都通过safe_action.py，禁止先gate再另起裸UI动作。safe_action与stop共用跨进程互斥锁，并在实际Invoke、鼠标落键、Enter前核对deadline及generation。--target JSON必须来自本次定向UIA，含hwnd、runtime_id、name、candidate_name、candidate_id、document_url；鼠标模式另提供已核验坐标。

首句reserve取得token后，safe_action --token派发，定向核验平台结果再resolve；dispatched不是发送成功。第二、三句使用run_safety.py message-begin --message-index 2/3取得独立token，发送后message-resolve。结果不明用unknown，绝不重发。首句sent后后续unknown不覆盖首句成功人数；所有未决句子跨运行阻塞，message-reconcile必须人工核实并--manual-confirmed，不自动释放额度。

## 计数与停止

普通运行默认target150、duration-min240、最多300位唯一已评估候选人，滚动24小时最多150位首句成功。暂停不延长自然截止。gate返回generation、may_start_candidate和drain_reason；数量触顶只完成当前人，不进入下一人，后两句不额外占人数。手动或时间截止立即禁止后续发送。

start新策略必须提供--stop-binding，本轮绑定经stop_controller.probe_binding核验才运行；不得借用另一窗口/聊天的停止按钮。UIA绑定含hwnd、process_id、process_started_at、应用document_runtime_id、chat_title、scope_runtime_id、stop_name；每次必须核验应用文档标题及常驻“聊天工具栏”的同名标题，只在该应用文档中定位唯一可见对话Scope，不能依赖会被虚拟化移除的早期消息；正式app_server绑定含本机ws URL、thread_id、turn_id，不能假定现有桌面会话可连接。无法可靠绑定时停止启动，不退回旧“只写账本”的结束方式。

进度悬浮窗独立于主agent：手动结束无二次确认；每秒检查截止及数量完成。控制器原子停机、推进generation、中断绑定回合、最多5秒取消/收集登记helper回执、未决标unknown，冻结一致性快照后关闭悬浮窗并打开Excel；迟到回写被拒绝。零候选也生成运行结果，锁定文件使用独立终止快照。中断失败必须在报表明确列出，不能声称思考已停。

## 可取消的采集与OCR

长截图、OCR及等待helper通过managed_helper.py --db <db> --run <id> --generation <gate值> -- <可执行文件> <本包脚本> ...启动。该入口登记PID及创建时间并独立检查停止/截止，不接受任意UI脚本。resume_capture.ps1本轮必须传-Run、-LedgerDb、-Generation（PowerShell保留别名Db给Debug，不可使用-Db），每次ScrollPattern前共用互斥锁重查门禁；其拼图子进程也自动登记。停止控制器只取消本轮登记且创建时间一致的helper。

启动绑定示例：pwsh -File scripts/bind-codex-stop.ps1 -WindowHandle <本窗口hwnd> -ChatMarker <已读到的本聊天常驻标题> -Output <本地binding.json>。返回ready后再传给start；不猜测窗口句柄、聊天标识或runtime_id。绑定每轮重新核验，不复用旧会话。

悬浮窗用launch_progress.py启动，独立于会被取消的agent工具进程job；无法独立启动则不进行候选人操作。控制器自身不登记为可取消的OCR/helper。
