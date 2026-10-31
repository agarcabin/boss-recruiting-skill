# 从 GitHub 更新 Skill

菜单第4项“更新项目”现在用于从GitHub检查和更新本Skill。仓库固定在根目录update-source.json；使用GitHub最新正式Release，不从默认分支直接覆盖安装。

## 选择更新项目

在当前对话执行，不先要求用户选择企业或岗位：

```text
runtime/win-x64/python/python.exe scripts/skill_update.py update
```

没有便携Python时使用本机Python 3.12及以上。当前仓库公开，update-source.json中private=false，直接通过HTTPS检查与下载，无需GitHub账号、登录或GitHub CLI。只有另行配置私有源时才需要本机GitHub CLI及有效登录；无法访问时说明具体错误，保留当前安装，不要求用户把令牌贴到聊天中。

- up_to_date：显示当前与远端版本，无需下载；不降级。
- no_release：显示该仓库尚无可访问正式版本。
- updated：显示旧版本、新版本及备份目录，重新读取SKILL.md和本次Release的CHANGELOG.md，再按新版本继续；不用重启或重新审核未变化的本地岗位。
- error：显示各线路具体错误并保留当前安装；活动或暂停的招聘运行须先正常结束，才能安装更新。每条线路只尝试一次，失败顺序切换；所有线路均失败后停止，不无限重试。校验失败、路径异常的文件不安装。

用户选择该入口即授权本次检查、下载及安装正式新版本，不再追加升级确认。此入口不创建投递运行。用户明确要改企业岗位资料时，仍按project-operations.md中的“岗位资料更新”处理。

## 更新范围

从1.0.8起，发布包包含SKILL.md、CHANGELOG.md、README.md、update-source.json、agents/references/scripts，以及profiles中的全部岗位Markdown、审核记录、索引和project.json。profiles只接受.md与名为project.json的配置文件。下载后核对ZIP的SHA-256和包内每个文件的清单、哈希、版本与仓库；拒绝越界路径、符号链接、未列入清单及候选人/运行数据条目。

安装前在本机用户数据目录保存被替换文件和restore.json；普通安装失败自动回滚。SKILL.md版本标记最后替换。包内同路径profiles文件先备份再替换，未随包提供的本地岗位不删除；便携runtime、Git目录、候选人资料、账本、截图及运行报表不上传、不覆盖。备份位于%LOCALAPPDATA%/Codex/recruiting-greetings/updates/backups。

检查版本而不下载安装可执行scripts/skill_update.py check。自动检查只在选择“更新项目”时发生，不创建后台定时任务。

## 国内网络备用线路（1.1.1）

公开仓库使用GitHub直连加四条HTTPS备用前缀：gh-proxy.org、gh-proxy.com、ghfast.top、ghproxy.net，配置在update-source.json的mirrors。首次直连优先，失败依次尝试；版本检查与安装包下载分别记住最后成功线路，下次优先该线路，失败再回退其他地址。偏好保存在本机用户数据目录updates/routes-*.json，不随更新包覆盖。单次网络操作超时12秒。

版本API不可达时还可尝试最新正式Release页面的canonical/og:url标签，再按固定仓库、版本和附件名构造下载地址；不把普通网页或镜像首页当成有效版本。下载ZIP和SHA-256都走同一候选线路，校验整个包及每个文件通过后才记为下载成功；错误页面、校验不符或损坏ZIP均换下一条。私有仓库继续走gh，不把凭据发送到公共备用站。

2026-10-31本机禁用HTTP代理配置的连通测试：gh-proxy.org和gh-proxy.com的版本API与校验文件下载通过；ghfast.top仅附件下载通过，ghproxy.net本次超时。公共线路可用性随网络变化，不能保证所有国内网络均通；工具按实际结果切换。使用方式参考[GH-Proxy官方文档](https://gh-proxy.com/docs/github-accelerator)。

## 发布新版本

当前采用三段式版本a.b.c，常规更新只将c加1，c超过10也不进位；只有用户明确要求b+1才修改b。当前版本见SKILL.md；旧两位小数版本仅作兼容。

完成修改和验证后同步版本与日志，再构建附件：

```text
python scripts/skill_update.py build --output <发布附件目录>
```

将Skill源码与完整profiles（企业岗位配置、审核记录、固定话术、project.json及索引）提交并推送到update-source.json指定仓库；runtime和候选人运行数据只保留本地。创建与版本一致的正式Release（标签v<版本号>），上传boss-recruiting-<版本号>.zip及同名.zip.sha256两个附件；使用gh release create的--notes-file传入发布说明。发布后实际运行check核对版本与附件，并从GitHub下载验证；不要将仅推送分支或仅创建标签当作可用更新。

## 从旧更新器迁移

1.0.7及以前的更新器禁止profiles，因此不能直接安装1.0.8完整包。首次迁移应下载1.0.8完整ZIP，先备份原Skill，解压合并覆盖Skill文件（保留runtime）；以后正常使用更新入口。不得仅改旧版本号绕过包校验。发布时明确告知此兼容事项。
