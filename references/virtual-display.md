# 虚拟副屏

副屏按钮优先使用真实显示器。只有当前处于**单显示器**状态时，点击“副屏”才会按需启动一块虚拟显示器；多显示器电脑不会创建虚拟屏，也不会切换到虚拟桌面。

## 启动与保留策略

- 虚拟屏只在点击“副屏”时启动，Skills 启动时不创建。
- 虚拟屏分辨率优先与主屏一致；驱动不支持同分辨率时使用最接近的同宽高比模式，并在回执中记录实际模式。
- 首次在一台机器上使用时先测量“加屏并亮屏”的耗时，结果写入本机设置，后续复用。
- `< 1 秒`：快速模式。每次点击现场启动，切回主屏后立即删除虚拟屏。
- `1–10 秒`：会话模式。首次点击启动后保留，切回主屏不删除；5 分钟无切换且窗口在主屏时自动删除。
- `>= 10 秒`：持久模式。首次点击启动后保留，切回主屏不删除；30 分钟无切换且窗口在主屏时自动删除。
- 点击“结束”或窗口关闭时，无论哪种模式都会删除虚拟屏。

## 拓扑要求

虚拟屏必须是**扩展屏**，位于主屏右侧，主屏的分辨率和位置保持不变（桌面图标不重排）。启动后核验：

- 主屏设备与 `bounds` 未变化；
- 虚拟屏 `top` 与主屏一致，`left` 不小于主屏 `right`；
- 窗口移动后 `MonitorFromWindow` 确实落在虚拟屏。

任一核验失败会删除虚拟屏并报错，不继续移动窗口。

Codex 窗口处于最大化状态时，移动流程会先还原窗口、移动到目标屏工作区、再最大化；否则 Windows 只会改“还原位置”，窗口仍留在原屏。

## 驱动

使用 Parsec VDD 0.41（签名 IddCx 驱动，安装包约 220KB）。驱动只需安装一次，运行时不要求管理员权限。

- 已安装：直接通过 IOCTL 增删显示器，50ms 心跳保活。
- 未安装：首次点击时下载并校验安装包（固定 SHA256，验签主体必须包含 `Parsec Cloud`），然后请求一次 UAC 管理员授权并静默安装。
- 离线环境可把 `parsec-vdd-0.41.0.0.exe` 放到 `runtime/vdd/`，Skills 会优先使用该文件。
- 安装失败、验签失败、驱动未就绪或无法打开设备时停止本次切换，不点坐标、不使用 CUA。

驱动接口（仅用于排查）：设备接口 `{00b41627-04c4-429e-a26e-0265cf50c8fa}`，`ADD=0x0022E004`、`REMOVE=0x0022A008`、`UPDATE=0x0022A00C`、`VERSION=0x0022E010`。

## 故障码

- `virtual_display_driver_missing` / `virtual_display_driver_unavailable`：驱动未安装或设备未就绪。
- `virtual_display_driver_download_failed` / `virtual_display_driver_signature_invalid`：安装包下载或验签失败。
- `virtual_display_driver_install_cancelled`：用户取消了管理员授权。
- `virtual_display_monitor_not_detected`：加屏后 Windows 未亮屏。
- `virtual_display_primary_changed` / `virtual_display_not_right_of_primary`：拓扑不符合“主屏不变、扩展在右”。
- `virtual_display_ioctl_failed`：驱动通信失败。
