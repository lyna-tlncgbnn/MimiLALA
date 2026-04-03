# 2026-04-03 Run-Scoped Thread ID For Checkpoints

## Problem

浏览器任务出现了跨轮污染：

- 同一 conversation 的上一轮任务是“重庆到北京”
- 下一轮用户改成了“广州到北京”
- 浏览器 planner 却仍然输出了 “from Chongqing to Beijing”

排查后确认，问题更接近运行态隔离，而不是 prompt 本身：

- `streaming_runner.py` 和 `runner.py` 之前都把 `conversation_id` 直接作为 LangGraph `thread_id`
- 同一 conversation 的多轮 run 会共享同一条 checkpoint 线程
- 浏览器子图的状态字段会在这种 durable state 上继续累积

对于普通聊天这未必立刻出错，但对于浏览器子图这类带大量 domain state 的执行链，很容易把上一轮任务语义带进下一轮。

## Change

本次调整把 LangGraph checkpoint 隔离粒度从“conversation 级”改成了“run 级”。

### 1. `thread_id` 改为 run 级

在 [shadow_runtime.py](/F:/AgentBot/agentbot/storage/shadow_runtime.py) 中：

- 创建 run 时先生成 `run_id`
- 同时把 `thread_id` 直接写成该 `run_id`

### 2. runner / streaming runner 改用当前 run 的 thread

在 [runner.py](/F:/AgentBot/agentbot/app/runner.py) 和 [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py) 中：

- 不再使用 `conversation_id` 作为 `thread_id`
- 改为使用 `active_run.run_id`
- 每轮都从 transcript 重新构造输入消息
- 不再按 conversation 级 checkpoint 决定是否“checkpoint resume”

## Why This Fix

这样调整后：

- 每轮 run 都拥有独立的 LangGraph durable state
- 浏览器子图不会再吃到上一轮残留的 `browser_task / browser_action_history / browser_status`
- transcript 仍然按 conversation 连续保存，不会影响产品层对话历史
- run / run_steps / thread_id 的关系也更清晰

也就是说：

- conversation 负责“产品层连续对话”
- run 负责“单轮执行”
- thread_id 负责“单轮 LangGraph state”

## Validation

已完成本地验证：

- `python -m compileall agentbot`
- 代码检查确认 `RunRepository` 中写入的 `thread_id` 已改为 run 级
- `runner.py` / `streaming_runner.py` 已改为使用当前 run 的 thread config

## Notes

这次没有移除 SQLite checkpointer。

它仍然存在，只是从“按 conversation 持久恢复同一条 graph state”改成了“按 run 持久化单轮 graph state”。这更符合当前系统还没有 approval / interrupt 恢复能力的实际阶段。
