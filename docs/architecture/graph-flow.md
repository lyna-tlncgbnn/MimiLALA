# Graph Flow

## 当前 graph 结构

当前 graph 在 `agentbot/graph/builder.py` 中组装，整体形状如下：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

其中 `route` 这一步是通过 `add_conditional_edges()` 和 `tools_condition()` 实现的。

## graph 在整体架构中的位置

graph 仍然是当前 Agent 核心执行层，CLI 和桌面端最终都会复用这套执行逻辑。

区别只在于入口不同：

- CLI 通过 `agentbot/app/cli.py` -> `agentbot/app/runner.py`
- 桌面端通过 `agentbot/api/` -> `agentbot/services/` -> `agentbot/app/runner.py`

也就是说，桌面端和 FastAPI 并没有替代 graph，而是把 graph 包在新的服务入口后面。

## 执行流程

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

## 当前 state model

当前 graph 仍然直接使用 `MessagesState`。

这意味着：

- 目前主状态仍然围绕消息列表组织
- 还没有引入自定义 typed state
- conversation 切换与 API 入口增强发生在 graph 外层，而不是 state 结构内部

## 当前限制

- 没有 checkpointer
- 没有 subgraph
- 除 `messages` 外没有额外的自定义 state 字段
- 没有 streaming
