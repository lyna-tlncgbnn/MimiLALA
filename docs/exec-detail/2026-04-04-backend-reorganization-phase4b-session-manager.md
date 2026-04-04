# 2026-04-04 Backend Reorganization Phase 4B Session Manager Split

## 目标

执行按 `browser-use` 风格收窄后的 Phase 4B：

- 不把 `agentbot/browser/session.py` 过度打散
- 先抽出 session registry / 目录 / close cleanup
- 保持 browser runtime 创建与 watchdog 装配仍在 `session.py`

## 本次改动

新增：

- `agentbot/browser/session_manager.py`

调整：

- `agentbot/browser/session.py`

## 拆出的职责

`session_manager.py` 现在承载：

- runtime session registry
- session 注册与移除
- artifacts / profiles / downloads 目录 helper
- orphan temp profile 清理
- runtime close cleanup

对应导出的能力包括：

- `register_runtime_session`
- `get_runtime_session`
- `discard_runtime_session`
- `browser_output_dir`
- `browser_profiles_dir`
- `browser_session_artifacts_dir`
- `browser_download_dir`
- `cleanup_orphan_browser_profiles`
- `close_runtime_session`

## 保留在 `session.py` 的职责

为了保持与 `browser-use` 接近的“中度拆分”尺度，本阶段没有继续下沉这些内容：

- `BrowserSessionState`
- `BrowserRuntimeSession`
- `start_browser_session`
- runtime 创建入口
- Playwright / system browser 启动
- watchdog 初始化与页面事件挂载
- downloads / profile / executable 相关底层实现

## 为什么这样拆

这一步的目标不是把 `session.py` 变成极薄 facade，而是先让 session lifecycle 中最稳定、最独立的一层脱离出来：

- registry
- directory management
- lifecycle cleanup

这样做更接近 `browser-use` 的做法，也避免把当前 runtime 创建逻辑拆得过碎。

## 结果

本次之后：

- `agentbot/browser/session.py` 从 832 行降到 788 行
- `agentbot/browser/session_manager.py` 新增 81 行

收益主要在于边界更清晰，而不是单纯追求行数下降。

## 未在本阶段处理的内容

以下内容仍保持不动：

- `_create_runtime_session`
- `_create_playwright_runtime_session`
- `_create_system_runtime_session`
- watchdog attachment
- dialog / popup / navigation handler 细节

如果后续还要继续推进 browser session 层整理，应先观察这些区域是否真的形成高频改动点，再决定是否继续拆。

## 验证

本次至少验证：

- `py_compile` 通过：
  - `agentbot/browser/session.py`
  - `agentbot/browser/session_manager.py`
- FastAPI app 仍可正常导入
- `start_browser_session` / `get_runtime_session` / `close_browser_session` 导入正常

## 判断

这一步符合“参考 `browser-use`，但不过度细拆”的目标：

- 有单独的 session manager
- `session.py` 仍保留主 session lifecycle 入口
- 没有提前打散 runtime 创建与 watchdog 装配逻辑
