# 2026-03-30 Multi-Conversation Persistence Implementation

## 本次执行目标

本次执行基于 `docs/exec-plans/active/multi-conversation-persistence.md` 落地了 persistence 内核升级，但遵循了当前阶段的收敛边界：

- 先把底层 conversation / execution 存储改成可支撑多会话的数据模型
- 当前 CLI 仍然只使用默认会话
- 不引入 active conversation state
- 不在本轮加入 CLI 会话切换、列表、重命名、删除命令
- 不改 LangGraph graph shape

## 本次实际改动

### 1. conversation 存储层从单会话 alias 模型升级为多会话模型

修改文件：

- `agentbot/memory/conversation.py`

原先的问题：

- 代码强依赖 `alias="default"`
- conversation 文件路径固定为 `workspace/conversations/default.jsonl`
- `ConversationMeta` 只有 `conversation_id`、`name`、`created_at`
- 没有 `updated_at`
- 没有 conversation CRUD 能力

本次改动后：

- `ConversationMeta` 补充了 `updated_at`
- conversation 文件改为按 `conversation_id` 存储
- 默认文件名形式变成：
  - `workspace/conversations/<conversation_id>.jsonl`
- 默认会话不再直接绑定 `default.jsonl`
- 新增默认会话指针文件：
  - `workspace/conversations/default.json`

该指针文件只记录默认会话当前绑定到哪个 `conversation_id`，例如：

```json
{"conversation_id": "conv_xxx"}
```

### 2. conversation store 补齐内部管理能力

`ConversationStore` 本次新增或补齐了以下内部语义：

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

说明：

- 当前 CLI 虽然仍只使用默认会话
- 但 persistence 内核已经具备后续前端/API 需要的基本 conversation 对象语义

### 3. conversation 元数据结构升级

新的 conversation 文件首行 meta 记录为：

```json
{
  "type": "meta",
  "conversation_id": "conv_xxx",
  "name": "default",
  "created_at": "...",
  "updated_at": "..."
}
```

后续消息记录仍然保持一行一个 JSON object 的结构，继续包含：

- `message_id`
- `timestamp`
- `role`
- `content`
- 可选 `tool_calls`
- 可选 `tool_call_id`

### 4. execution 存储层改为按 conversation_id 对齐

修改文件：

- `agentbot/memory/execution.py`

原先的问题：

- execution 文件路径固定为 `workspace/executions/default.jsonl`
- 存储模型仍然是单会话 alias
- 文件首行 meta 直接复用了 conversation meta

本次改动后：

- execution 文件改为按 `conversation_id` 存储
- 文件路径形式变成：
  - `workspace/executions/<conversation_id>.jsonl`
- 写入接口从旧的默认单会话语义改成：
  - `append_events(meta, events)`
- execution 文件首行 meta 只保留稳定归属字段：

```json
{
  "type": "meta",
  "conversation_id": "conv_xxx",
  "created_at": "..."
}
```

这样 conversation 改名不会影响 execution 的归属关系。

### 5. runner 接入新的 persistence 接口

修改文件：

- `agentbot/app/runner.py`

本次改动：

- `runner` 不再依赖旧的 `create_default_meta()` / `save_default_conversation()`
- 默认会话读取改为走新的 `load_default_conversation()`
- conversation 保存改为走：
  - `replace_conversation_messages(meta.conversation_id, result["messages"], existing_meta=meta)`
- execution 保存改为走：
  - `append_events(meta, events)`

同时删除了一个已经失效的旧分支，避免继续引用不存在的旧接口。

## 本次迁移策略

当前工作区原始真实数据为：

- `workspace/conversations/default.jsonl`
- `workspace/executions/default.jsonl`

本次迁移逻辑在首次加载默认会话时自动触发：

1. 发现旧的 `workspace/conversations/default.jsonl`
2. 读取其中 meta，拿到原有 `conversation_id`
3. 把 conversation 文件迁移为：
   - `workspace/conversations/<conversation_id>.jsonl`
4. 生成默认会话指针文件：
   - `workspace/conversations/default.json`
5. 旧 `workspace/conversations/default.jsonl` 删除
6. execution 文件在首次追加事件时迁移为：
   - `workspace/executions/<conversation_id>.jsonl`
7. 旧 `workspace/executions/default.jsonl` 删除

## 当前实际磁盘结果

迁移完成后，当前默认会话相关数据已经变成：

```text
workspace/
  conversations/
    conv_73ccc2abc33146c08551c3a5bd6e7dee.jsonl
    default.json
  executions/
    conv_73ccc2abc33146c08551c3a5bd6e7dee.jsonl
```

其中：

- `default.json` 记录默认会话绑定到哪个 `conversation_id`
- conversation 和 execution 现在通过同一个 `conversation_id` 一一对齐

## 本次验证

### 1. 代码编译验证

运行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果通过。

### 2. 默认会话迁移验证

通过脚本调用 `ConversationStore().load_default_conversation()` 后确认：

- 旧 `default.jsonl` conversation 文件已迁移
- 新的 `<conversation_id>.jsonl` conversation 文件已生成
- `default.json` 默认会话指针已生成

### 3. conversation CRUD 验证

通过脚本验证了以下能力：

- `create_conversation()`
- `rename_conversation()`
- `append_message_to_conversation()`
- `list_conversations()`
- `delete_conversation()`

说明：

- persistence 内核的多会话操作语义已经具备
- 当前只是还没有在 CLI 层暴露这些能力

### 4. execution 迁移验证

通过脚本向默认会话追加测试 execution event 后确认：

- execution 文件已迁移到 `<conversation_id>.jsonl`
- 旧 `workspace/executions/default.jsonl` 已删除

### 5. runner 链路验证

通过脚本调用 `run_once("ping")` 验证：

- conversation 加载成功
- 新工具列表能正常注册
- graph 可以正常开始执行

最终失败点仍然是模型连接错误：

- `Model execution failed: Connection error.`

这说明：

- 本次 persistence 改动没有破坏 runner 主链路
- 当前失败来自模型连接，而不是 conversation / execution 存储接口

## 当前边界

本次执行明确没有做以下内容：

- 没有引入 active conversation state 文件
- 没有给 CLI 增加会话选择、切换、列表命令
- 没有引入前端/API 层会话管理接口
- 没有引入 checkpointer
- 没有把 conversation persistence 改成数据库

## 当前结果

截至本次执行结束，项目已经具备：

- conversation 按 `conversation_id` 独立存储
- execution 按 `conversation_id` 独立存储
- 默认会话通过指针文件绑定到一个标准 conversation object
- conversation 元数据具备 `updated_at`
- 多会话 CRUD 能力已经作为内部 persistence 能力存在
- 当前 CLI 仍然保持“只使用默认会话”的简单体验

## 给 plan agent 的后续建议

如果后续要总结归档，建议 plan agent 重点关注：

1. 计划文档里原本提到的 “active conversation” 是否在当前阶段被明确延期
2. 当前实现采用的是“默认会话指针文件”，不是 active state 方案
3. 当前多会话能力已在 persistence 内核具备，但尚未在 CLI 层暴露
4. 后续如果进入前端/API 阶段，可以直接基于现有 `ConversationStore` 内部语义继续扩展
