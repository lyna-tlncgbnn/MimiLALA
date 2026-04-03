# Database Architecture

## 概览

当前主存储已经迁移到 SQLite。

数据库文件位于：

- `workspace/agent_runtime.db`
- `workspace/langgraph_checkpoints.db`

两者职责不同：

- `agent_runtime.db`
  产品层运行时数据
- `langgraph_checkpoints.db`
  LangGraph 线程 checkpoint

## `agent_runtime.db`

初始化入口：

- `agentbot/storage/bootstrap.py`
- `agentbot/storage/db.py`
- `agentbot/storage/schema.py`

当前 schema version：

- `1`

### 主要表

#### `conversations`

保存会话元数据。

字段：

- `conversation_id`
- `title`
- `created_at`
- `updated_at`
- `archived_at`

#### `runs`

保存 conversation 内的每次独立任务执行。

字段：

- `run_id`
- `conversation_id`
- `thread_id`
- `user_message_id`
- `final_message_id`
- `workflow_name`
- `status`
- `started_at`
- `ended_at`
- `error_message`

#### `messages`

保存 transcript read model。

字段：

- `message_id`
- `conversation_id`
- `run_id`
- `role`
- `phase`
- `visibility`
- `content_json`
- `text_preview`
- `created_at`

设计要点：

- transcript 不等于底层 LangGraph message state
- 前端主消息区依赖这张表

#### `run_steps`

保存 run 内部的结构化步骤。

字段：

- `step_id`
- `run_id`
- `parent_step_id`
- `step_type`
- `title`
- `status`
- `tool_name`
- `tool_call_id`
- `input_json`
- `output_json`
- `summary_text`
- `display_mode`
- `sort_order`
- `started_at`
- `ended_at`

设计要点：

- 这是执行面板的主数据源
- 历史 run 的可展开步骤来自这里

#### `artifacts`

为后续文件、报告、链接类产物预留。

当前代码已经建表，但主链路还没有大规模使用。

### 索引

当前 schema 已包含多组运行时索引，包括：

- conversation 更新时间索引
- message 的 conversation/run 维度索引
- runs 的 conversation/thread 索引
- run_steps 的 run/tool_call 维度索引
- artifacts 的 run 索引

## `langgraph_checkpoints.db`

checkpoint 数据库由：

- `agentbot/graph/checkpoints.py`

通过 `SqliteSaver` 管理。

当前行为：

- `thread_id` 是 run 级字段，不再直接等于 `conversation_id`
- runner / streaming_runner 每轮都传入当前 run 对应的 `thread_config(thread_id)`
- 如果线程已有 checkpoint，则基于 checkpoint 恢复
- 如果是迁移旧会话且尚无 checkpoint，则会先做 seed，再进入 checkpoint 模式

这张库是运行状态真相的一部分，但不是前端主 read model。

## Repository 层

SQLite 访问主要通过 repository 封装：

- `agentbot/storage/repositories/conversations.py`
- `agentbot/storage/repositories/messages.py`
- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`
- `agentbot/storage/repositories/artifacts.py`

当前 `RunRepository` 已直接提供面向前端摘要的数据：

- `step_count`
- `visible_step_count`
- `has_execution`

这样前端不需要再靠“点开以后才知道有没有步骤”去猜。

## 当前真相边界

当前推荐把数据库职责理解成：

- `agent_runtime.db`
  产品读模型与历史查询真相
- `langgraph_checkpoints.db`
  图执行状态与恢复真相

前端不直接读取 checkpoint 库。

前端显示使用的是：

- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/runs`
- `GET /api/runs/{run_id}/steps`

## 与旧 JSONL 的关系

旧 JSONL 模块仍在仓库里保留：

- `agentbot/memory/conversation.py`
- `agentbot/memory/execution.py`

但当前主聊天路径已经不再以它们作为 source of truth。

它们现在更多承担：

- 历史兼容
- 迁移过渡
- 代码保留

如果文档和代码发生冲突，应以 SQLite 主路径为准。
