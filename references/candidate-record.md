# 评估记录和日报

record共用字段：candidate_id、candidate_name、started_at（含时区）、electronic_resume_enabled、overall_score、hard_requirements、decision(greet/skip/review)、pros、cons。结束时间由真实离开动作的finalize-timing补入，不估计。card另含card和card_evidence；resume另含electronic、coworker_progress，resume_evidence仅在实际保存后提供。

词表、分数和资格通过同一 recruiting_rules.evaluate 在record及reserve核对；新建项目的规则保存在project.json.rules。默认条件不得套用其他项目。direct_rule按项目快照记录真实命中词和快速分；完整评分未知不编造，薪资/在职和年限字段按实际已读信息填写，扣分交统一代码计算，不能预扣两次。

主执行器正常运行不重复调用单步record/reserve。可见候选简报含时间、姓名、综合分、判定、时长、优点、劣势及本地证据链接；命中证据显示“命中词”，原始结构在隐藏页保留。外部文本强制写为字符串。日表唯一目标持久登记，改output-root仍使用原文件；不生成最终副本。

写表失败保留账本和pending，不阻止下一人；运行结果页保留每个run、中断和未评估候选，不能伪造评估。手工补写使用candidate_log.py rebuild --help。历史旧表仅在核验记录完整覆盖后本地归档；无法确认的保留并报告。
