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

- `workspace/` 本地运行时数据库与浏览器 artifacts
- `.agents/skills/` 仓库级 skills

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
  结构化浏览器动作执行与动作后副作用处理
- `session.py`
  Playwright 会话生命周期、runtime 事件记录、下载目录管理
- `dom_service.py`
  页面 observation、交互元素提取、稳定 selector 映射、frame-aware 页面摘要
- `observation_capture.py`
  raw capture 层，采集 main document / iframe document、candidate elements、headings、landmarks、page info
- `observation_serialize.py`
  serialization 层，负责 candidate ranking、semantic groups、prioritized hints、`BrowserStateSummary` 输出
- `loop_detection.py`
  轻量 loop detection 与页面指纹
- `views.py`
  浏览器子图的数据模型与结构化动作模型

当前职责边界：

- 负责浏览器子图内部 runtime
- 不负责主图普通 tools 调度
- 不负责完整 `browser-use` event bus / watchdog 基础设施

### `agentbot/graph/`

LangGraph 构建与 checkpoint 接入：

- `builder.py`
- `browser_nodes.py`
- `browser_routes.py`
- `browser_subgraph.py`
- `checkpoints.py`
- `nodes.py`
- `routes.py`

其中浏览器相关职责是：

- `browser_subgraph.py`
  组装浏览器子图
- `browser_nodes.py`
  浏览器子图的 prepare / observe / decide / act / evaluate / finish 节点
- `browser_routes.py`
  浏览器子图条件路由

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

- 保持浏览器子图单动作 planner 协议
- 借鉴 `browser-use` 的高价值浏览器规则
- 不直接迁移 `browser-use` 完整多动作 agent loop 输出格式

### `agentbot/memory/`

历史 JSONL 模块保留区。
当前不再是主聊天链路核心。

## `ui/`

### `ui/src/app/`

应用壳与全局入口：

- `App.tsx`
- `app-shell.tsx`
- `main.tsx`
- `styles.css`

### `ui/src/features/`

按功能域拆分：

- `chat/`
- `conversations/`
- `settings/`

### `ui/src/shared/`

共享基础设施：

- `api/`
- `ui/`
- `lib/`

### `ui/src/state/`

前端全局 UI 状态：

- `ui-store.ts`

## `docs/`

当前文档按职责分为：

- `architecture/`
  技术结构真相与当前边界
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

- `docs/architecture/graph-flow.md`
- `docs/architecture/runtime-flow.md`
- `docs/architecture/browser-use-migration-todo.md`

## `workspace/`

当前主要运行时文件：

- `agent_runtime.db`
- `langgraph_checkpoints.db`
- `browser_artifacts/`

如果文档和代码发生冲突，请以实际目录结构和当前 FastAPI / SQLite / LangGraph 主链路为准。
