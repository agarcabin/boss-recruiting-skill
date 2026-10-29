# Windows UI Automation

控制口径见 [control-policy.md](control-policy.md)，操作入口见 [click-modes.md](click-modes.md)。

BOSS仍使用定向Win32 UIA和本地Win32截图。禁止CUA（包括只读绑定/截图）、DOM、整页AX、网页脚本及CDP。曾观察CUA绑定触发刷新，该工具限制本轮未删除。

默认Invoke；鼠标轨迹仅用户开启时使用。不强制抢焦点；键盘要求焦点已经在BOSS文档。举报/不合适/删除控件仍禁用。普通窗口遮挡允许后台Invoke，截图不得把遮挡图像冒充简历。

目标RuntimeId用于寻址，不再核对候选人姓名、候选人祖先、活跃账本键、名称/类名、generation、deadline或一次性凭据。窗口/控件不存在时工具返回实际错误，重新定位，不盲点。

卡片has-viewed可读时用于选择未查看起点；状态节点缺失或冲突时记未知，继续读取当前卡片，不要求人工确认。

页面加载/Document异常允许等待、重查一次；需要时在焦点正确的BOSS文档使用Refresh，或明确非CUA入口重开一次。恢复后旧RuntimeId作废，重新定位、重读同事进度及内容。不因一次查询返回0强制停机，也不无限刷新。验证码、风控、登录失效或平台限制按保留规则处理。

## 本机实测页面层级与控件归属（2026-10-27）

用户在 BOSS 页面留下的批注确认，同一视觉浮层中的控件分属不同 iframe，不能只按屏幕位置猜文档：

| 功能 | 浏览器层级 / URL | 已观察到的页面控件 | 操作定位约定 |
| --- | --- | --- | --- |
| 推荐卡片列表 | 推荐页 `https://www.zhipin.com/web/chat/recommend`；推荐 iframe `https://www.zhipin.com/web/frame/recommend/?jobid=...`。Win32 UIA 有时把卡片挂在 `Document: BOSS直聘` 主 URL 下 | `ListItem` / `ClassName=card-item`，卡片容器类如 `candidate-card-wrap css-type-1` | 先按实际 UIA `DocumentUrl` 选唯一可见文档，再核对当前候选人完整 Name 与 viewed 状态 |
| 悬浮电子简历正文 | 推荐 iframe 内嵌套的 `https://www.zhipin.com/web/frame/c-resume/?source=recommend`；用户批注确认该 frame 内的 `div#resume` 是简历正文区域 | 浏览器节点 `div#resume`；UIA 不一定直接映射 DOM `id`，可映射为 `AutomationId=resume`，滚动容器也可能表现为 `ClassName=resume-detail-wrap` | 只从当前 c-resume Document 定向查找；采集脚本先查已知 wrapper，再查 `AutomationId=resume` 及其滚动父级。不得用推荐卡片摘要替代简历正文，也不得用 DOM 读取正文 |
| 悬浮简历的打招呼按钮 | 用户批注显示按钮属于父级推荐 iframe `.../web/frame/recommend/?jobid=...`，不属于 c-resume 正文 frame | 页面节点 `div.button-chat-wrap.resumeGreet > span.btn-doc > div.button-list > button.btn-v2.btn-v2-new`；UIA 应以当前实际可见文档中 `Button` / `Name=打招呼` 定位 | 即使按钮视觉上在简历浮层右侧，也回到推荐文档核验按钮；核对候选人祖先、按钮类名和发送状态，不能在 c-resume 文档里因找不到而改点列表同名按钮 |
| 简历浮层“下一位” | 打开简历时的推荐主 Document；用户批注及本机 UIA 观察到 `Group` / `ClassName=turn-btn next`，名称可为空 | `turn-btn next` 是可复用的类名模式，不是可长期保存的控件句柄 | 定向UIA找到当前箭头RuntimeId后Invoke，不再作候选人祖先/账本归属匹配。不得跨候选人复用旧 RuntimeId。Invoke 后核验 c-resume 文档或可见页面状态变化；`dispatched` 不代表已切换，不再比对候选姓名。 |


查找窗口可用resolve-recruiting-window.ps1；该步骤不再要求随后绑定Codex停止按钮。长截图/OCR仅在有需要时使用，不是所有候选人的强制前置。
