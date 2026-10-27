# 从 GitHub 更新 Skill

菜单第4项“更新项目”现在用于从GitHub检查和更新本Skill。仓库固定在根目录update-source.json；使用GitHub最新正式Release，不从默认分支直接覆盖安装。

## 选择更新项目

在当前对话执行，不先要求用户选择企业或岗位：

```text
runtime/win-x64/python/python.exe scripts/skill_update.py update
```

没有便携Python时使用本机Python 3.12及以上。私有仓库需要本机GitHub CLI及有效登录；无法访问时说明具体错误，保留当前安装，不要求用户把令牌贴到聊天中。

- up_to_date：显示当前与远端版本，无需下载；不降级。
- no_release：显示该仓库尚无可访问正式版本。
- updated：显示旧版本、新版本及备份目录，重新读取SKILL.md和本次Release的CHANGELOG.md，再按新版本继续；不用重启或重新审核未变化的本地岗位。
- error：说明原因，保留当前安装；活动或暂停的招聘运行须先正常结束，才能安装更新。校验失败、路径异常、下载失败不继续安装，不自动重试。

用户选择该入口即授权本次检查、下载及安装正式新版本，不再追加升级确认。此入口不创建投递运行。用户明确要改企业岗位资料时，仍按project-operations.md中的“岗位资料更新”处理。

## 更新范围

发布包只包含SKILL.md、CHANGELOG.md、README.md、update-source.json及agents/references/scripts。下载后核对ZIP的SHA-256和包内每个文件的清单、哈希、版本与仓库；拒绝越界路径、符号链接和覆盖本地数据的条目。

安装前在本机用户数据目录保存被替换文件和restore.json；普通安装失败自动回滚。SKILL.md版本标记最后替换。profiles、便携runtime、Git目录、候选人资料、账本、截图及运行报表保留本地，更新不上传或覆盖。备份位于%LOCALAPPDATA%/Codex/recruiting-greetings/updates/backups。

检查版本而不下载安装可执行scripts/skill_update.py check。自动检查只在选择“更新项目”时发生，不创建后台定时任务。

## 发布新版本

当前正式发布基线为1.0.0；后续沿用每次+0.01的约定，1.0.0按1.00计算，下一版1.01，再下一版1.02。更新器同时支持三段式版本及两位小数版本，比较时1.10对应1.1.0。

完成修改和验证后同步版本与日志，再构建附件：

```text
python scripts/skill_update.py build --output <发布附件目录>
```

将通用Skill源码提交并推送到update-source.json指定仓库，保留profiles及runtime在本地。创建与版本一致的正式Release（标签v<版本号>），上传boss-recruiting-<版本号>.zip及同名.zip.sha256两个附件；使用gh release create的--notes-file传入发布说明。发布后实际运行check核对版本与附件，并从GitHub下载验证；不要将仅推送分支或仅创建标签当作可用更新。
