> 1.0.14日常执行以[连续运行](continuous-workflow.md)为准：冻结启动计划、主循环、重试复用本次访问、一次导出、表格缓存和美康快速分支。下文旧单步流程只作接口说明。

> 1.0.13新增功能及命令见[plan-features.md](plan-features.md)，包括同事前置、收藏、快速启动、今日表格统计和防息屏。

# 候选人评估与简报

以 [evaluation-modes.md](evaluation-modes.md) 为现行唯一口径，机器词表见recruiting-rules.json。

record输入只含评估摘要与本地证据路径，不复制简历全文。共用字段：candidate_id、candidate_name、started_at（含时区）、electronic_resume_enabled、overall_score、hard_requirements、decision(greet/skip/review)、pros、cons。不得填ended_at；实际处理完后finalize-timing。

card模式另含card:{advantage,expectation,already_contacted}及card_evidence:{image,uia_json}；JSON观察中的姓名与字段必须一致，包含真实URL、时间和矩形。electronic_resume_enabled:false，不填electronic或resume_evidence。评分自动计算为优势60+期望40，不作门槛，record立即归档卡片图/UIA JSON。

resume模式包含electronic:{score,evidence}、真实coworker_progress；resume_evidence:{image,ocr_text,ocr_json}可选，按实际读取内容评分。AGV增加requirement_states，值met/unknown/failed。advanced分别记录brand_work（四品牌任一工作经历，不限AGV）和agv（任何AGV经历），可以来自不同经历；另记录independent/vendor/team/travel/certificate/left_job，离职不加分。basic记录agv/vendor/certificate/left_job，其中agv和vendor为“或”，两项都failed才拦截，任一项正向经历有效命中即可触发。所有缺项保留unknown，未知0分；不再使用generic_agv_experience额外加分。record优先从可读OCR原文、否则从真实keyword_text核实关键词并按规则重算AGV分数；缺项允许与明确不符分开记录，不使用hard_override掩盖failed。美康新通道直接触发，年限仅减分，其他正常通道按当前岗位；2026-10-28英语证据放宽时，在electronic.evidence记录相关海外销售经历依据与“英语能力由经历推定、未直接陈述”，不因未单列英语能力将hard_requirements设为false；其他底线仍独立核验，明确英语不能用于工作不得覆盖。

record和reserve共用资格函数。decision=greet只有资格允许才写入；关键词命中低于min_score可以通过。保存触发keyword/score/both、命中词/原句、逐项底线、规则快照及实际消息状态（single仅首句，triple三句，见[greeting-modes.md](greeting-modes.md)）。所有已评估者留痕，包括skip/review。

Excel位于桌面/自动投递记录/<月日>/<企业>-<岗位>-投递记录.xlsx；简报可见列为录入时间、候选人、综合分、判定、判断时长、优点、劣势、证据链接；“触发方式”和“招呼结果”字段保留在工作簿中但默认隐藏。card链接查看名片，resume链接查看简历。隐藏详细信息及评估证据保存可追溯字段，首句成功与后续句状态分别呈现。停止时额外生成独立结束快照及运行结果页，不伪造未完成评估或点击时间。

简历模式复杂职业轨迹才按subagent-evaluation.md隔离分析；子agent不得控制BOSS或发送、记账。普工不做OCR评估委派。具体命令见run-commands.md。

记录、归档、报表写入与计时不再作为继续门槛。record自动补登记；重复候选人保留独立访问记录。写表失败保留report_written=0和警告，后续rebuild补写，不阻止发送。详见[运行控制策略](control-policy.md)。
