# Streaming Chat

## 当前目标

当前流式聊天链路的目标不是一次性重写整个聊天系统，而是在保留现有：

- LangGraph graph shape
- conversation persistence
- execution persistence
- 同步聊天接口

的前提下，把桌面聊天主链路从“整轮阻塞返回”升级为“前端可见的流式执行过程”。

这一层当前主要解决的是：

- user 消息发送后立刻进入聊天流
- assistant 有明确 waiting 状态
- assistant 文本逐步流式出现
- tool 执行过程在聊天流中可见
- 流结束后前端与最终持久化结果重新对齐

## 整体位置

当前 streaming chat 仍然处于既有分层中，没有引入新的系统级通道。

整体链路如下：

```text
React UI
  -> POST /api/conversations/{conversation_id}/messages/stream
    -> FastAPI StreamingResponse (text/event-stream)
      -> ChatService.stream_message_to_conversation()
        -> streaming_runner.stream_once()
          -> LangGraph graph.stream(...)
            -> LLM / Tools / Conversation Persistence / Execution Persistence
```

与同步链路的关系是：

- 同步链路继续走 `run_once()`
- 流式链路新增 `stream_once()`
- 两者复用同一套 graph、tools、conversation storage、execution storage

## 为什么采用 POST + SSE over fetch

当前流式聊天入口固定为：

- `POST /api/conversations/{conversation_id}/messages/stream`

返回类型固定为：

- `text/event-stream`

前端没有使用浏览器原生 `EventSource`，而是采用：

- `fetch()`
- `ReadableStream.getReader()`
- 手动解析 SSE 事件片段

原因是：

1. 当前发送消息本身是一个 POST 语义，而不是单纯订阅
2. 浏览器原生 `EventSource` 更适合 GET 订阅
3. 当前本地 FastAPI + React 场景下，`fetch + SSE parser` 足够简单，且不需要引入 WebSocket

因此，这里的“流式聊天”本质上是：

- 请求语义使用 POST
- 响应体格式使用 SSE
- 前端以流式字节读取的方式消费 SSE

## 后端执行模型

### 1. 保留同步 runner

同步执行仍然由：

- `agentbot/app/runner.py`

负责。

它继续服务于：

- CLI
- 原有同步 `POST /messages`

### 2. 新增 streaming runner

流式执行单独由：

- `agentbot/app/streaming_runner.py`

负责。

它的职责是：

1. 加载 settings
2. 构建支持 streaming 的 chat model
3. 加载指定 conversation 历史
4. 构造 `SystemMessage + history + HumanMessage`
5. 调用 `graph.stream(...)`
6. 把 LangGraph 流事件翻译成 UI 事件
7. 在结束时持久化最终 conversation
8. 追加 execution events

### 3. graph 本身没有改形状

流式聊天没有改变当前 graph 结构，仍然是：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

也就是说，本次流式化改变的是：

- 执行结果如何返回
- 前端如何消费执行过程

而不是：

- graph 节点结构
- route 逻辑
- persistence 模型

## LangGraph 流事件与内部转换

当前 streaming runner 使用：

- `graph.stream(..., stream_mode=["messages", "updates", "values"], version="v2")`

这里三个模式分别承担不同职责：

### `messages`

用于获取 assistant 的 token / text delta。

当前用途：

- 触发 `assistant_message_started`
- 持续触发 `assistant_delta`

### `updates`

用于获取节点更新后的消息对象。

当前用途：

- 当 `chatbot` 产出带 `tool_calls` 的 `AIMessage` 时，转换成 `tool_started`
- 当 `tools` 产出 `ToolMessage` 时，转换成 `tool_finished`

### `values`

用于获取执行过程中的完整 state。

当前用途：

- 在流式执行结束后拿到最终 authoritative `messages`
- 用这些最终消息写回 conversation persistence

### v2 事件形状说明

当前 LangGraph `version="v2"` 下，多模式 streaming 事件不总是简单 tuple。

至少会出现如下结构：

```python
{
  "type": "values",
  "ns": (),
  "data": {...}
}
```

因此 streaming runner 当前专门有一层规范化逻辑，把流事件统一转换成：

- `event_type`
- `payload`

然后再进入项目自己的事件映射逻辑。

## SSE 事件协议

当前后端对前端固定输出以下事件：

- `user_message_accepted`
- `assistant_waiting`
- `assistant_message_started`
- `assistant_delta`
- `tool_started`
- `tool_finished`
- `assistant_completed`
- `conversation_committed`
- `error`
- `done`

### `user_message_accepted`

表示当前 user 输入已被后端正式接受。

主要字段：

- `conversation_id`
- `message_id`
- `timestamp`
- `content`

前端用途：

- 把 optimistic user message 更新为正式 message_id / timestamp

### `assistant_waiting`

表示进入模型处理阶段，但还没有可展示的 assistant 文本。

前端用途：

- 在聊天流里显示 waiting assistant 占位

### `assistant_message_started`

表示 assistant 真正开始输出。

主要字段：

- `message_id`
- `timestamp`

前端用途：

- 把 waiting assistant 占位切换成真实 assistant streaming message

### `assistant_delta`

表示 assistant 文本增量。

主要字段：

- `message_id`
- `delta`

前端用途：

- 将 delta 追加到当前 assistant message.content

### `tool_started`

表示某个 tool call 已开始执行。

主要字段：

- `tool_call_id`
- `tool_name`
- `args`
- `timestamp`

前端用途：

- 在聊天流里插入 tool 运行状态消息

### `tool_finished`

表示某个 tool 已返回完整结果。

主要字段：

- `tool_call_id`
- `tool_name`
- `tool_output`
- `timestamp`

前端用途：

- 把对应 tool 运行状态消息更新为正式 tool 输出消息

### `assistant_completed`

表示当前轮 assistant 输出结束。

主要字段：

- `message_id`
- `timestamp`
- `content`

前端用途：

- 用最终完整内容收敛 streaming assistant message

### `conversation_committed`

表示最终 conversation 已完成持久化。

主要字段：

- `conversation_id`

前端用途：

- 知道此时可以通过 refetch 重新拿 authoritative conversation

### `error`

表示本轮流式执行失败。

主要字段：

- `message`

前端用途：

- 显示用户可见错误
- 将当前流式状态切换为失败

### `done`

表示 SSE 流本身正常结束。

## 前端状态模型

### 1. 现有数据源不再只依赖 persisted messages

当前聊天区不再只渲染：

- `conversationQuery.data.messages`

而是改成：

- persisted messages
- 当前轮 `liveMessages`

最终展示数据为：

```text
displayedMessages = persistedMessages + liveMessages
```

### 2. 当前轮临时消息

`liveMessages` 当前承接：

- optimistic user message
- waiting assistant message
- streaming assistant message
- tool running / finished message

这些消息只存在于当前前端渲染周期，不直接作为最终持久化结果。

### 3. 前端 phase

当前前端引入了明确的 streaming phase：

- `idle`
- `waiting_assistant`
- `assistant_streaming`
- `tool_running`
- `completed`
- `failed`

这比旧的单一 `isSending` 更适合表达聊天流中的阶段变化。

## 流结束后的最终同步

当前设计明确要求：

- streaming 期间的 UI 消息只是临时态
- 最终 authoritative 状态仍然来自服务端持久化后的 conversation

因此当前链路在流结束后总会：

1. `invalidateQueries(["conversation", conversationId])`
2. `invalidateQueries(["conversations"])`
3. 清空 `liveMessages`
4. 让前端重新以服务端 conversation 结果为准

这一步可以避免：

- 前端本地拼装消息与真实持久化结果不一致
- assistant/tool message_id、timestamp、tool_calls 等字段漂移

## 失败处理

当前流式聊天对失败的处理原则是：

- 尽量保留用户已经看到的过程
- 给出明确错误
- 不做自动重试

大致分为三类：

### assistant 尚未开始输出前失败

- user 消息已保留
- waiting assistant 状态结束
- 前端显示错误消息

### assistant streaming 中失败

- 已输出的 assistant 文本保留
- 前端显示错误消息

### tool 执行阶段失败

- 当前轮进入失败状态
- tool 运行消息不会再继续推进
- 前端显示错误消息

## 当前限制

当前 streaming chat 架构仍然有明确边界：

- 没有 stop generation
- 没有 WebSocket
- 没有 tool result 的 token 级 streaming
- 没有 execution panel 联动
- 没有复杂的断线恢复
- 没有系统化自动化测试覆盖整条 SSE 链路

此外，当前 tool running 的前端展示仍然是轻量消息态，而不是更复杂的执行可视化。

## 与其他文档的关系

Streaming chat 是建立在以下结构之上的：

- `graph-flow.md`
- `frontend.md`
- `persistence.md`

其中：

- `graph-flow.md` 说明 graph 本身如何执行
- `frontend.md` 说明前端页面与数据分层
- 本文说明“如何把 graph 执行过程转成前端可消费的流式聊天体验”
