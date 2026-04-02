# 2026-04-02 Agent Runtime Redesign Phase 2 Shadow Writes

## 本次执行目标

本次执行是 `docs/architecture/agent-runtime-redesign.md` 第二阶段的第一步落地。

第一阶段已经完成了 SQLite 存储底座：

- 数据库文件
- schema
- repository 层
- CLI / FastAPI 启动初始化

但第一阶段结束时，新数据库还没有接入真实运行路径，仍然只有旧 JSONL 在承载实际业务。

因此本次执行的目标是：

- 保持当前产品行为不变
- 保持旧 JSONL conversation / execution persistence 继续作为主路径
- 开始把真实运行过程同步写入 SQLite
- 为后续切 API、切前端、切 checkpointer 做数据层准备

本次目标可以概括为：

> 让新 SQLite 模型开始接收真实数据，但暂时不让用户感知存储迁移。

## 本次采用的迁移策略

本次没有直接切换主存储，而是采用了“影子写入”。

所谓影子写入，就是：

1. 现有业务路径照常运行
2. 新存储层在旁路同步接收一份结构化数据
3. 如果新存储层写入失败，不影响旧主链路

在当前阶段，这个策略是必须的，因为：

- 现有 JSONL conversation / execution persistence 仍然是线上可用路径
- 新 SQLite 模型还没有被 API 和前端消费
- 一旦直接切换存储，出现 schema、映射、字段不一致问题，会直接影响现有聊天链路

因此本次的核心设计原则是：

- SQLite 写入必须是 best-effort
- SQLite 写入失败不能中断现有聊天
- 当前 API 响应仍以旧系统为准

## 本次实际改动

### 1. 扩展 repository，支持旧 conversation 数据镜像

修改文件：

- `agentbot/storage/repositories/conversations.py`
- `agentbot/storage/repositories/messages.py`
- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`
- `agentbot/storage/repositories/artifacts.py`

#### 1.1 `ConversationRepository`

新增能力：

- `upsert(...)`
- `delete(conversation_id)`

这一步非常关键。

因为当前系统里的会话 ID 来自旧 JSONL conversation 文件，第二阶段不能重新发一套 SQLite conversation_id。必须允许：

- 旧 conversation_id 继续是系统唯一会话标识
- SQLite 直接镜像这一 ID

所以 `upsert(...)` 是影子写入成立的前提。

#### 1.2 `MessageRepository`

新增能力：

- `delete_for_conversation(conversation_id)`

这是为会话删除做准备。

虽然当前 API 仍然从旧存储读数据，但如果 conversation 在旧系统中被删除，SQLite 也必须同步删除 transcript rows，否则后续切 API 时会读到脏数据。

#### 1.3 `RunRepository`

扩展能力：

- `create(...)` 支持显式传入 `run_id` 和 `started_at`
- `update_status(...)` 修正为在部分参数缺失时保留现有字段
- `delete_for_conversation(conversation_id)`

这里的关键点是：

- 第二阶段开始后，每次真实请求都要在 SQLite 中形成一个 `run`
- 运行状态更新要能在 success / failure 路径下稳定工作

#### 1.4 `RunStepRepository`

新增能力：

- `delete_for_run_ids(run_ids)`

这为 conversation 删除时的 run-step 清理打基础。

#### 1.5 `ArtifactRepository`

新增能力：

- `delete_for_run_ids(run_ids)`

虽然当前阶段没有 artifact 生产链路，但 schema 既然已经存在，删除链路也要补齐，否则后续很容易留下孤儿记录。

### 2. 新增运行期影子写入桥接层

新增文件：

- `agentbot/storage/shadow_runtime.py`

这是本次执行的核心文件。

它不是新的主业务层，而是一个迁移期桥接器，职责是：

- 把旧系统的 conversation / runner / streaming runner 活动镜像写入 SQLite
- 将旧系统的“消息驱动”流程翻译成新系统的 `conversation / run / run_step / message` 结构
- 所有写入默认按 best-effort 思路设计

#### 2.1 新增 `ActiveRunShadow`

定义了一个迁移期运行态对象：

- `run_id`
- `conversation_id`
- `user_message_id`
- `tool_steps`
- `next_sort_order`

这个对象的作用是：

- 在一次同步或流式运行过程中，暂时持有当前 run 的镜像上下文
- 记录某个 `tool_call_id` 对应的 SQLite `step_id`
- 追踪 run 内的 step 排序

它不是最终对外模型，而是第二阶段用于桥接旧 runner 流程和新 SQLite run-step 模型的过渡结构。

#### 2.2 `RuntimeShadowWriter` 的能力

新增的方法包括：

- `sync_conversation(meta)`
- `sync_conversations(metas)`
- `delete_conversation(conversation_id)`
- `start_run(...)`
- `record_tool_started(...)`
- `record_tool_finished(...)`
- `complete_run(...)`
- `fail_run(...)`
- `sync_completed_run_from_messages(...)`

当前实际被业务使用的是前几类核心方法。

#### 2.3 影子写入时的模型映射

本次已经明确实现了一套旧模型到新模型的映射规则。

##### conversation 映射

旧系统里的：

- `ConversationMeta.conversation_id`
- `ConversationMeta.name`
- `created_at`
- `updated_at`

被镜像到 SQLite `conversations` 表中。

##### user message 映射

当一次 run 开始时，用户输入被写入 SQLite `messages`：

- `role = user`
- `phase = final_answer`
- `visibility = visible`

这里虽然 `phase = final_answer` 这个名字看起来更适合 assistant，但当前阶段保持 transcript 行结构统一，优先保证数据能落进新表并被稳定关联到 `run_id`。

##### run 映射

每次用户请求会生成一个新的 SQLite `run`：

- `conversation_id = 当前 conversation`
- `thread_id = 当前 conversation_id`
- `workflow_name = chat_turn`
- `status = running`

此时 run 已经从“设计概念”变成了代码里的真实实体。

##### tool call 映射

旧系统的 `tool_started` / `tool_finished` 事件不再只是 execution log 或 SSE 事件。

现在它们还会映射为 SQLite `run_steps`：

- `step_type = tool_call`
- `display_mode = timeline`
- `status = running/completed/failed`

这一步是后续“思考中面板”以及“历史步骤回看”的关键数据来源。

##### final assistant 映射

当 run 成功完成后，最终 assistant 文本会写入 SQLite `messages`：

- `role = assistant`
- `phase = final_answer`
- `visibility = visible`

同时 run 会更新为：

- `status = completed`
- `final_message_id = 最终 assistant message_id`

##### failure 映射

当同步 runner 或 streaming runner 在任何阶段失败时，SQLite run 会被尽力更新为：

- `status = failed`
- `error_message = 用户可见错误文案`
- `ended_at = 当前时间`

这让 SQLite 新模型从一开始就能承载 run 的失败语义，而不是只有成功样例。

### 3. 会话 CRUD 开始同步写入 SQLite

修改文件：

- `agentbot/services/conversations.py`

#### 当前新增的影子行为

##### `list_conversations()`

当前行为变为：

1. 仍从旧 `ConversationStore` 读取
2. 拿到列表后 best-effort 同步到 SQLite
3. 返回值仍是旧系统数据

##### `create_conversation()`

当前行为变为：

1. 仍由旧 `ConversationStore` 创建 conversation
2. 创建成功后 best-effort 写入 SQLite
3. 返回值仍是旧系统的 `ConversationMeta`

##### `get_conversation()`

当前行为变为：

1. 仍从旧 JSONL conversation 文件读取
2. best-effort 同步 conversation meta 到 SQLite
3. 返回值不变

##### `rename_conversation()`

当前行为变为：

1. 仍重命名旧 JSONL conversation
2. 成功后同步更新 SQLite conversation title

##### `delete_conversation()`

当前行为变为：

1. 仍删除旧 JSONL conversation
2. 仍删除旧 execution file
3. 再 best-effort 级联删除 SQLite 的：
   - conversation
   - messages
   - runs
   - run_steps
   - artifacts

#### 这一层的设计关键点

这部分写法统一用了 `_best_effort(...)`。

含义是：

- SQLite 失败不影响当前 conversation API 行为
- 旧系统仍然是 source of truth
- 这符合第二阶段的迁移策略

### 4. 同步 runner 接入 SQLite 影子写入

修改文件：

- `agentbot/app/runner.py`

这是本次最重要的改动之一。

#### 4.1 用户消息不再是匿名 `HumanMessage`

在本次修改之前，同步 runner 构造 user 输入时使用的是：

- `HumanMessage(content=user_text)`

这意味着同步路径中的 user message 没有稳定：

- `message_id`
- `timestamp`

而新 SQLite transcript 和 run 需要稳定引用这些字段。

因此本次改为：

- 在同步 runner 中为 `HumanMessage` 显式注入 `_agentbot.message_id`
- 同时注入 `_agentbot.timestamp`

这一步不仅是为了 SQLite，也让同步 runner 的消息元数据与 streaming runner 更一致。

#### 4.2 run 启动时机

在同步 runner 成功加载 conversation 后，会：

1. best-effort 同步 conversation meta 到 SQLite
2. 基于 user message 启动一个 SQLite `run`
3. 将 user transcript 行写入 SQLite `messages`

这一步意味着：

- 每次真实同步调用都会在 SQLite 中落下一条 run
- 不再需要等到前端或 API 改造完成后才有 run 数据

#### 4.3 new messages 到 run_steps 的映射

同步 runner 在 graph 执行结束后，仍然会得到：

- `new_messages = result["messages"][len(input_messages):]`

本次新增逻辑会扫描 `new_messages`：

- assistant 带 `tool_calls` 时，写 `tool_call` step
- `ToolMessage` 时，更新对应 step 为 completed/failed

#### 4.4 run 完成时机

当旧系统 conversation 已成功持久化、execution log 已成功写入后，才会尝试：

- 写最终 assistant transcript 到 SQLite
- 将 SQLite run 更新为 `completed`

也就是说：

- SQLite 当前是旁路镜像，不抢先于旧系统提交
- 旧系统成功后，SQLite 才把这一轮镜像为 completed

#### 4.5 run 失败路径

在以下场景中，本次都会 best-effort 标记 SQLite run 为 `failed`：

- graph execution failed
- conversation persistence failed
- 没有找到 final assistant message

这样后续做 run 列表或历史回看时，不会只看到成功样本。

### 5. Streaming runner 接入 SQLite 影子写入

修改文件：

- `agentbot/app/streaming_runner.py`

这部分改动与同步 runner 对齐，但更贴近流式事件生命周期。

#### 5.1 流式 run 启动

在 streaming runner 成功加载 conversation 并创建 `user_message` 后，会：

1. 同步 conversation meta 到 SQLite
2. 基于 user message 创建 SQLite run
3. 记录 active shadow run

#### 5.2 tool_started / tool_finished 到 run_steps 的映射

流式 runner 现在在处理 SSE 内部事件时，除了旧逻辑外，还会：

- `tool_started` -> SQLite `run_steps.create(...)`
- `tool_finished` -> SQLite `run_steps.update_status(...)`

因此当前流式执行过程中，SQLite 已经可以开始积累真实 step timeline。

#### 5.3 流式完成后的 transcript 镜像

当最终 assistant 文本确定后，streaming runner 会：

- 把最终 assistant transcript 写入 SQLite
- 标记 run 为 `completed`

#### 5.4 流式失败路径

在以下场景，本次也会尽力把 SQLite run 标成失败：

- graph execution failed
- final values 缺失
- conversation persistence failed

#### 5.5 当前仍未改变的地方

虽然流式 runner 已经写入 SQLite，但当前仍然：

- 向前端输出旧 SSE 协议
- 返回值与旧前端契约保持兼容
- 旧 JSONL 仍然是 conversation 主记录

这点很重要，因为第二阶段当前还不是“新前端切换阶段”。

## 本次验证

### 1. 模块导入验证

已验证以下模块可正常导入：

- `agentbot.app.runner`
- `agentbot.app.streaming_runner`
- `agentbot.services.conversations`
- `agentbot.storage.shadow_runtime`

这说明第二阶段引入的新依赖关系在导入层面没有破坏当前项目结构。

### 2. conversation 同步验证

通过直接调用 `RuntimeShadowWriter.sync_conversation(meta)`，确认：

- SQLite `conversations` 表中能够正确写入旧 conversation metadata

这验证了：

- 数据库连接与 schema 正常
- `ConversationRepository.upsert(...)` 正常
- 旧 `ConversationMeta` 到新表的映射正常

### 3. 影子 run / step 链路隔离验证

为了避免污染工作区主库，本次使用了一个临时 SQLite 文件做隔离验证。

验证路径为：

1. `start_run(...)`
2. `record_tool_started(...)`
3. `record_tool_finished(...)`
4. `complete_run(...)`

验证结果确认：

- `conversations = 1`
- `runs = 1`
- `messages = 2`
- `run_steps = 1`

同时验证了：

- run 状态为 `completed`
- user / assistant transcript rows 均正常写入
- tool step 状态从 `running` 更新为 `completed`

### 4. 工作区主库状态核对

为了避免把手工验证数据留在主库中，本次在工作区主数据库中清除了测试 run/message/step 数据。

最终核对结果：

- `conversations = 1`
- `runs = 0`
- `messages = 0`
- `run_steps = 0`

这说明：

- 主库当前只保留由会话列表同步带来的 conversation 元数据
- 没有残留人工验证产生的脏 run / message / step 数据

## 当前系统在第二阶段之后的状态

本次执行完成后，系统已经从“只有 schema 和 repository”推进到“运行入口已开始具备新模型镜像能力”。

当前状态可以概括为：

### 旧系统仍然负责

- 主业务 conversation history
- execution log
- API 返回
- 前端显示

### 新系统已经开始负责

- mirror conversation metadata
- mirror per-request runs
- mirror final transcript messages
- mirror tool-step timeline

### 当前运行关系

```text
user request
  -> old runner / streaming runner
    -> old JSONL persistence (source of truth)
    -> best-effort shadow SQLite writes
         - conversations
         - runs
         - messages
         - run_steps
```

也就是说，第二阶段当前已经不是“只建结构”，而是“新结构开始接收真实运行数据”。

## 这一步仍然没有做的事

这次仍然没有切以下内容：

- 没有把 conversation API 切换到 SQLite 读取
- 没有新增 run/step 查询 API
- 没有让前端读取 `runs` / `run_steps`
- 没有改变前端消息渲染模型
- 没有引入 LangGraph SQLite checkpointer
- 没有做端到端真实模型调用回归测试

这些都属于后续阶段。

## 当前遗留问题与边界

### 1. SQLite 仍然不是 source of truth

当前 SQLite 只是影子副本。

这意味着：

- 如果影子写入失败，旧系统照常工作
- SQLite 可能在极端情况下出现镜像不完整

这是当前阶段允许的，因为此时我们优先保证旧系统稳定。

### 2. `messages.phase` 在 user message 上仍是过渡写法

当前 user transcript 行写入时使用：

- `phase = final_answer`

这不是最终最理想语义，而是阶段性统一写法。

后续如果要更严格区分 transcript message 类型，可以再调整为更清晰的 phase 语义。

### 3. streaming runner 与 sync runner 的 SQLite 镜像能力已对齐，但仍不是统一 runtime service

目前同步路径和流式路径都接入了 SQLite shadow writes，但实现仍然分散在两个 runner 中。

这在当前阶段可以接受，因为主要目标是先让新模型接收到真实数据。

后续如果继续推进，应当考虑把 run lifecycle 进一步收敛到统一 service。

## 对第三步的直接影响

有了本次影子写入，下一步就可以开始做“新查询接口”，因为：

- SQLite 中已经具备真实 conversation 元数据
- 真实请求已经可以落成 run
- 真实工具流程已经可以落成 step
- transcript 可见消息已经可被新表承载

下一步不必再去设计：

- run 是什么
- step 怎么写
- conversation 如何镜像

下一步可以直接做：

1. run 查询 API
2. run_steps 查询 API
3. conversation transcript 的 SQLite 读取验证
4. 新旧接口并存期的数据一致性校验

## 相关文件

本阶段新增或修改的主要文件如下。

新增：

- `agentbot/storage/shadow_runtime.py`

修改：

- `agentbot/storage/repositories/conversations.py`
- `agentbot/storage/repositories/messages.py`
- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`
- `agentbot/storage/repositories/artifacts.py`
- `agentbot/services/conversations.py`
- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

## 结论

本次执行后，第二阶段已经从“只有新 schema”推进到“真实运行开始影子写入新模型”。

这一步的意义不在于用户立刻看到变化，而在于：

- 新 SQLite 结构已经开始承接真实业务数据
- run / step 不再只是文档中的概念
- 后续切查询 API 和前端 execution panel 已经有了数据基础

换句话说，从这一刻开始，SQLite 新模型已经不再是空壳，而是开始成为未来主系统的真实后备形态。
