# Project Structure

## 顶层目录

当前仓库已经形成四层主结构：

```text
desktop/    Electron 桌面壳
ui/         React 前端
agentbot/   Python 后端与 Agent 运行时
docs/       项目文档
```

此外还有：

- `workspace/` 本地运行时数据库与产物
- `.agents/skills/` 仓库级技能

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

### `agentbot/graph/`

LangGraph 构建和 checkpoint 接入：

- `builder.py`
- `checkpoints.py`
- `nodes.py`
- `routes.py`

### `agentbot/storage/`

SQLite 主存储：

- `db.py`
- `schema.py`
- `bootstrap.py`
- `models.py`
- `repositories/`

### `agentbot/tools/`

工具模块与注册：

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

### `agentbot/memory/`

旧 JSONL 模块保留区。

当前不再是主聊天路径核心。

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
  技术结构真相
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

## `workspace/`

当前主要运行时文件：

- `agent_runtime.db`
- `langgraph_checkpoints.db`

如果文档和代码发生冲突，请以实际目录结构和当前 FastAPI/SQLite 主链路为准。
