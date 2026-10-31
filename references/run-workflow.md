# 投递运行流程（1.0.14）

现行入口：[连续运行](continuous-workflow.md)。限制仍以[control-policy.md](control-policy.md)为准。

1. quick_start首次解析并保存plan_file；只执行未完成的改名、侧栏、打开BOSS和已登录提示检查。未审核提醒一次。
2. 到推荐页等用户手动调整筛选并回复1；使用原plan_file --confirm-filters，不重解析或创建重复运行。
3. 显示悬浮窗，启动workflow_runner --launch；主循环完成同事检查、快速/完整评估、发送核验、收藏、一次写表及下一位。
4. needs_assessment/card_visual/followups是本地交接，按request_file的真实材料写response_file后自动续接，不重开候选人或逐名询问用户。
5. 主循环统一暂停/继续/结束。数量达标后不打开下一人，收尾并生成最终表格；无时长、滚动24小时额度或固定逐人间隔。1.1.1起所有岗位共用每5分钟最多10人的窗口，满额仅等待余时；慢电脑超过5分钟不额外等。按连续运行文档自动续接，不绕过rate_limited。

同事检查最高优先级。普通遮挡可后台UIA，截图须真实；未读取内容记未知。验证码、风控、账号退出及平台限制仍处理。单步命令仅用于明确调试或恢复，日常流程不继续由聊天手工拼接。
