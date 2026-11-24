# 内置浏览器鼠标轨迹

本文件的鼠标点击、点击后移动及等待时移动，仅在用户明确开启 `use_mouse_trajectory=true` 并授权实际操作时使用；默认值为 `false`，未指定时也按[点击方式开关](click-modes.md)使用 UIA `InvokePattern.Invoke()`，不运行本文件的鼠标移动脚本，也不调用鼠标拟人 skill。下文的聊天小窗键盘发送规则适用于两种点击方式。页面观察和控件定位始终通过 Win32 UI Automation 定向查询完成，禁止使用 CUA 绑定、截图、读取、点击或导航 BOSS 页面；本地鼠标脚本不能识别候选人或判断发送成功。

1. 从最新 Win32 UIA 定向查询结果定位目标控件，并取得其**物理屏幕像素**中心。取得 Codex 浏览器顶层窗口句柄，以及浏览器 Document 的物理边界 `left,top,right,bottom`。截图缩放像素和 CSS 像素不可直接使用。无法可靠取得任一数据时停止。
2. 确认目标窗口可见、未最小化、没有其他人使用鼠标。页面滚动、窗口移动或缩放后重新获取坐标和边界。目标控件越界时不发送输入。若只是当前鼠标起点在 BOSS 内容边界外（例如停在 Codex 对话区），且用户已授权代为移动鼠标，可先用 Windows `SetCursorPos` 将鼠标无点击地移到 BOSS 内容区内的安全空白位置；随后重新读取光标位置、做一次 `-DryRun` 并确认整条轨迹都在边界内，再执行页面操作。此定位移动不得点击，也不得把鼠标移到发送、删除或举报等控件上。若窗口或页面边界不明确，或重新预演仍越界，则停止。
3. Codex 必须已经最大化。`move-click.ps1` 遇到未最大化的窗口时会先最大化并拒绝本次点击；重新获取页面坐标和内容边界后再执行，脚本不得使用 `SW_RESTORE` 还原窗口。
4. 使用 PowerShell 7 运行本 Skill 的 `scripts/move-click.ps1`，传入 `-X`、`-Y`、`-WindowHandle` 和 `-ContentBounds`；必要时先用 `-DryRun` 检查轨迹。一次操作只运行脚本一次，随后从页面状态确认结果。结果不明时停止，不能重复点击。
5. `move-click.ps1` 默认拦截“举报”“不合适”“删除”以及 `btn-report`、`btn-quxiao` 控件；命中禁止控件时不发送鼠标输入。
6. `move-click.ps1` 在真实点击后默认继续随机移动 `1000ms`，且落点与点击位置的直线距离至少约 `24px`；所有按钮点击后都不得把鼠标停在按钮上。点击后移动仍须保持在浏览器物理内容边界内。
7. 真实点击输出必须同时包含 `clickStartedAt` 和 `clickEndedAt`。切换进入候选人的 `clickStartedAt` 用作判断开始，切换离开候选人的 `clickEndedAt` 用作判断结束。

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass `
  -File "<本 Skill 路径>\scripts\move-click.ps1" `
  -X <目标中心 X> -Y <目标中心 Y> `
  -WindowHandle <顶层窗口句柄> `
  -ContentBounds "<left,top,right,bottom>"
```

脚本默认轨迹约 1400 毫秒，点击后随机移动 `1000ms`，支持 `-PostClickMoveMs`、`-PostClickMoveRadiusPx`、`-DurationMs`、`-Jitter`、`-PauseChance`、`-NoClick` 和 `-DryRun`。不要将点击后移动设为空操作。本招聘流程不使用随机空闲点击；等待时使用下列缓慢圆周移动。脚本会检查前台窗口和页面边界；任何检查失败都必须停下核对。轨迹不提供平台风控保证。

## 聊天小窗键盘发送

本节只适用于 `greeting_mode=triple`。默认 `single` 点完“打招呼”并核验后直接切换下一份简历/卡片，不点“继续沟通”，不打开小窗，不粘贴或回车发送。详见 [招呼方式开关](greeting-modes.md)。

只有账本 `reserve` 为 `ready`、发送前 `gate` 通过、当前候选人的聊天小窗已打开且 Codex 内置浏览器仍在前台时，才发送岗位话术。打开小窗后输入框默认获得焦点；不再查询输入框坐标或寻找发送按钮。把待发送的**单句**放入系统剪贴板，向当前前台窗口发送 `Ctrl+V`，随后按一次 `Enter`。每句单独粘贴、单独回车，发送后只定向核验该句消息已显示一次，再处理下一句。第二句与第三句之间重新运行 `gate`。不得用鼠标点击发送按钮，也不要因为没有立刻看到消息就再次回车。小窗未打开、前台窗口变化、焦点被抢走或结果不明时停止并按运行流程记录 `unknown`，不盲发或重发。

## 等待时的缓慢移动

仅在 `use_mouse_trajectory=true` 时，页面加载、风控复查或等待恢复期间使用 [idle_mouse.py](../scripts/idle_mouse.py) 在浏览器内容区域内做“5 秒缓慢圆周移动 + 5 秒停顿”的周期动作；该脚本不点击，也不会修改页面。`--duration-ms` 表示总等待时长，20 秒等待应产生 2 个 5 秒移动脉冲。`false` 时仅计时等待，不移动鼠标。

```powershell
python scripts/idle_mouse.py --x <中心X> --y <中心Y> --radius 24 --period-ms 2600 --duration-ms 20000 --active-ms 5000 --rest-ms 5000 --content-bounds "<left,top,right,bottom>" --window-handle <HWND>
```

- 中心点与整个半径范围必须位于浏览器物理内容边界内，否则停止。
- 每次移动脉冲默认 5 秒，脉冲之间停顿 5 秒；20 秒总等待产生 2 次移动。
- `--duration-ms` 是总等待时长，`--active-ms` 是每次移动时长，`--rest-ms` 是两次移动之间的停顿时长。
- 开始点击、滚动、填写或发送前必须等待移动命令结束，不能与真实操作并行。
- 页面滚动、窗口移动、缩放或内容边界变化后重新计算中心和边界。
- 坐标必须来自当前可见的 UIA 控件，不得复用旧详情面板或旧列表中的坐标。
