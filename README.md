> 当前1.1.1增加所有岗位共用的10人/5分钟限速、Excel“运行状态”页中的简历保存失败原因，以及GitHub更新的四条备用线路和成功线路记忆。正常运行见[连续运行](references/continuous-workflow.md)；旧单步接口保留调试及恢复。历史完整旧测试集的问题仍按日志保留，不宣称已全部修复。

# BOSS Recruiting Skill

在Codex中使用的BOSS招聘Skill，包含岗位资料管理、卡片或简历评估、受控招呼及归档流程。当前版本见SKILL.md，更新内容见CHANGELOG.md。

招呼方式可选“单次打招呼 / 三连式打招呼”，所有岗位默认单次：点“打招呼”并核验成功后直接下一份简历/卡片，不点“继续沟通”。三连式保持原来的首句加第二、三句话术。运行可用--greeting-mode single/triple选择，详见references/greeting-modes.md。

## 安装与更新

从本仓库正式Release下载boss-recruiting-<版本>.zip并解压到本机Codex skills目录中的boss-recruiting文件夹。当前仓库公开，可以直接下载。本包使用Windows UI Automation；执行脚本需要本机Python 3.12以上或已配置的便携运行环境，现有业务脚本还使用Pillow、openpyxl、PyYAML及简历OCR所需依赖。

启动Skill后，首页第4项“更新项目”检查GitHub Release；有新版本时自动下载、校验、备份并安装。当前公开更新源无需GitHub账号、登录或GitHub CLI。

旧版1.0.0使用私有源配置；已有GitHub登录的用户可直接选择第4项更新。尚未配置GitHub CLI的旧版用户，可先下载1.01及以上版本覆盖Skill通用文件，保留本地profiles和runtime，之后即可匿名更新。

```text
python scripts/skill_update.py check
python scripts/skill_update.py update
python scripts/skill_update.py build --output dist
```

从1.0.8起，仓库与发布包包含通用指令、脚本、规则，以及全部企业完整岗位配置、审核记录、固定话术和project.json。当前共13个已审核岗位，见profiles/企业岗位索引.md。更新会备份并替换包内同路径的岗位文件，其他本地岗位保留；候选人资料、账本、运行报表、凭据及便携runtime不上传、不覆盖。审核结论随岗位保存，实际发送前仍须核验当前账号、岗位页面并取得用户授权。

1.0.7及更早的旧更新器不接受含profiles的发布包：首次升级到1.0.8请下载完整ZIP，先备份原Skill，再解压合并覆盖；不要删除本地runtime。随后可正常使用“更新项目”入口。

发布维护流程见references/github-updates.md。
