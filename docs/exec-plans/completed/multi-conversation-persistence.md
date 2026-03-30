# 已完成计划：Multi-Conversation Persistence

## 状态

DONE

## 原计划目标

这一阶段原本计划把项目从“默认单会话持久化”升级为“多会话持久化”，并为后续前端与 API 打下 conversation 数据模型基础。

计划重点包括：

- 支持多个 conversation
- 补齐 conversation 元数据
- 补齐 conversation 管理能力
- 保持 execution 与 conversation 的稳定关联

## 实际完成情况

根据执行总结 `docs/exec-detail/2026-03-30-multi-conversation-persistence-implementation.md`，这一阶段已经完成了 persistence 内核升级，并把底层数据模型从单默认会话推进到了多会话模型。

### 1. conversation 存储已经升级为多会话模型

当前 conversation 存储已经不再固定绑定 `default.jsonl`，而是改为按 `conversation_id` 独立存储。

当前结果包括：

- 每个 conversation 按独立 `conversation_id` 存储
- conversation 文件路径改为 `workspace/conversations/<conversation_id>.jsonl`
- conversation meta 中补齐了 `updated_at`
- 默认会话通过单独的指针文件维护，而不是继续直接绑定固定文件

### 2. conversation persistence 内核已经具备多会话管理语义

执行总结明确说明，`ConversationStore` 已经补齐了多会话 persistence 所需的核心内部能力，包括：

- `create_conversation`
- `list_conversations`
- `get_conversation`
- `get_conversation_meta`
- `rename_conversation`
- `delete_conversation`
- `append_message_to_conversation`
- `replace_conversation_messages`

这说明：

- 多会话 CRUD 语义已经在 persistence 层成立
- 后续前端或 API 可以直接建立在这套内部语义之上

### 3. execution 存储已经与 conversation_id 对齐

execution 存储也已经从默认单会话文件模型升级为按 `conversation_id` 独立存储。

当前结果包括：

- execution 文件路径改为 `workspace/executions/<conversation_id>.jsonl`
- conversation 与 execution 继续通过同一个 `conversation_id` 对齐
- conversation 改名不会破坏 execution 的归属关系

### 4. runner 已接入新的 persistence 接口

执行总结说明，当前 runner 已经改为使用新的 conversation / execution persistence 接口。

这意味着：

- 当前 CLI 主流程已经建立在新 persistence 模型之上
- 本次升级没有要求重做 LangGraph loop

## 本阶段没有完成的内容

这一点需要明确记录，避免后续误判阶段完成度。

根据执行总结，本阶段**没有**完成以下内容：

- 没有引入 active conversation state 文件
- 没有在 CLI 层增加会话切换、列出、重命名、删除命令
- 没有提供前端/API 层的会话管理接口
- 没有引入 checkpointer

也就是说，这一阶段完成的是：

- 多会话 persistence 内核

而不是：

- 完整的用户层多会话交互体验

## 如何理解这次阶段完成

从计划管理角度，这一阶段可以视为已完成，因为最关键的目标已经实现：

- conversation 数据模型已经不再被单默认会话绑定
- persistence 层已经具备多会话管理能力
- execution 与 conversation 的对齐关系仍然成立
- 后续前端与 API 已经有了可以复用的底层语义

同时，也需要承认这次完成方式是“先完成 persistence 内核，再把用户层暴露留到后续阶段”，而不是一次性把所有会话交互都做完。

## 当前结果

截至本阶段完成，项目已经具备：

- conversation 按 `conversation_id` 独立存储
- execution 按 `conversation_id` 独立存储
- 默认会话通过指针文件绑定到一个标准 conversation 对象
- conversation meta 包含 `updated_at`
- 多会话 CRUD 已作为内部 persistence 能力存在
- 当前 CLI 仍然保持“默认会话驱动”的简单使用方式

## 相关文档

- `docs/exec-detail/2026-03-30-multi-conversation-persistence-implementation.md`
