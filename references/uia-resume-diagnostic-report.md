# BOSS 电子简历 UIA 定位诊断报告

测试时间：2026-10-21 15:06  
测试环境：Codex 内置浏览器，Windows UI Automation  
测试对象：当前已打开的 BOSS 电子简历  
测试约束：仅使用原生 UIA；未使用 Playwright、frameLocator、DOM Snapshot、页面刷新或重复 getTab

## 结论摘要

本次同时确认了两个独立问题：

1. `AutomationElement.FromPoint` 没有命中 `c-resume`，而是命中了 Codex 页面上的同一层全屏透明 Group。
2. 点击简历正文后，`FocusedElement` 能正确进入 `c-resume`，但简历正文仍没有暴露为 UIA Text 控件。

因此，这既是**坐标命中定位问题**，也是**正文可访问性缺失问题**。

## 基线

找到的简历 Document：

| 属性 | 值 |
|---|---|
| Name | BOSS直聘 |
| ControlType | Document |
| FrameworkId | Chrome |
| ProcessId | 61228 |
| RuntimeId | `42,1837948,4,83,3,4610` |
| BoundingRectangle | `(1193, 282, 851, 4802)` |
| Patterns | ValuePattern、ScrollPattern、TextPattern、ScrollItemPattern |

## 测试 A：坐标命中

坐标由当前 `c-resume` 实际矩形和屏幕尺寸计算，不使用截图像素常量。

| 测试位置 | 坐标 | FromPoint 命中 | RuntimeId | 是否属于 c-resume |
|---|---:|---|---|---|
| 简历正文 | `(1618, 875)` | Group，Name/Class 为空 | `42,1837948,4,6,1,369188` | 否 |
| 右侧操作区 | `(2302, 875)` | 同一 Group | `42,1837948,4,6,1,369188` | 否 |
| 浮窗外背景 | `(1043, 875)` | 同一 Group | `42,1837948,4,6,1,369188` | 否 |

三个点命中完全相同的 RuntimeId。该元素矩形为 `(946,224,1616,1294)`，父链最终进入 Codex 的 “读取 自动打招呼 skill” Document，而不是 `c-resume`。

父链中出现的关键类名：

- `pointer-events-none fixed inset-0 [contain:paint]`
- `pointer-events-none fixed inset-0 overflow-visible`
- `Chrome_RenderWidgetHostHWND`
- `Chrome_WidgetWin_1`

结论：坐标命中层被 Codex 的全屏交互覆盖层拦截，`FromPoint` 无法直接命中电子简历。

## 测试 B：焦点归属

### 点击简历正文后

`AutomationElement.FocusedElement` 返回：

- Name：BOSS直聘
- ControlType：Document
- RuntimeId：`42,1837948,4,83,3,4610`

父级链：

```text
BOSS直聘 Document
  -> 空 Document
  -> resume-detail-wrap
  -> lib-standard-resume ... wasm-resume-layout lib-resume-recommend
  -> boss-popup__wrapper boss-dialog recommendV2
  -> dialog-wrap active
  -> boss-layer__lock-scroll
  -> 推荐牛人 Document
```

结论：实际点击成功进入了电子简历浮窗，焦点归属正确。

### 点击右侧操作区后

`FocusedElement` 返回“推荐牛人” Document，父链位于推荐列表 iframe 中。

结论：正文和右侧区域属于不同的焦点容器，不是同一个可访问性正文节点。

## 测试 C：Pattern 与 RawView

对 `FromPoint` 返回的正文位置元素检查：

- TextPattern：不可用
- ValuePattern：不可用
- LegacyIAccessiblePattern：不可用

但该元素不是 `c-resume` 本身，所以这些结果只能说明“命中的覆盖层不可读”，不能代表简历 Document。

此前对实际 `c-resume` Document 的检查结果：

- TextPattern：可用
- DocumentRange 文本：只有右侧“经历概览”和操作按钮
- Text 子控件数量：0
- RawView 子节点：1 个 Image

父链中的类名包含 `wasm-resume-layout`，说明中间正文很可能是 WebAssembly/自定义渲染区域，没有生成可被 UIA 直接读取的文本节点。

## 回答问题

### A. UIA 是否实际命中了浮窗正文？

`FromPoint` 没有。点击后的 `FocusedElement` 命中到了 `c-resume` Document。

### B. UIA 是否只抓取了背景页面？

`FromPoint` 和最初的 TextPattern 行为确实落到背景/概览层；点击后焦点可以进入 `c-resume`。

### C. 正文是否存在独立的 UIA 子控件？

没有发现。`c-resume` 的 UIA 子树只有 1 个 Image，没有 Text、Edit 或可读取正文的 Pane。

### D. 是定位问题还是可访问性接口不暴露文本？

两者都有：

1. `FromPoint` 被 Codex 覆盖层拦截，属于定位问题。
2. `FocusedElement` 已正确进入 `c-resume`，但正文没有 UIA Text 节点，属于可访问性暴露问题。

### E. 是否值得继续研究 UIA？

不建议继续投入在“直接通过 UIA TextPattern/RawView 读取中间正文”上。

UIA 仍适合：

- 确认 `c-resume` 是否打开。
- 通过 FocusedElement 定位简历容器。
- 获取右侧经历概览。
- 控制鼠标拖选。

完整正文应优先使用：

1. UIA `resume-detail-wrap` 内层滚动 + 固定视口截图 + 长图拼接。
2. 长图分块 RapidOCR。

生产流程见 [长截图与 RapidOCR](resume-capture-ocr.md)。Windows 自带 OCR 和拖选复制保留为历史对照与异常兜底。

## 原始诊断命令

诊断脚本：

```text
scripts/uia-resume-diagnostic.ps1
```

执行方式：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/uia-resume-diagnostic.ps1 -WindowHandle <HWND>
```
