# Graph Flow

## 当前图结构

当前 LangGraph 主 loop 仍然保持简洁：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

关键构建文件：

- `agentbot/graph/builder.py`

## 节点职责

### `chatbot`

负责：

- 调用已绑定 tools 的 chat model
- 产出 assistant 内容
- 决定是否发起 tool calls

### `route`

负责：

- 根据 `AIMessage` 中是否存在 tool calls 决定下一步
- 无 tool calls 时结束
- 有 tool calls 时进入 `tools`

### `tools`

负责：

- 执行注册的工具
- 把工具结果回送给 graph

## 当前状态模型

当前 graph 仍然主要围绕消息状态运行，但运行时 durability 已经增强。

当前特点：

- conversation 级 `thread_id`
- SQLite checkpointer
- 共享同步/流式入口

## Checkpoint 集成

当前 graph 编译时已经接入：

- `agentbot/graph/checkpoints.py`

核心对象：

- `SqliteSaver`

当前规则：

- `conversation_id` 直接作为 `thread_id`
- 如果线程已有 checkpoint，则后续轮次从 checkpoint 恢复
- 旧 conversation 切入新架构时，必要时先做 seed

## 同步与流式的关系

两条执行路径都会复用同一个 graph：

- `runner.py`
- `streaming_runner.py`

不同点不在 graph 结构，而在：

- 如何消费事件
- 如何向前端返回
- 如何组织本轮 UI 体验

## 当前边界

当前 graph 仍然没有系统化引入：

- subgraph
- multi-agent orchestration
- long-term memory state
- 复杂 typed state machine

当前设计仍然偏向：

- 小而稳的 agent loop
- 在 graph 外层做产品级数据建模
