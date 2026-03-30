# Persistence Model

## 当前存储策略

项目当前使用 `workspace/` 下的本地文件进行持久化。

持久化分成两类：

- conversation 数据
- execution 数据

当前目录结构如下：

```text
workspace/
  conversations/
    default.json
    <conversation_id>.jsonl
  executions/
    <conversation_id>.jsonl
```

其中：

- `conversations/<conversation_id>.jsonl` 保存一个 conversation 的元数据和消息历史
- `executions/<conversation_id>.jsonl` 保存同一个 conversation 的 execution events
- `conversations/default.json` 用来标记当前 CLI 使用的默认会话对应哪个 `conversation_id`

## Conversation Storage

`agentbot/memory/conversation.py` 负责管理 conversation 持久化。

当前实现采用：

- 每个 conversation 一份独立 JSONL 文件
- 第一行是 `meta` record
- 后续每一行是 `message` record

### Conversation Meta

conversation 文件首行包含以下核心字段：

- `conversation_id`
- `name`
- `created_at`
- `updated_at`

示意结构：

```json
{
  "type": "meta",
  "conversation_id": "conv_xxx",
  "name": "default",
  "created_at": "2026-03-30T15:00:00+08:00",
  "updated_at": "2026-03-30T15:10:00+08:00"
}
```

`updated_at` 表示这个 conversation 最近一次被更新的时间。

当前会在以下场景更新：

- conversation 被写入新消息后
- conversation 被重命名后

### Message Records

conversation 文件中的消息记录继续使用一行一个 JSON object 的方式保存。

关键字段包括：

- `message_id`
- `timestamp`
- `role`
- `content`

在需要时还会包含：

- `tool_calls`
- `tool_call_id`
- `name`

`system` message 不会被持久化到 conversation 文件中。

### 当前默认会话

当前 CLI 仍然只使用一个默认会话。

这个默认会话不是通过固定的 `default.jsonl` 文件直接存储，而是通过：

```text
workspace/conversations/default.json
```

来指向某个标准 conversation。

该文件的内容很简单：

```json
{
  "conversation_id": "conv_xxx"
}
```

这样做的目的是：

- 保持当前 CLI 仍然只有一个默认会话入口
- 同时让底层 conversation 存储已经具备标准多会话模型

### Conversation Store 提供的能力

当前 `ConversationStore` 已经具备以下内部能力：

- `ensure_default_conversation()`
- `load_default_conversation()`
- `create_conversation()`
- `list_conversations()`
- `get_conversation()`
- `get_conversation_meta()`
- `rename_conversation()`
- `delete_conversation()`
- `append_message_to_conversation()`
- `replace_conversation_messages()`

这意味着虽然当前 CLI 还没有暴露会话管理命令，但 persistence 内核已经具备多会话语义。

## Execution Storage

`agentbot/memory/execution.py` 负责保存 execution events。

当前实现同样采用：

- 每个 conversation 一份独立 JSONL 文件
- 文件路径与 conversation 的 `conversation_id` 对齐

文件路径形式为：

```text
workspace/executions/<conversation_id>.jsonl
```

### Execution Meta

execution 文件的第一行是 `meta` record。

这里保存的是稳定归属信息，而不是完整的 conversation 展示元数据。

关键字段包括：

- `conversation_id`
- `created_at`

示意结构：

```json
{
  "type": "meta",
  "conversation_id": "conv_xxx",
  "created_at": "2026-03-30T15:00:00+08:00"
}
```

这样设计的意义是：

- execution 文件只负责说明“这些事件属于哪个 conversation”
- conversation 改名不会影响 execution 的归属关系

### Event Records

execution 文件的后续每一行是一个 `event` record。

关键字段包括：

- `event_id`
- `execution_id`
- `timestamp`
- `event`

在不同事件类型下，还会带有额外字段，例如：

- `message_count`
- `tools`
- `tool`
- `args`
- `output`
- `content`
- `stage`
- `error`

## Conversation 与 Execution 的关系

conversation 文件和 execution 文件通过同一个 `conversation_id` 对齐。

也就是说：

- 一个 conversation 有一份自己的消息历史文件
- 同一个 conversation 也有一份自己的 execution 事件文件

`run_once()` 每调用一次，都会生成一个新的 `execution_id`，并把这次执行过程中的事件追加到当前默认会话对应的 execution 文件中。

## 默认 CLI 运行方式

当前 CLI 不做会话切换，也不维护单独的 active state 文件。

当前行为是：

- 启动时读取 `default.json`
- 找到默认会话对应的 `conversation_id`
- 加载该 conversation 的历史消息
- 本轮执行结束后，把结果继续写回同一个 conversation 文件
- 同时把 execution events 写回对应的 execution 文件

因此，当前用户体验仍然是“一个默认会话持续对话”，但底层文件组织已经是面向多会话的结构。

## Legacy 兼容

`ConversationStore` 和 `ExecutionStore` 当前仍然保留了对旧默认文件布局的迁移兼容。

兼容范围包括：

- `workspace/conversations/default.jsonl`
- `workspace/sessions/default.jsonl`
- `workspace/executions/default.jsonl`

当系统发现这些旧文件时，会在加载默认会话或写入 execution 时把它们迁移到当前的 `conversation_id` 文件布局中。
