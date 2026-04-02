# Persistence

当前主持久化已经不是 JSONL，而是 SQLite。

请优先阅读：

- [database.md](/F:/AgentBot/docs/architecture/database.md)
- [runtime-architecture.md](/F:/AgentBot/docs/architecture/runtime-architecture.md)

## 当前事实

主存储文件：

- `workspace/agent_runtime.db`
- `workspace/langgraph_checkpoints.db`

当前产品层主数据对象：

- conversations
- messages
- runs
- run_steps
- artifacts

当前图执行持久化：

- LangGraph `SqliteSaver`

## 为什么本文件保留

本文件保留是为了兼容旧引用，因为仓库里很多执行记录仍然使用 “persistence” 这个名称。

但如果你要理解当前实现，请不要再把：

- `workspace/conversations/*.jsonl`
- `workspace/executions/*.jsonl`

当成主路径。

## 旧实现状态

旧 JSONL persistence 模块仍然存在于仓库：

- `agentbot/memory/conversation.py`
- `agentbot/memory/execution.py`

当前它们不再代表主聊天链路的 source of truth。
