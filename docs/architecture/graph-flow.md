# Graph Flow

## 当前 graph 结构

当前 graph 在 `agentbot/graph/builder.py` 中组装，整体形状如下：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

其中 `route` 这一步是通过 `add_conditional_edges()` 和 `tools_condition()` 实现的。

## graph 在整体架构中的位置

graph 仍然是当前 Agent 核心执行层，CLI、FastAPI 和桌面端都会复用这套 LangGraph 执行逻辑。

区别只在于入口不同：

- CLI 通过 `agentbot/app/cli.py` -> `agentbot/app/runner.py`
- 非流式 API 通过 `agentbot/api/` -> `agentbot/services/` -> `agentbot/app/runner.py`
- 流式聊天 API 通过 `agentbot/api/` -> `agentbot/services/` -> `agentbot/app/streaming_runner.py`

也就是说，桌面端与 FastAPI 并没有替代 graph，而是把 graph 包在新的服务入口后面。

## 同步执行流程

1. `agentbot/app/runner.py` 构造输入消息列表，内容包括：
   - system prompt
   - 已保存的 conversation history
   - 当前用户输入
2. `chatbot` 节点调用已经绑定 tools 的 chat model。
3. `route_after_chatbot` 判断 AIMessage 是否发出了 tool calls。
4. 如果存在 tool calls，则由 `tools` 节点通过 `ToolNode` 执行。
5. 工具执行结果重新送回 `chatbot`。
6. 当模型不再发出 tool calls 时，graph 结束，并返回最终 AIMessage。
7. runner 将最新消息写回 conversation storage，并将执行事件写回 execution storage。

## 流式执行流程

在 streaming chat 主链路中，不再走“整轮结束后一次性返回”的模式，而是走 streaming runner：

1. 前端调用 `POST /api/conversations/{conversation_id}/messages/stream`
2. FastAPI 把请求交给 chat service
3. chat service 调用 `agentbot/app/streaming_runner.py`
4. streaming runner 基于 LangGraph `graph.stream(...)` 消费流式事件
5. assistant 文本增量、tool 生命周期状态与最终提交事件持续通过 `SSE` 发给前端
6. 流结束后 conversation 仍会按现有 persistence 模型落盘
7. 前端重新拉取最终 conversation，完成和持久化结果的对齐

## 当前 state model

当前 graph 仍然直接使用 `MessagesState`。

这意味着：

- 当前主状态仍然围绕消息列表组织
- 还没有引入自定义 typed state
- conversation 切换、多会话 persistence 和 API 增强仍然发生在 graph 外层，而不是 state 结构内部

## 当前限制

- 没有 checkpointer
- 没有 subgraph
- 除 `messages` 外没有额外的自定义 state 字段
- 流式能力当前只覆盖聊天主链路，不包含 execution 可视化联动
