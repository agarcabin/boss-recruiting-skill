# 评估模式与触发规则（2026-10-29）

岗位评估口径；运行控制以 [control-policy.md](control-policy.md) 为准。词表及AGV权重的机器配置为 [recruiting-rules.json](recruiting-rules.json)，record和reserve共同使用 scripts/recruiting_rules.py。

## 项目与底线

岗位front matter指定 evaluation_mode: card/resume 与 trigger_policy: worker/meikang/agv_advanced/agv_basic。无配置的历史项目采用legacy原评分口径。项目元数据与每轮快照保存candidate_namespace，改显示名不重算身份。

- worker：8个普通岗位，包括铆工，统一列表规则；不保留旧学历、工龄、图纸、技能、地点、班次或最低分拦截。优势或期望任一正向命中即招呼。优势60、期望40，同组不重复，仅作记录。
- meikang：version4起新增28家公司本人任职＋海外/出口/销售/业务直接通道，或生化/化学发光/质谱出口经历＋海外词直接通道；同事检查始终在分析前。命中新通道不被旧硬条件或分数二次否决。年限仅按配置扣分，不作排除；未命中则保留原行业/业务或评分通道，经验之外的硬条件按当前岗位。细节见[plan-features.md](plan-features.md)。
- agv_advanced（海康、华睿）：四品牌任一工作经历（brand_work）与任何AGV经历（agv）分别判断，可以来自不同经历，不要求品牌工作属于AGV；另要求独立实施、乙方实施、带队现场实施、常年出差。任一要求明确不符拦截，未知允许；AGV60、独立10、乙方10、带队10、出差5、任何证书5，满分100，未知0分，品牌工作不另计分，离职不加分。删除旧generic_agv_experience额外20分。
- agv_basic（凯乐士、极智嘉）：AGV经历或乙方实施经历，任一项有效命中即可招呼，只有乙方实施经历也可以；两项都明确不符才拦截，未知允许。一项failed不阻止另一项有效命中，也不能凭failed项的关键词触发。AGV65、乙方25、任何证书5、明确离职5，满分100，未知0分；乙方关键词须有本人正向实施/部署/调试/交付语境。
- AGV的requirement_states逐项使用met/unknown/failed，不能伪造已满足；证书不按数量累加。规则配置version=3适用于新运行，既有version=2快照沿用旧判断与旧权重，不改写历史运行。
- 双通道默认70分且同时生效；关键词通道不受最低分拦截，保留实际低分，不改成70绕门禁。关键词仅本人正向经历/意向，否定及广告引用不命中；AGV需经验语境，品牌裸词、证书、离职不单独触发。record读取本地OCR原文核实，reserve重用同一判断函数。

## 普工证据与流程

1. 按本轮数量目标，定向UIA定位当前可见card-item；用capture-card.ps1保存card.png和card.uia.json（姓名、完整Name、优势、期望、列表沟通状态、URL、矩形、时间）。截图遮挡或身份不明不发送。同事图标有则先跳过；查明无图标再解析筛选字段。普通字段缺失记未知，不强制暂停；普通列表筛选不要求打开电子简历。
2. candidate-begin在实际读取卡片时登记；未命中skip，无法读字段review；关键词命中greet。列表明确已沟通则按平台状态处理；不因账本历史命中跳过；不检查详情同事记录。
3. 评估JSON包含card与card_evidence:{image,uia_json}、electronic_resume_enabled:false、实际started_at。record计算分数与触发原因、复制证据至当天名片图片目录并写Excel；原resume/PDF状态均not_applicable，而非missing。
4. 按 [招呼方式开关](greeting-modes.md)执行：默认single只点列表“打招呼”，核验后直接下一卡片，不点继续沟通；只有triple才保留列表默认招呼、既有第二句介绍、第三句索简历并打开聊天小窗。称谓从卡片明确姓名/称谓读取，无证据用您好；普通筛选不打开电子简历；备选或成功招呼者可为收藏打开后返回列表。
5. 本轮候选人处理完成后，用真实读取/完成时间finalize-timing并candidate-finish；timing_source=card_read，不编造详情切换点击。候选标识保留用于记录；各次访问使用独立键，不作历史去重。

## 简历模式

美康与AGV先做同事去重，再按真实简历内容判断；本地长截图、RapidOCR和章节检查可选；保留美康pdf_required:false。其他简历模式按原PDF归档制度。只有简历模式可以委派复杂OCR文本评估；不得将普工卡片变成简历OCR流程。

## 发送、计数与停止

默认single，仅用户明确选择才triple。通过safe_action使用当前UIA目标；不再要求每次gate/reserve、generation或候选人祖先核验。可直接调用safe_action，记账引用自动生成且不作为动作授权凭据。

默认150招呼、300查看，可用--target及--max-views指定任意正整数。没有运行时间、滚动24小时额度或发送间隔限制。数量达到后结束，不自动超出本次目标。

未审核/冲突仅提醒；未写报表、未同步、未归档、未登记或未完成计时不阻塞后续。长截图、OCR及完整性检查为可选工具，使用实际读取的内容评估，未读信息记未知。

unknown如实记录，可自动重新查询并在明确可招呼时重试一次；无人工核销前置条件，也不跨运行阻塞。删除候选人历史去重，保留独立访问和发送记录。

悬浮窗必须显示，停止按钮绑定可选。手动结束时控制器写停止状态、取消本轮helper并生成报表；无绑定时不承诺中断Codex模型回合。采集helper仍可被控制器取消，不再检查截止时间。

1.0.14/version5：美康先做直接通道，未提供完整分时记录基础80的快速规则分并按实际年限扣分，资格不受该分数限制；未命中才完整评估。执行流程见continuous-workflow.md。
