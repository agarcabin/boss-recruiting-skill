# BOSS Recruiting Skill

在Codex中使用的BOSS招聘Skill，包含岗位资料管理、卡片或简历评估、受控招呼及归档流程。当前版本见SKILL.md，更新内容见CHANGELOG.md。

## 安装与更新

从本仓库正式Release下载boss-recruiting-<版本>.zip并解压到本机Codex skills目录中的boss-recruiting文件夹。当前仓库公开，可以直接下载。本包使用Windows UI Automation；执行脚本需要本机Python 3.12以上或已配置的便携运行环境，现有业务脚本还使用Pillow、openpyxl、PyYAML及简历OCR所需依赖。

启动Skill后，首页第4项“更新项目”检查GitHub Release；有新版本时自动下载、校验、备份并安装。当前公开更新源无需GitHub账号、登录或GitHub CLI。

旧版1.0.0使用私有源配置；已有GitHub登录的用户可直接选择第4项更新。尚未配置GitHub CLI的旧版用户，可先下载1.01及以上版本覆盖Skill通用文件，保留本地profiles和runtime，之后即可匿名更新。

```text
python scripts/skill_update.py check
python scripts/skill_update.py update
python scripts/skill_update.py build --output dist
```

仓库与发布包包含通用指令、脚本和规则。岗位配置、候选人资料、账本、运行报表、凭据及便携runtime保留在使用者本机。更新会保留这些本地内容；岗位可另用Skill的项目分享与导入功能迁移。实际招聘发送需要用户授权。

发布维护流程见references/github-updates.md。
