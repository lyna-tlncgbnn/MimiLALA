# 2026-03-31 Streaming Chat Phase 1 Implementation

## 本次执行目标

本次执行围绕 `docs/exec-plans/active/streaming-chat-phase-1.md` 落地聊天主链路的第一阶段流式化改造，目标是：

- 保留现有同步 `POST /api/conversations/{conversation_id}/messages`
- 新增流式聊天主入口
- 让前端发送后立刻显示 user 消息并清空输入框
- 让 assistant 支持 waiting / streaming 状态
- 让 tool 执行过程在聊天流中可见
- 在流结束后重新与最终 persistence 状态对齐

本次实现继续遵守当前项目边界：

- 不改 conversation persistence 模型
- 不改 execution persistence 模型
- 不引入 WebSocket
- 不做 tool output 的 token 级流式输出
- 不改 CLI 主链路

## 本次实际改动

### 1. 新增后端 streaming runner

新增文件：

- `agentbot/app/streaming_runner.py`

职责：

- 复用现有 `Settings`、`build_graph()`、`ConversationStore`、`ExecutionStore`
- 加载指定 conversation 历史
- 通过 LangGraph `graph.stream(..., stream_mode=["messages", "updates", "values"], version="v2")` 驱动单轮执行
- 将 LangGraph 流事件转换为前端可消费的 UI 事件
- 在执行结束后持久化最终 conversation
- 追加 execution events

本次固定输出的流式事件包括：

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

### 2. 新增流式聊天 API

修改文件：

- `agentbot/api/routes/conversations.py`
- `agentbot/services/chat.py`

新增接口：

- `POST /api/conversations/{conversation_id}/messages/stream`

实现方式：

- 返回 `text/event-stream`
- 使用 FastAPI `StreamingResponse`
- 每个事件都输出为标准 SSE 片段：

```text
event: <event_name>
data: <json>
```

同时保留原有同步接口，保证旧链路兼容。

### 3. LLM 工厂补充 streaming 开关

修改文件：

- `agentbot/models/llm.py`

本次改动：

- `build_llm(settings)` 升级为 `build_llm(settings, streaming=False)`
- streaming runner 调用时显式传入 `streaming=True`
- 原有同步 runner 继续走默认值，不受影响

### 4. 前端新增 POST + SSE over fetch 流式接入

修改文件：

- `ui/src/lib/api.ts`

新增内容：

- `ChatStreamEvent` 联合类型
- `streamMessage(conversationId, content, onEvent)`
- 手写 SSE parser

这里本次明确采用的是：

- `fetch(POST /messages/stream)` + 手动解析 `text/event-stream`

而不是浏览器原生 `EventSource`，因为本次主链路是 POST 请求而不是 GET。

### 5. 前端聊天区改为“持久化消息 + 当前轮临时消息”

修改文件：

- `ui/src/components/layout/app-shell.tsx`

本次改动：

- 不再只渲染 `conversationQuery.data.messages`
- 新增 `liveMessages`
- 最终显示数据为：
  - `persisted messages + liveMessages`

当前轮临时消息包括：

- optimistic user message
- waiting assistant message
- streaming assistant message
- tool running / tool finished message

前端状态上引入了更明确的 phase：

- `idle`
- `waiting_assistant`
- `assistant_streaming`
- `tool_running`
- `completed`
- `failed`

### 6. 本次流式 UI 的实际行为

当前前端行为已经改为：

1. 用户发送后，user 消息立即进入聊天流
2. 输入框立即清空
3. assistant 先进入 waiting 状态
4. 一旦收到首个 delta，assistant 切换为真实 streaming 输出
5. tool 开始时插入 tool 状态消息
6. tool 完成后把该条 tool 消息更新为完整结果
7. 整轮结束后重新拉取 conversation，覆盖临时 UI 状态

### 7. 与此前消息 UI 改造保持兼容

当前流式实现延续了前面已经完成的聊天消息 UI：

- assistant/tool/user 共用 `MessageCard`
- assistant 里的 `tool_calls` 仍可显示
- 消息标题旁仍显示时间
- tool card 的长内容折叠逻辑仍保留

## 本次实际踩到并修复的问题

### 1. LangGraph v2 streaming 事件形状与初始假设不一致

最初按 `(mode, payload)` tuple 处理流事件，但当前 LangGraph `version="v2"` 至少会返回如下结构：

```python
{
  "type": "values",
  "ns": (),
  "data": {...}
}
```

因此最初没有正确拿到最终 `values.messages`，会报：

- `Streaming run did not produce a final message state.`

后续已在 `streaming_runner.py` 中补充 `_normalize_stream_chunk()`，兼容：

- tuple 形状
- `{"type": ..., "data": ...}` 字典形状

### 2. tool_finished 事件字段读取错误

后端最初错误地把事件当成平铺结构读取，写成：

- `event["tool_output"]`
- `event["tool_name"]`

但本项目 SSE 事件统一结构实际是：

- `event["event"]`
- `event["data"]`

因此在 tool 执行完成时会触发：

- `Graph execution failed: 'tool_output'`

后续已改为从 `event["data"]["tool_output"]` 等路径取值。

## 本次验证

### 1. Python 导入验证

验证过：

```powershell
.\.venv\Scripts\python.exe - <<'PY'
import agentbot.api.app
import agentbot.app.streaming_runner
print("python-import-ok")
PY
```

结果通过，说明新增 streaming runner 与 API 路由至少在导入层面没有破坏后端结构。

### 2. 前端构建验证

运行：

```powershell
npm run build
```

工作目录：

- `F:\AgentBot\ui`

结果通过，说明：

- `streamMessage()` 类型与解析逻辑可通过编译
- `AppShell` 的 live message overlay 逻辑可通过编译
- 当前聊天 UI 组件树未被本次 streaming 改造打坏

### 3. 实际联调验证

本次在真实 UI 联调过程中确认并修复了两类实际错误：

- `Streaming run did not produce a final message state.`
- `Graph execution failed: 'tool_output'`

修复后，用户确认当前链路已可以继续工作。

## 当前限制

本次执行仍然保持以下边界：

- 仍未引入真正的停止生成能力
- 未引入 WebSocket
- 未做 tool output token streaming
- 未做复杂的中断恢复机制
- 未把 streaming 状态与 execution 可视化面板联动
- 未补系统化自动化测试

另外，当前 front-end tool running 文案仍然是较轻量的占位展示，后续可以继续优化视觉表达。

## 当前结果

截至本次执行结束，项目已经具备：

- 同步聊天接口
- 流式聊天接口
- optimistic user message
- assistant waiting 状态
- assistant streaming 输出
- tool started / tool finished 聊天流展示
- 流结束后与最终 conversation persistence 重新对齐

也就是说，桌面聊天主链路已经从“整轮阻塞返回”推进到了“可见的流式对话链路”。

## 建议给后续阶段的动作

如果后续继续推进，建议优先处理：

1. 把 waiting / tool running 的视觉样式做得更明确
2. 为 streaming SSE 事件补最小自动化测试
3. 评估是否要加入 stop generation
4. 评估是否要把 execution log 与 streaming UI 联动
5. 在文档中补一份专门的事件协议说明，减少后续维护成本
