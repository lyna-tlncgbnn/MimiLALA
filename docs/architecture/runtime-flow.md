# Runtime Flow

## 目标

本文件描述当前代码里从桌面前端到 LangGraph 再到持久化的主链路。

它不是产品说明，而是运行链路说明。

## 同步主链路

同步链路主要用于：

- CLI
- 同步 API

路径如下：

```text
CLI / POST /runs
  -> ChatService.send_run_to_conversation()
    -> run_once(...)
      -> build_graph(...)
      -> graph.stream(...)
      -> tools / LLM / checkpoints
      -> persist transcript / run / steps
    -> read back conversation + latest run
```

关键文件：

- `agentbot/app/runner.py`
- `agentbot/services/chat.py`
- `agentbot/api/routes/conversations.py`

## 流式主链路

当前桌面端主聊天体验主要走流式链路：

```text
React UI
  -> POST /api/conversations/{conversation_id}/runs/stream
    -> FastAPI StreamingResponse
      -> ChatService.stream_message_to_conversation()
        -> stream_once(...)
          -> LangGraph graph.stream(...)
            -> LLM + ToolNode + checkpoints
          -> translate runtime events to SSE
      -> browser fetch + stream reader
        -> activeRun state
        -> query refetch
        -> persisted transcript/runs take over
```

关键文件：

- `ui/src/shared/api/api.ts`
- `ui/src/app/app-shell.tsx`
- `agentbot/api/routes/conversations.py`
- `agentbot/services/chat.py`
- `agentbot/app/streaming_runner.py`

## 前端阶段

一次流式发送的大致前端阶段是：

1. 用户提交 draft
2. 前端决定目标 conversation
3. 如果没有 active conversation，则先创建 conversation
4. 前端创建临时 `activeRun`
5. 前端开始读取 SSE
6. `run_started` 到达后，补齐真实 `run_id`
7. `step_started / step_completed` 更新执行步骤
8. `assistant_final_delta` 逐步拼正文
9. `assistant_finalized / run_completed` 到达后完成本轮
10. invalidate / refetch conversation 与 runs
11. persisted transcript 与 historical runs 接管显示

## SSE 语义

当前主事件是：

- `run_started`
- `step_started`
- `step_completed`
- `assistant_final_delta`
- `assistant_finalized`
- `run_completed`
- `run_failed`
- `done`

这意味着当前 UI 已经不再依赖旧的：

- `assistant_waiting`
- `tool_started`
- `tool_finished`

那套 message-centric 协议。

## LangGraph 执行阶段

当前 graph 仍以 chatbot/tool loop 为主，但已经开始接入 specialist subgraph：

1. runner 构建输入
2. graph 先经过 intent 判断节点
3. 如果识别为浏览器任务，则进入 `browser_subgraph`
4. 否则进入 `chatbot` 节点调用已绑定 tools 的 LLM
5. route 判断是否转入 `tools`
6. `ToolNode` 执行
7. 工具结果送回 `chatbot`
8. 当模型不再发出 tool call 时结束

当前 `browser_subgraph` 已经完成最小真实浏览器交互闭环，当前主要支持：

- Playwright 驱动 Chromium 会话
- 真实页面导航与读取
- 页面标题、主文本、链接、表单控件摘要
- 页面截图输出到 `workspace/browser_artifacts/`
- 子图内部 `observe -> decide -> act -> evaluate -> observe/finish` 循环
- 基础交互动作：`click / type / scroll / wait / go_back / switch_tab`
- browser 执行步骤实时写入 `run_steps`
- browser screenshot / page summary artifacts 落入统一 `artifacts`
- 轻量 loop detection 提示重复动作与页面停滞
- 敏感动作会先收口为 `approval_required`，为后续 approval / interrupt UI 预留边界

它当前仍然不是完整 browser automation framework，现阶段主要用于打通：

- 子图接入主图
- browser 执行步骤落库
- execution timeline 可见性
- 真实页面读取能力

后续阶段再继续补真实交互动作。

当前 run 相关 API 还额外支持：

- `GET /api/runs/{run_id}/steps`
- `GET /api/runs/{run_id}/artifacts`

和早期阶段不同的是，当前执行会附带：

- SQLite runtime storage
- LangGraph checkpoint persistence

## 持久化阶段

当前一次 run 结束后，最终会稳定落到两套存储：

### 产品层数据库

落到 `agent_runtime.db`：

- conversation metadata
- user message
- assistant final message
- run
- run steps

### LangGraph checkpoint 库

落到 `langgraph_checkpoints.db`：

- thread state
- checkpoint snapshots

## 当前前端显示模型

前端不是直接把所有消息平铺出来，而是：

### transcript

来自 persisted `messages`

### active run

来自当前 SSE 事件和本地状态

### historical runs

来自 persisted `runs`

### historical run steps

来自 persisted `run_steps`

这个模型的好处是：

- 运行中的过程可见
- 历史对话保持干净
- 工具过程不会污染 transcript 主消息区

## 失败和对账

当前流式链路已经把“传输错误”和“业务终态”分开处理：

- SSE 用于实时体验
- SQLite persisted run 用于最终真相

所以流式收尾阶段即使有 transport error，前端最终仍会回读：

- conversation
- runs

由持久化结果做最后裁决，而不是单纯把 transport error 当成 run failure。

## 推荐结合阅读

- [runtime-architecture.md](/F:/AgentBot/docs/architecture/runtime-architecture.md)
- [database.md](/F:/AgentBot/docs/architecture/database.md)
- [streaming-chat.md](/F:/AgentBot/docs/architecture/streaming-chat.md)
