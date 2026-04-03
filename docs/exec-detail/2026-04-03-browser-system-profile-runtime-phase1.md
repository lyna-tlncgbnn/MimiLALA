# 2026-04-03 Browser System Profile Runtime Phase 1

## 背景

之前浏览器子图主要走的是：

- Playwright `chromium.launch()`
- `browser.new_context()`
- Agent 自己管理一个隔离 context

这条路径虽然能完成自动化，但和 browser-use 的本地浏览器模式差异很大，也容易出现：

- 手动新开标签页行为不自然
- 浏览器环境与本机真实浏览器割裂
- 难以继承本地 profile 的站点行为和设置

## 本次目标

把浏览器 session 层往 browser-use 的本地浏览器模式靠拢，但不改动现有：

- LangGraph 主图 / 子图边界
- transcript / runs / run_steps / checkpoints
- 前后端时间线与消息协议

## 本次实现

### 1. 浏览器配置模型扩展

在 [settings.py](/F:/AgentBot/agentbot/config/settings.py) 中新增：

- `browser.mode`
- `browser.executable_path`
- `browser.user_data_dir`
- `browser.profile_directory`
- `browser.temp_profiles_dir`
- `browser.copy_local_profile`

### 2. Session 启动链路重构

在 [session.py](/F:/AgentBot/agentbot/browser/session.py) 中把浏览器 runtime 明确拆成两条路径：

- `system`
- `playwright`

其中 `system` 模式会：

1. 解析本机浏览器可执行文件
2. 解析本机 `User Data`
3. 选择 profile 目录
4. 把 profile 复制到 workspace 下的临时目录
5. 用 `launch_persistent_context(...)` 启动真实本地浏览器语义的 persistent context

### 3. workspace 临时 profile 目录

临时 profile 目录正式落到：

- [browser_profiles](/F:/AgentBot/workspace/browser_profiles)

每个 session 使用自己的子目录，避免直接占用或污染原始 profile。

### 4. prepare 落库信息增强

在 [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py) 的 `browser_prepare` 中新增落库字段：

- `mode`
- `executable_path`
- `user_data_dir`
- `profile_directory`
- `temp_profile_dir`
- `cdp_url`

这样 run_steps 能直接看出当前 session 到底走的是哪条浏览器启动路径。

## 当前状态

这一步的重点是先把 session/runtime 主路径切干净，解决“继续堆小 patch”的问题。

下载事件、popup 生命周期和更细的 runtime 语义还会在后续阶段继续收敛。
