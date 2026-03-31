# Streaming Chat Phase 1

## 状态

已完成。

## 阶段目标

把当前“整轮完成后一次性返回”的聊天链路升级成基于 `SSE` 的流式聊天链路，并让桌面端具备更自然的会话反馈：

- user 消息发送后立即出现在聊天区
- 输入框立即清空
- assistant 回复前有明确的等待状态
- assistant 回复过程中按文本增量持续显示
- tool 执行时显示运行中状态
- tool 结果完成后一次性显示
- 本轮结束后前端与持久化结果重新对齐

## 实际完成内容

本阶段已经完成以下能力：

- 新增流式执行入口 [agentbot/app/streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py)，用于驱动单轮流式输出
- 保留原同步 `run_once()` 链路，不影响 CLI 与原有非流式接口
- 新增流式接口 `POST /api/conversations/{conversation_id}/messages/stream`
- 流式接口通过 FastAPI `StreamingResponse` 返回 `text/event-stream`
- 前端新增基于 `fetch` 的 `SSE` 消费逻辑与事件解析
- 聊天区改成“持久化消息 + 临时 liveMessages”叠加渲染
- 发送后立即插入 optimistic user message
- 发送后立即清空输入框
- assistant 等待中、streaming 中、tool 执行中的状态都能在聊天区明确显示
- tool 结果以单次完成结果插入聊天流，不做 token 级流式拆分
- 流结束后重新拉取 conversation，保证最终 UI 与持久化结果一致

## 事件协议

本阶段已经落地的流式事件包括：

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

这些事件已经成为当前桌面端 streaming chat 主链路的协议基础。

## 前端侧结果

桌面端当前已经具备以下流式体验：

- 用户发送消息后，消息立即出现在聊天区
- assistant 尚未开始输出时，界面会显示等待回答状态
- assistant 内容按增量持续显示，而不是整段一次性出现
- 如果中途触发 tool，会先显示 tool 执行中状态
- tool 完成后会显示完整结果
- assistant 可在 tool 之后继续输出
- 本轮结束后聊天区回到服务端最终状态

## 后端侧结果

后端当前已经具备以下能力：

- 基于 LangGraph `graph.stream(...)` 的流式执行链路
- assistant 文本增量与 tool 生命周期事件的统一发射
- 流式执行结束后的 conversation 持久化提交
- conversation 结果提交完成后的最终确认事件

## 实施过程中确认的关键点

本阶段实现中已经验证并固定了几个重要结论：

- 当前桌面端主链路适合使用 `POST + SSE over fetch`
- 不需要为这一阶段引入 `WebSocket`
- 不需要让 tool 结果做 token 级流式输出
- 前端不应该只依赖服务端最终 `messages`，而应该维护临时流式状态层
- 流式链路与同步链路应并存，避免影响 CLI 与已有调用方

## 当前边界

虽然 `streaming chat phase 1` 已完成，但以下内容仍不在本阶段范围内：

- stop generation / 主动中断生成
- `WebSocket` 通道
- tool 结果的细粒度流式输出
- execution 面板联动
- 断线重连与复杂恢复机制
- 完整自动化 SSE 测试体系

## 对后续阶段的意义

这一阶段完成后，项目已经从“桌面端可以调用后端聊天”进一步升级到“桌面端具备可用的流式聊天体验”。  
这为后续继续做以下方向打下了基础：

- execution log visualization
- 更完整的 streaming 体验
- 更完整的桌面调试与设置能力

## 相关文档

- [docs/exec-detail/2026-03-31-streaming-chat-phase-1-implementation.md](/F:/AgentBot/docs/exec-detail/2026-03-31-streaming-chat-phase-1-implementation.md)
- [docs/architecture/streaming-chat.md](/F:/AgentBot/docs/architecture/streaming-chat.md)
