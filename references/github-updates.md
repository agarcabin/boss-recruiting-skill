# 安装、更新与发布

本项目创新招聘组自用，所有项目信息已加密。

首次从官方GitHub HTTPS仓库页面取得固定提交的scripts/bootstrap.ps1。该脚本固定依赖清单SHA-256与Ed25519公钥；依赖清单先用PowerShell/.NET校验，再下载、核验并配置独立Python及固定哈希的轮子，最后验证ZIP签名。镜像只运输字节，未验证ZIP中的bootstrap不能作为首次信任根。脚本配置用户目录环境，不修改系统PATH或Python。默认安装到用户.codex/skills/boss-recruiting。

首次裸装配置环境后提示解密，密码提示“你是谁？”。输错/取消不显示内置资料，仍可创建origin=user项目；以后执行project_vault.py unlock --prompt可主动解锁。正确解密在当前Windows用户本地DPAPI保存数据密钥，后续免密。正式旧版通过原文件自动兼容迁移；旧包持有者可复现该兼容路径，因此不是强授权系统。

菜单第4项运行 runtime/win-x64/python/python.exe scripts/skill_update.py update。check只检查。最新正式Release须同时包含ZIP、同名.zip.sha256、同名.zip.sig；先验签再解包，再检查清单、哈希、版本与路径。公开下载不需账号；直连失败可走update-source.json备用前缀，认证失败不信任该内容。失败保留原安装并显示原因，不无限重试。

活动或暂停招聘运行须先结束；所有更新与新run创建共用数据库维护门。安装先备份、冻结历史岗位身份，整体替换通用代码和已解锁内置项目，SKILL.md最后更新；自建项目、历史运行、账本、资料和可用runtime保留。旧程序缺新build_id无法启动。断电导致维护门未释放时，使用已验签工具 skill_update.py recover --root <安装目录> --backup <本次备份目录>；只能恢复当前维护日志对应备份，不可任意选择历史备份。

发布者先同步版本和通用日志，再运行 skill_update.py build --output <目录>。默认收集内置项目加密，净化公开源码并扫描；签名私钥和稳定数据密钥只保留本机DPAPI，必须备份。缺密钥构建失败。自建项目默认不上传。仅提交构建返回的public_source目录，不能提交本地安装目录或私有源码。创建v<版本>标签及正式Release，上传ZIP、SHA和SIG三个附件，以--notes-file提交说明；发布后匿名检查、下载、验签、解包并做实际升级验证。

历史引用和发布附件已按本次迁移范围清理；平台缓存、他人旧克隆或已下载文件不能由本仓库撤回，不把删引用称为全球清除。
