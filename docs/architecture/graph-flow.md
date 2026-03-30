# Graph Flow

## 当前 graph 结构

当前 graph 在 `agentbot/graph/builder.py` 中组装，整体形状如下：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

其中 `route` 这一步实际上是通过 `add_conditional_edges()` 和 `tools_condition()` 实现的。

## 执行流程

1. `agentbot/app/runner.py` 会先构造输入消息列表，内容包括：
   - system prompt
   - 已保存的 conversation history
   - 当前用户输入
2. `chatbot` 节点调用已经绑定 tools 的 chat model。
3. `route_after_chatbot` 判断 AIMessage 是否发出了 tool calls。
4. 如果存在 tool calls，则由 `tools` 节点通过 `ToolNode` 执行。
5. 工具执行结果会重新送回 `chatbot`。
6. 当模型不再发出 tool calls 时，graph 结束，并返回最终 AIMessage。

## 当前 state model

当前 graph 直接使用 `MessagesState`。

这样可以让当前学习阶段保持简单，但也意味着还没有引入自定义 typed state 来承载更多控制数据。

## 当前限制

- 没有 checkpointer
- 没有 subgraph
- 除 `messages` 外没有额外的自定义 state 字段
- 没有 streaming
