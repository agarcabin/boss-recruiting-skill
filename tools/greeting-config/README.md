# 招呼配置总览

用于本地管理和编辑招聘岗位 Markdown 配置的 Windows 桌面工具。界面内嵌在单个 EXE 中，岗位配置始终保存在 EXE 所在目录。

## 下载与运行

从 GitHub Releases 下载 `打开招呼配置.exe`，放入「02 招呼配置」目录后双击运行。

程序会读取自身所在目录及下级公司目录中的 `.md` 文件，支持：

- 岗位配置表单与 Markdown 原文编辑
- 企业、岗位与收藏岗位导航
- 初始词库、AB 词库和 `A1+B1/B2` 分组
- 时间、地点、AI 复盘和招呼话术配置
- Syncthing 局域网同步状态查看及暂停/恢复
- DeepSeek 词库与地点扩充
- 本地备份与历史恢复

页面关闭后，本地服务会在 1 分钟内自动退出。

## DeepSeek 配置

公开版本不包含 API Key。第一次使用 AI 扩充时，界面会要求输入 DeepSeek API Key。

密钥使用 Windows DPAPI 加密，仅保存在当前 Windows 用户的本地应用数据目录，不写入岗位 Markdown、同步目录或 Git 仓库。

## 从源码构建

在 Windows PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

构建结果位于 `release\打开招呼配置.exe`。构建脚本会检查源码中是否出现疑似 API Key，发现后停止构建。

## 文件说明

- `src\招呼配置.html`：内嵌界面源码
- `src\招呼配置服务.cs`：本地文件、Syncthing 与 AI 服务
- `build.ps1`：Windows 单文件 EXE 构建脚本

## 数据与隐私

本工具只读取 EXE 所在目录中的 Markdown 配置。AI 扩充会把当前词库或地点内容发送到 DeepSeek；地点范围查询使用公开行政区划数据。使用前请确认这符合所在组织的招聘数据处理要求。
