> 1.0.14日常执行以[连续运行](continuous-workflow.md)为准：冻结启动计划、主循环、重试复用本次访问、一次导出、表格缓存和美康快速分支。下文旧单步流程只作接口说明。

# 2026-10-29更新功能（1.0.13）

本版实施更新计划剩余功能；1.0.12删除的限制继续删除。数量150/300仅默认，长截图/OCR仍可选，不恢复状态、候选归属或token等逐动作守卫。

## 同事检查在先

普工capture-card.ps1在当前卡片子树先查同事已招呼图标/可访问标记，再读筛选字段，观察写到card.coworker_contact。present直接跳过，不解析优势/期望；absent且查询完整才评估；unknown记待处理，不冒充无图标。

如果图标名称不暴露、只剩不透明icon或局部查询不完整，使用本地view_image查看刚保存的card.png，先判断同事标记；通过card_observation.py --input <card.uia.json> --image <card.png> --visual-state present/absent --evidence <实际视觉依据> --output <已核验观察.json>保存视觉结论。只有确认无标记后才从已采集raw_text解析优势/期望；不OCR、不打开详情、不因该技术分支要求用户逐人确认。

电子简历打开后立即登记本次访问，UIA读取右下角同事进度，执行：

```text
python scripts/candidate_checks.py --run <id> --candidate-id <实际标识> --input <本次同事观察.json>
```

结果保存到本次访问。skip使用candidate_log.py coworker-skip写表、不分析；unavailable/unknown记“同事检查待处理”，分数留空，不自动归为岗位备选。允许继续后才读取和分析正文；选用capture_resume.py时，该入口先确认同事检查通过。record也在关键词/评分前检查，不能复用另一访问的结果。

## 美康

recruiting-rules.json version4保存28家公司、业务词、产品/海外词及年限扣分配置。meikang_rules.py核验本人工作段/结构化work_experience。行业资料、客户名单、否定词不作为本人任职；公司与业务词可位于不同本人工作条目。

A：指定公司任职＋海外/出口/销售/业务；B：生化/化学发光/质谱产品出口＋海外词。命中新通道直接触发，其他旧岗位硬条件不二次否决，但同事检查在先。未命中则保留原正常通道。

年限不再是硬条件：3年及以上不扣，2年至不足3年扣5，不足2年扣10；未知不编造。提供related_experience_years和score_before_experience，重算不重复扣分；两年或更少不因年限单独排除。

评估JSON可包含真实work_experience:[{company,position,duties,description}]；没有结构化记录则从实际keyword_text/OCR的工作段识别。不得自行补造工作经历。

## 收藏

备选或首句已核验成功者，在切换下一位前执行：

```text
python scripts/ui_features.py favorite --run <id> --candidate-id <实际标识> --hwnd <当前窗口>
```

先读右侧收藏状态：saved不点；unsaved点一次并核验；不可读或结果不明记pending，不反复切换开关。unknown发送、未发送符合者、同事去重或同事检查待处理不自动收藏。

普工只在列表筛选结束、确认为备选或已招呼后，为收藏打开电子简历；不新增查看行、不重评简历，不调用electronic-opened增加查看。收藏后返回列表再继续。不要把这类为收藏打开简历当作启用简历评估。

favorite_results保留结果和证据。收藏失败不改写招呼成功状态，也不阻止后续；数量达到后的当前候选人收尾包括收藏。

收藏结果同时进入工作簿隐藏“评估证据”的“收藏状态”列，后续写表或结束快照会刷新该状态。

## 快速启动与当前聊天

用户直接说“帮我打招呼，打美康50人”时先调用quick_start.py --prompt <原话>，跳过首页/企业菜单。返回await_filters，尚未创建运行；返回唯一岗位、目标和北京时间chat_title。未审核只提醒，不阻止。

按返回title调用mcp__codex_app__set_thread_title（省略threadId，即当前聊天），随后ui_features.py sidebar收起左侧列表。使用open_in_codex的非CUA浏览器入口打开BOSS，然后ui_features.py login处理已登录提示。到推荐页停一次，用户选好条件回复1后，使用首次返回的plan_file加--confirm-filters创建运行，保持解析的目标。创建后立即launch_progress.py。

普通菜单启动同样使用ledger.start返回的chat_title改名、收起侧栏。侧栏已收起不再切换；无法读取状态时记未核验，不盲目切换。

## 已登录提示

ui_features.py login只处理BOSS范围内明确“已经登录”提示的确认按钮，一次点击后复查消失；无提示继续。验证码、异地登录、安全验证等不适用。未遇到真实提示时，不能宣称此页面实测成功。

## 今日表格和预计时间

daily_metrics.py与workbook共享按北京时间、企业岗位筛出的记录。只有首句发送已核验sent的行涂绿色；仅decision=greet不涂绿色。悬浮窗读取当前今日工作簿的实际候选行和绿色行，文件占用/写入落后时显示“表格待同步”，不虚报已写入。

本次目标按本次进度完成，今日累计跨运行延续。例如今日已有20绿色，再要求招呼50，则需新增50，今日最后70。跨午夜切换今日表，运行目标不重置。

剩余时间按实际平均处理时间和成功率，计算查看/招呼目标预计先达到者；样本不足显示估算中，不触发时间截止。

## 悬浮窗与防息屏

绿色暂停/继续按钮及点击区域放大，按面板高度居中。button_geometry覆盖100/125/150%尺寸。运行/数量收尾时，悬浮窗主线程申请Windows显示和系统保持唤醒；暂停、结束和退出释放。线程/进程退出也由Windows清除申请，不移动鼠标或永久改电源设置。
