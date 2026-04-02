# Streaming Chat

## 当前形态

当前桌面聊天主链路已经是 run-oriented SSE，而不是早期的 message-centric streaming。

主入口：

- `POST /api/conversations/{conversation_id}/runs/stream`

兼容入口：

- `POST /api/conversations/{conversation_id}/messages/stream`

## 事件模型

当前前端消费的核心事件是：

- `run_started`
- `step_started`
- `step_completed`
- `assistant_final_delta`
- `assistant_finalized`
- `run_completed`
- `run_failed`
- `done`

这套协议把：

- run 生命周期
- step 生命周期
- 最终回答正文流式输出

分开表达。

## 为什么不是 WebSocket

当前实现使用：

- `fetch()`
- `ReadableStream`
- `text/event-stream`

而不是 WebSocket。

原因是：

- 当前模型是 request/response 型单轮发送
- POST + SSE 已足够表达“发一轮消息并持续接收事件”
- 实现复杂度更低

## 当前前端模型

前端不会把所有流式事件直接压成消息列表。

当前渲染模型是：

- persisted transcript
- active run
- historical runs

其中：

- `assistant_final_delta` 只驱动当前轮正文
- `step_started / step_completed` 只驱动执行区

## 当前对账规则

流式链路不能把 SSE 当成最终真相。

当前规则是：

- SSE 负责实时体验
- SQLite persisted transcript / runs 负责最终真相
- 结束后前端会重新拉取 conversation 与 runs

因此 transport 层异常不应自动等价于最终业务失败。

## 关键文件

- `ui/src/shared/api/api.ts`
- `ui/src/app/app-shell.tsx`
- `agentbot/api/routes/conversations.py`
- `agentbot/app/streaming_runner.py`
- `agentbot/services/chat.py`

## 当前限制

当前仍未覆盖：

- stop generation
- token 级 tool output streaming
- 多路并行 stream 协议
- 浏览器/服务端断线恢复
- 体系化流式自动化测试
