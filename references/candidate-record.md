# 评估记录和日报

1.5.4-beta 起，“运行记录/简历图片”分为“已招呼简历”“AI复盘捞回简历”“AI复盘过滤简历”“未招呼简历”，以已校验的AI结论及平台发送状态分类。原图、标色图和说明一起移动，账本与Excel同步更新链接；细则见 [resume-capture-ocr.md](resume-capture-ocr.md)。同事重复在截图前跳过，不单设图片目录。

record共用字段：candidate_id、candidate_name、started_at（含时区）、electronic_resume_enabled、overall_score、hard_requirements、decision(greet/skip/review)、pros、cons。结束时间由真实离开动作的finalize-timing补入，不估计。card另含card和card_evidence；resume另含electronic、coworker_progress，resume_evidence仅在实际保存后提供。

词表、分数和资格通过同一 recruiting_rules.evaluate 在record及reserve核对；新建项目的规则保存在project.json.rules。默认条件不得套用其他项目。direct_rule按项目快照记录真实命中词和快速分；完整评分未知不编造，薪资/在职和年限字段按实际已读信息填写，扣分交统一代码计算，不能预扣两次。

主执行器正常运行不重复调用单步record/reserve。可见候选简报含时间、姓名、综合分、判定、时长、优点、劣势及本地证据链接；命中证据显示“命中词”，原始结构在隐藏页保留。单词库岗位只显示“词库：命中词”，多词库岗位才显示“A组：…；B组：…”。外部文本强制写为字符串。日表唯一目标持久登记，改output-root仍使用原文件；不生成最终副本。

写表失败保留账本和pending，不阻止下一人；运行结果页保留每个run、中断和未评估候选，不能伪造评估。手工补写使用candidate_log.py rebuild --help。历史旧表仅在核验记录完整覆盖后本地归档；无法确认的保留并报告。


## 2026-11-17 日报目录与静态 Excel

日期目录外层只保留岗位最终 Excel。简历图片、简历OCR、记录快照等过程资料统一保存在同日“运行记录”下。取消 CSV/Excel查询刷新及新建 .data 目录，不修改旧运行的规则快照；旧 csv_reports 标记不再触发 CSV 导出。运行中打开报告复用同岗同日唯一的“运行记录/记录快照/<主表名称>-快照.xlsx”；写入失败保留旧快照，不另建随机副本。结束时生成外层独立最终 Excel，验证所有者和记录覆盖后清理本岗位临时快照与旧 .data，最终报告路径指向外层 Excel。生成或核验失败不删除快照；文件占用等清理失败保留待补状态，不阻止结束。迁移现有资料前备份并同步修复账本和表格中的简历路径。
