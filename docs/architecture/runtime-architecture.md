# Runtime Architecture

## 定位

AgentBot 当前已经不是单一的 CLI demo，而是一个本地桌面 Agent 应用。

主结构如下：

```text
Electron Shell
  -> React UI
    -> FastAPI Local API
      -> ChatService / ConversationService
        -> runner / streaming_runner
          -> LangGraph
            -> LLM + Tools
            -> SQLite runtime storage
            -> LangGraph SQLite checkpoints
```

## 当前设计目标

当前运行时的目标不是“把所有东西都压成消息流”，而是把不同层次的运行信息分开：

- conversation transcript
- per-run execution state
- per-run execution steps
- low-level LangGraph checkpoints

这套分层支撑了当前桌面端的两种主要体验：

1. 用户可见的稳定对话历史
2. 运行中和历史可回看的执行过程

## 核心分层

### 1. Desktop Shell

`desktop/` 提供 Electron 桌面壳：

- 启动窗口
- 加载 React 前端
- 在开发阶段协助连接本地前后端

当前桌面壳不是业务逻辑中心，更多承担宿主角色。

### 2. Frontend UI

`ui/` 是 React 前端，当前主界面采用 run-oriented 渲染模型：

- transcript 只展示用户可见消息
- active run 展示当前轮临时执行态
- historical runs 展示历史任务与可展开步骤

前端不再把 tool 调用当成普通聊天气泡直接渲染。

### 3. Local API

`agentbot/api/` 是 FastAPI 本地服务层。

它负责：

- conversation CRUD
- transcript 查询
- run 查询
- 同步发送
- 基于 `text/event-stream` 的流式运行接口

当前主接口已经是 run-oriented：

- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs/stream`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/steps`

兼容接口仍然保留：

- `POST /api/conversations/{conversation_id}/messages`
- `POST /api/conversations/{conversation_id}/messages/stream`

但它们不再是主路径。

### 4. Service Layer

当前 service 层主要有两个中心对象：

- `ConversationService`
- `ChatService`

职责分别是：

- `ConversationService`
  conversation 元数据和 transcript 读写
- `ChatService`
  把 API/CLI 语义翻译成 runner 调用和最终查询

### 5. Runtime Execution Layer

当前执行层由两个入口组成：

- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

分别对应：

- 同步单轮执行
- 流式单轮执行

两者共享同一套核心运行时能力：

- settings
- LangGraph builder
- tools registry
- SQLite runtime storage
- LangGraph checkpoints

### 6. LangGraph Layer

当前 graph 由 `agentbot/graph/builder.py` 构建，核心 loop 仍然是：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

但和早期版本不同的是：

- graph 已经挂接 SQLite checkpointer
- LangGraph `thread_id` 当前按 run 隔离，并与 `run_id` 对齐
- 同一个 conversation 的后续轮次会基于 checkpoint 恢复

### 7. Storage Layer

当前主存储已经是 SQLite，而不是 JSONL。

运行时数据分成两套数据库：

- `workspace/agent_runtime.db`
- `workspace/langgraph_checkpoints.db`

前者面向产品层 read model，后者面向 LangGraph durable execution。

## 当前对象模型

### Conversation

conversation 是长期容器，对应侧边栏里的一个会话。

它承载：

- `conversation_id`
- 标题
- created/updated 时间
- 关联 transcript
- 关联 runs

### Run

run 是 conversation 中一次独立任务执行。

它承载：

- `run_id`
- `conversation_id`
- `thread_id`
- `user_message_id`
- `final_message_id`
- `status`
- started/ended 时间

当前桌面端的“这一轮任务”就是 run。

### Run Step

run step 是 run 内部的结构化步骤，是执行面板的主要数据来源。

它承载：

- `step_id`
- `run_id`
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

### Transcript Message

message 只保留产品层需要的可见消息：

- `role`
- `phase`
- `visibility`
- `content_json`
- `text_preview`

当前 transcript 的主要角色仍然是：

- `user`
- `assistant`

tool 步骤不再作为主聊天 UI 的直接等价物。

### Checkpoint

checkpoint 由 LangGraph `SqliteSaver` 负责管理，保存线程级运行状态。

它不直接作为前端 read model，但承担：

- durable execution
- 线程恢复
- 调试和状态保真

## 当前主链路

当前桌面聊天主链路是：

1. 用户在 React 前端发送消息
2. 前端调用 `/api/conversations/{id}/runs/stream`
3. FastAPI 把请求交给 `ChatService`
4. `ChatService` 调用 `stream_once(...)`
5. `streaming_runner` 基于 LangGraph 流式运行
6. 后端通过 SSE 推送 run / step / final-answer 事件
7. 前端维护当前轮 `activeRun`
8. 运行完成后，前端回读 SQLite-backed transcript 和 runs
9. active run 退场，持久化结果接管展示

## 当前实现边界

当前系统已经具备：

- SQLite 主存储
- run / step 数据模型
- LangGraph checkpointer
- SSE 流式聊天
- 桌面前端执行面板

当前仍未覆盖：

- long-term memory
- multi-agent orchestration
- subgraph 体系化使用
- 停止生成
- 生产级 tracing backend
- 完整自动化测试矩阵

## 推荐继续阅读

- [database.md](/F:/AgentBot/docs/architecture/database.md)
- [runtime-flow.md](/F:/AgentBot/docs/architecture/runtime-flow.md)
- [streaming-chat.md](/F:/AgentBot/docs/architecture/streaming-chat.md)
- [frontend.md](/F:/AgentBot/docs/architecture/frontend.md)
