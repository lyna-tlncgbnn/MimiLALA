# 2026-04-03 Browser Runtime Config And Download Fix

## 背景

这次主要处理了三类浏览器 runtime 问题：

1. 可见浏览器窗口放大后，页面内容区域仍然保持固定宽度，边上出现空白
2. 下载成功后，浏览器子图仍可能误报 `Target page, context or browser has been closed`
3. 下载目录和 artifacts 目录不透明，用户不知道文件落到哪里

## 原因

### 1. 窗口空白

此前 browser session 启动时固定写死：

- `viewport = 1280 x 720`

即使用户手动把窗口拉大，页面渲染 viewport 仍然是固定尺寸，所以会出现“窗口变大，但页面内容区不跟着变”的现象。

### 2. 下载后误报浏览器关闭

此前下载等待逻辑里使用了：

- `runtime.page.wait_for_timeout(...)`

当下载动作使当前页面句柄进入不稳定状态时，这种等待可能抛出 page/context closed 类异常，进而被上层统一翻译成“浏览器关闭”，即使下载其实已经成功。

### 3. 下载目录不可见

此前默认下载路径是 session 目录下的内部 `downloads/`，但没有暴露成可配置项，也没有在配置文档里说明。

## 本次改动

### 配置增强

更新：

- `agentbot/config/settings.py`
- `config.json`
- `docs/runbooks/config.md`

新增 browser 配置项：

- `browser.max_actions_per_step`
- `browser.viewport_width`
- `browser.viewport_height`
- `browser.window_width`
- `browser.window_height`
- `browser.no_viewport`
- `browser.start_maximized`
- `browser.artifacts_dir`
- `browser.downloads_dir`
- `browser.channel`

### session 启动参数增强

更新：

- `agentbot/browser/session.py`
- `agentbot/graph/browser_nodes.py`

现在浏览器子图在启动 session 时，会把 `config.json` 里的浏览器参数传入 runtime，包括：

- headless / channel
- 窗口大小
- viewport 大小
- 是否禁用固定 viewport
- artifacts 目录
- downloads 目录

### artifacts / downloads 路径收口

更新：

- `agentbot/browser/session.py`
- `agentbot/browser/dom_service.py`
- `agentbot/browser/actions.py`

现在：

- 页面截图落到当前 session 的 `artifacts_dir`
- 动作截图也落到当前 session 的 `artifacts_dir`
- 下载文件落到 `downloads_dir`
- download event 会带上完整目标路径，而不是只报文件名

### 下载等待修复

更新：

- `agentbot/browser/actions.py`

把依赖 `runtime.page.wait_for_timeout(...)` 的下载轮询改成了纯 Python 侧的 `sleep(...)` 轮询，并对 page settle / page url 读取补了更安全的 closed 检查。

这能显著降低“下载已成功，但 page 句柄瞬时失效后被误报成浏览器关闭”的概率。

## 当前 config.json 默认值

当前仓库已经写入：

- `browser.no_viewport = true`
- `browser.viewport_width = 1440`
- `browser.viewport_height = 900`
- `browser.window_width = 1440`
- `browser.window_height = 900`
- `browser.downloads_dir = "workspace/browser_downloads"`
- `browser.artifacts_dir = "workspace/browser_artifacts"`

## 验证

执行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

并确认：

1. `Settings.from_file()` 可以正确读取新增 browser 配置项
2. browser session 已接入 `no_viewport / downloads_dir / artifacts_dir / channel`
3. runtime 下载等待路径不再依赖 `runtime.page.wait_for_timeout(...)`
