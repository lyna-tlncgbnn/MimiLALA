# Persistence Model

## 当前存储策略

项目当前使用 `workspace/` 下的本地 JSONL 文件进行持久化。

```text
workspace/
  conversations/
    default.jsonl
  executions/
    default.jsonl
```

## Conversation Storage

`agentbot/memory/conversation.py` 把一个命名 conversation 文件写成：

- 第一行一个 `meta` record
- 后续每一行一个 `message` record

关键字段包括：

- `conversation_id`
- `name`
- `created_at`
- `message_id`
- `timestamp`

`system` message 不会被持久化。

## Execution Storage

`agentbot/memory/execution.py` 会把 execution events 存在并行文件中：

- 第一行仍然是同一 conversation 的 `meta` record
- 后续每一行是一个 `event` record

关键字段包括：

- `event_id`
- `execution_id`
- `timestamp`
- `event`

## 两个文件之间的关系

conversation 文件与 execution 文件通过同一个 `conversation_id` 对齐。

每调用一次 `run_once()`，都会生成一个新的 `execution_id`。

## Legacy 兼容

`ConversationStore` 目前仍然保留了对旧 `workspace/sessions/default.jsonl` 格式的 fallback reader，但新的写入路径已经是 `workspace/conversations/default.jsonl`。
