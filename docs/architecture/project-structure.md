# Project Structure

## 顶层目录

当前仓库已经形成四层主结构：

```text
desktop/    Electron 桌面壳
ui/         React 前端
agentbot/   Python 后端与 Agent Runtime
docs/       项目文档
```

此外还有：

- `workspace/`
  本地运行时数据库、浏览器 artifacts、下载目录、临时浏览器 profile
- `.agents/skills/`
  仓库级 skills

## 运行入口

- `main.py`
  CLI 入口
- `agentbot/api/app.py`
  FastAPI 入口
- `desktop/electron/main.js`
  Electron 入口

## `agentbot/`

### `agentbot/app/`

运行入口与执行调度：

- `cli.py`
- `runner.py`
- `streaming_runner.py`

### `agentbot/api/`

FastAPI 接口层：

- `app.py`
- `schemas.py`
- `serializers.py`
- `routes/`

### `agentbot/services/`

业务语义层：

- `conversations.py`
- `chat.py`

### `agentbot/config/`

配置读取与校验：

- `settings.py`

### `agentbot/browser/`

浏览器子图支撑层：

- `actions.py`
  graph 与 runtime 之间的兼容层，把 `BrowserAction` 翻译成 runtime action event
- `session.py`
  浏览器会话生命周期、本地 profile、downloads、artifacts、runtime 初始化与 browser state request 入口
- `dom_service.py`
  browser state 入口封装；当前已经改成通过 runtime 请求 browser state
- `observation_capture.py`
  raw capture 层，采集 main document / iframe document、candidate elements、headings、landmarks、page info
- `observation_serialize.py`
  serialization 层，负责 candidate ranking、semantic groups、prioritized hints、`BrowserStateSummary` 输出
- `loop_detection.py`
  轻量 loop detection 与页面指纹
- `views.py`
  浏览器子图的数据模型与结构化动作模型

#### `agentbot/browser/runtime/`

Browser Runtime V2 的核心目录：

- `event_bus.py`
  runtime event bus
- `events.py`
  runtime 事件模型
- `watchdog_base.py`
  watchdog 基类
- `watchdogs/`
  runtime watchdog 分层

#### `agentbot/browser/runtime/watchdogs/`

当前已实现的 watchdog：

- `default_action_watchdog.py`
  动作执行中间层
- `downloads_watchdog.py`
  下载开始、下载完成、active downloads
- `popups_watchdog.py`
  新 tab / popup 与 page close
- `dialogs_watchdog.py`
  dialog 处理
- `navigation_watchdog.py`
  导航完成
- `lifecycle_watchdog.py`
  page/browser lifecycle
- `dom_watchdog.py`
  BrowserStateRequestEvent、DOM cache、selector map cache、screenshot capture

当前职责边界：

- 浏览器 runtime 已经开始向 `browser-use` 靠拢
- graph 不再直接管理 DOM cache
- 但外层仍然保留 LangGraph 子图结构和现有 run_steps/timeline 协议

### `agentbot/graph/`

LangGraph 构建与 checkpoint 接入：

- `builder.py`
- `browser_nodes.py`
- `browser_routes.py`
- `browser_subgraph.py`
- `checkpoints.py`
- `nodes.py`
- `routes.py`
- `state.py`

其中浏览器相关职责是：

- `browser_subgraph.py`
  组装浏览器子图
- `browser_nodes.py`
  浏览器子图的 prepare / observe / decide / act / evaluate / finish 节点
- `browser_routes.py`
  浏览器子图条件路由
- `state.py`
  浏览器子图相关状态字段

### `agentbot/storage/`

SQLite 主存储：

- `db.py`
- `schema.py`
- `bootstrap.py`
- `models.py`
- `repositories/`

### `agentbot/tools/`

普通工具模块与注册：

- `basic.py`
- `codebase.py`
- `common.py`
- `command.py`
- `editing.py`
- `filesystem.py`
- `web_fetch.py`
- `web_search.py`
- `registry.py`
- `infra/`
- `providers/`

### `agentbot/prompts/`

提示词模块：

- `system.py`
- `browser_subgraph.py`

其中 `browser_subgraph.py` 当前职责是：

- 维护浏览器子图 planner 协议
- 借鉴 `browser-use` 的高价值浏览器规则
- 向 planner 暴露 browser state、planner state、action history、plan state

### `agentbot/memory/`

历史 JSONL 模块保留区。当前不再是主链路核心。

## `workspace/`

当前主要运行时文件：

- `agent_runtime.db`
- `langgraph_checkpoints.db`
- `browser_artifacts/`
- `browser_downloads/`
- `browser_profiles/`

其中：

- `browser_artifacts/`
  保存每个 session 的页面截图等 artifacts
- `browser_downloads/`
  保存配置为统一下载目录的下载文件
- `browser_profiles/`
  system browser 模式下复制出的临时 profile

## `docs/`

当前文档按职责分为：

- `architecture/`
  技术结构事实与当前边界
- `product/`
  产品范围与路线
- `runbooks/`
  使用与排障
- `decisions/`
  技术决策
- `exec-detail/`
  已完成实现说明
- `exec-plans/`
  计划与归档

与浏览器子图最相关的文档包括：

- [graph-flow.md](/F:/AgentBot/docs/architecture/graph-flow.md)
- [browser-observation-pipeline.md](/F:/AgentBot/docs/architecture/browser-observation-pipeline.md)
- [browser-planner-state.md](/F:/AgentBot/docs/architecture/browser-planner-state.md)
- [browser-runtime.md](/F:/AgentBot/docs/architecture/browser-runtime.md)
- [browser-use-migration-todo.md](/F:/AgentBot/docs/architecture/browser-use-migration-todo.md)

如果文档和代码发生冲突，以实际目录结构和当前 FastAPI / SQLite / LangGraph 主链路为准。
