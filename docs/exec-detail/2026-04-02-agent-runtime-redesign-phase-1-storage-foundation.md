# 2026-04-02 Agent Runtime Redesign Phase 1 Storage Foundation

## 本次执行目标

本次执行是 `docs/architecture/agent-runtime-redesign.md` 的第一阶段落地。

本阶段的目标不是切换业务逻辑，而是先把新架构需要的本地存储底座建起来，保证后续第二阶段、第三阶段可以在稳定基础上逐步迁移。

本阶段明确目标：

- 引入新的 SQLite 存储层
- 建立 conversation / message / run / run_step / artifact 的基础 schema
- 增加数据库初始化与连接管理
- 增加 repository 层，作为后续业务迁移的统一读写入口
- 将数据库初始化接入 CLI 和 FastAPI 启动流程
- 保持现有 JSONL conversation / execution persistence 继续工作

本阶段明确不做：

- 不切换现有聊天主链路到 SQLite
- 不改现有 `ConversationStore` / `ExecutionStore` 的读写路径
- 不改前端接口
- 不改现有 SSE 事件协议
- 不引入 LangGraph checkpointer
- 不做旧 JSONL 数据迁移

一句话概括，本阶段做的是“新房子的地基和管线”，不是“搬家”。

## 为什么第一阶段要这样做

当前系统仍基于两套旧持久化：

- `workspace/conversations/<conversation_id>.jsonl`
- `workspace/executions/<conversation_id>.jsonl`

这套模型当前还能支撑已有功能，但已经不适合目标架构。

目标架构要求：

- 一个 conversation 下有多个 run
- 一个 run 下有多个 step
- transcript 与 execution trace 分离
- 后续引入 LangGraph checkpoint persistence

如果直接在现有 runner、API、前端上同步切换到新模型，风险较高：

- 现有聊天主链路会被同时改动 persistence、API、frontend 三层
- 一旦新 schema 或 repository 设计有问题，会直接影响已有功能
- 旧 JSONL 数据也无法作为兜底

因此本阶段采用最保守策略：

1. 先引入 SQLite 和 schema
2. 先建立新 storage API
3. 让数据库在运行时稳定存在
4. 暂时不改变旧业务路径

这样做的结果是：

- 旧功能继续可用
- 新架构开始有真实代码而不是停留在文档
- 第二阶段可以只聚焦“如何写入 runs / run_steps”，而不是同时解决建库问题

## 本次实际改动

### 1. 新增 `agentbot/storage/` 存储层目录

新增目录：

- `agentbot/storage/`
- `agentbot/storage/repositories/`

这是新架构下的本地存储层入口，职责上与现有 `agentbot/memory/` 区分如下：

- `agentbot/memory/`
  旧 JSONL persistence，仍是当前生产路径
- `agentbot/storage/`
  新 SQLite persistence，当前处于基础设施阶段

这一步的意义是先把“新架构代码应该放哪里”确定下来，避免后续继续把新旧逻辑掺在一起。

### 2. 新增公共路径与基础工具

新增文件：

- `agentbot/storage/paths.py`
- `agentbot/storage/common.py`

#### `paths.py`

定义了新存储层使用的固定路径：

- workspace 根目录
- SQLite 数据库文件路径

当前数据库文件路径为：

```text
workspace/agent_runtime.db
```

这样做的目的：

- 保持数据库与现有 `workspace/` 语义一致
- 后续无论是 CLI、FastAPI 还是桌面端，都共用同一份本地数据库

#### `common.py`

提供新架构下通用的：

- `new_prefixed_id(prefix)`
- `now_iso()`

这两个能力后续会被 repository 层持续复用，避免每个模块重复生成 ID 和时间戳逻辑。

### 3. 新增 SQLite schema 定义

新增文件：

- `agentbot/storage/schema.py`

这是本阶段的核心文件之一。

当前定义了：

- `SCHEMA_VERSION = 1`
- schema 初始化逻辑
- 所有基础表的 DDL
- 所有必要索引

#### 当前创建的表

1. `schema_metadata`
2. `conversations`
3. `runs`
4. `messages`
5. `run_steps`
6. `artifacts`

#### 当前创建的索引

- conversation 最近更新时间索引
- conversation 下消息时间索引
- message 的 `run_id` 索引
- conversation 下 run 时间索引
- `thread_id` 索引
- run 下 step 排序索引
- `tool_call_id` 索引
- run 下 artifact 索引

#### 为什么本阶段就把这些表都建出来

因为第二阶段开始，后端写路径会逐渐迁移到这些表里。如果第一阶段只建一半表，第二阶段还要继续补 schema，会把“基础设施变更”和“业务写入变更”混在一起。

本阶段提前把目标结构落全，后续每个阶段只关注行为迁移。

### 4. 新增数据库连接与初始化管理

新增文件：

- `agentbot/storage/db.py`
- `agentbot/storage/bootstrap.py`

#### `db.py`

提供 `AgentDatabase`：

- 统一数据库路径
- 统一 `sqlite3` 连接管理
- 统一 `row_factory`
- 自动开启 `PRAGMA foreign_keys = ON`
- 提供事务安全的 `connect()` 上下文
- 提供 `initialize()` 初始化入口

这一步的意义是：

- 避免后续 repository 直接各自打开数据库文件
- 保证 schema 初始化方式一致
- 为之后接入更高层 service/repository 组合提供稳定入口

#### `bootstrap.py`

提供：

- `ensure_agent_database()`

这是一个很轻的封装，职责很明确：

- 确保数据库文件存在
- 确保 schema 已初始化
- 返回数据库路径

之所以单独做这一层，是为了让 CLI、API 启动阶段都能调用统一入口，而不是分别持有数据库初始化细节。

### 5. 新增 dataclass 模型

新增文件：

- `agentbot/storage/models.py`

当前定义了 5 类 row model：

- `ConversationRow`
- `MessageRow`
- `RunRow`
- `RunStepRow`
- `ArtifactRow`

这些 dataclass 的定位不是业务 domain model，而是 repository 层返回的结构化行对象。

为什么要先加这层：

- 避免 repository 直接向上暴露 `sqlite3.Row`
- 让后续 service 层和 API 层不依赖底层数据库实现细节
- 保持新存储层输出稳定

### 6. 新增 repository 层

新增文件：

- `agentbot/storage/repositories/conversations.py`
- `agentbot/storage/repositories/messages.py`
- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`
- `agentbot/storage/repositories/artifacts.py`
- `agentbot/storage/repositories/__init__.py`

#### 当前 repository 的作用

当前 repository 不是给现有业务链路使用的，而是给后续迁移做准备。

已经具备的能力：

##### `ConversationRepository`

- `create(title)`
- `get(conversation_id)`
- `list_all()`
- `update_title(conversation_id, title)`
- `touch(conversation_id, updated_at=None)`

##### `MessageRepository`

- `create(...)`
- `list_for_conversation(conversation_id, visible_only=True)`

当前 message 模型已经按新设计区分：

- `role`
- `phase`
- `visibility`
- `content_json`
- `text_preview`

这与旧系统“所有东西都当消息写入 transcript”的方向已经明确分离。

##### `RunRepository`

- `create(...)`
- `get(run_id)`
- `list_for_conversation(conversation_id)`
- `update_status(...)`

这一步非常关键，因为它把 `run` 作为一等实体放进了代码，而不再只是停留在架构文档中。

##### `RunStepRepository`

- `create(...)`
- `list_for_run(run_id)`
- `update_status(...)`

这也是本次重构的核心之一。后续“思考中面板”“历史步骤回看”“按 run 聚合 UI”都会建立在这层之上。

##### `ArtifactRepository`

- `create(...)`
- `list_for_run(run_id)`

虽然当前阶段还没有 artifact 生产链路，但 schema 和 repository 已经留出位置，后续生成文件、图片、报告、链接时可以直接接入。

### 7. 将数据库初始化接入 FastAPI 启动

修改文件：

- `agentbot/api/app.py`

本次修改内容：

- 在 FastAPI `startup` 生命周期里调用 `ensure_agent_database()`

这样带来的效果是：

- 启动本地 API 时，会自动创建数据库与表
- 不需要单独跑初始化脚本
- 数据库成为应用的一部分，而不是人工维护的额外依赖

这一点对于桌面端很重要，因为用户不会主动做“数据库初始化”这类运维动作。

### 8. 将数据库初始化接入 CLI 入口

修改文件：

- `agentbot/app/cli.py`

本次修改内容：

- CLI 进入主逻辑前先执行 `ensure_agent_database()`

这样带来的效果是：

- 即使只使用 CLI，也会拥有同样的数据库基础设施
- 不会出现“API 路径建了库、CLI 路径没建库”的分叉状态

这一步是在为后续统一 runtime 存储行为做准备。

### 9. 更新架构文档状态

修改文件：

- `docs/architecture/agent-runtime-redesign.md`

本次补充了状态说明：

- 设计文档不再只是“计划”
- 已经明确记录 Phase 1 已开始
- 当前状态是“SQLite storage bootstrap and repository layer are present in the codebase, but the runtime still reads and writes through the legacy JSONL stores”

这一步的意义是防止后续误判项目状态。

## 第一阶段之后，系统整体逻辑是怎样的

本阶段之后，系统进入一种“双存储并存，但只有旧路径在实际承载业务”的状态。

可以这样理解：

### 当前仍在承载业务的旧路径

- `agentbot/memory/conversation.py`
- `agentbot/memory/execution.py`
- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

当前真实聊天、流式输出、会话历史、execution log 仍然使用：

- JSONL transcript
- JSONL execution log

### 已经建好的新路径

- `agentbot/storage/`

当前新路径已经具备：

- SQLite 数据库文件
- 目标 schema
- repository 接口
- 启动期自动初始化

但还没有接入：

- 当前聊天写路径
- 当前 SSE 事件写路径
- 当前 API 读路径

### 这意味着什么

从运行时角度看，当前应用逻辑仍然是：

```text
CLI / FastAPI
  -> old runner / streaming runner
    -> JSONL conversation / execution stores
```

但从基础设施角度看，系统已经额外具备：

```text
CLI / FastAPI startup
  -> ensure_agent_database()
    -> SQLite db file
      -> conversations / messages / runs / run_steps / artifacts tables
```

也就是说，应用现在已经开始“带着新房子的地基运行”，但还没有搬进去。

## 本次验证

### 1. 数据库初始化验证

执行了数据库初始化入口，确认返回路径为：

```text
F:\AgentBot\workspace\agent_runtime.db
```

同时确认文件已实际创建。

### 2. 表结构验证

通过 `sqlite3` 查询 `sqlite_master`，确认当前数据库已经存在：

- `artifacts`
- `conversations`
- `messages`
- `run_steps`
- `runs`
- `schema_metadata`

并确认：

- `schema_version = 1`

### 3. 启动集成验证

虽然本次没有切换业务路径，但从代码上已经确保：

- FastAPI 启动时自动建库
- CLI 启动时自动建库

这说明数据库层已经真实进入应用生命周期，而不是孤立代码。

## 为什么这一步没有直接切业务路径

这一步看起来“只做了底层”，但实际上是必要的边界控制。

如果第一阶段直接让 runner 开始写 SQLite，会引入以下耦合问题：

- schema 是否稳定
- repository 是否完整
- 旧 JSONL 是否要双写
- API 是否同步切换
- 前端是否同步适配

这些问题如果一起处理，风险会过高。

本阶段把问题拆开后，后续阶段会更清晰：

### 第一阶段

只解决：

- 数据库存不存在
- schema 不存在
- 没有新存储层代码

### 第二阶段

只解决：

- 新请求如何写入 `runs` / `run_steps` / transcript messages

### 第三阶段

只解决：

- LangGraph checkpointer 接入

### 第四、五阶段

再分别切 API 和前端

这就是本阶段“看上去克制，但实际上是正确切法”的原因。

## 当前结果

截至本次执行结束，项目已经具备：

- 一份正式的 agent runtime 重构设计文档
- 一套新的 SQLite 本地存储层
- conversation / message / run / run_step / artifact 的基础 schema
- repository 层代码
- CLI / FastAPI 启动时自动初始化数据库
- 保持旧 JSONL 业务路径继续工作

这意味着项目已经从“只有设计稿”推进到了“新存储架构已进入代码库并可被后续阶段直接复用”的状态。

## 对第二阶段的直接影响

第二阶段不需要再做这些事情：

- 不需要再设计数据库文件位置
- 不需要再设计基础 schema
- 不需要再补初始化逻辑
- 不需要再定义 repository 边界

第二阶段可以直接专注于：

1. 在每次用户请求开始时创建 `run`
2. 把用户可见 transcript 逐步写入 `messages`
3. 把过程性步骤写入 `run_steps`
4. 暂时维持旧 JSONL 兼容或影子写入策略

换句话说，第一阶段已经把第二阶段最容易分散注意力的基础工作提前清掉了。

## 相关文件

本阶段新增或修改的主要文件如下。

新增：

- `agentbot/storage/__init__.py`
- `agentbot/storage/common.py`
- `agentbot/storage/paths.py`
- `agentbot/storage/schema.py`
- `agentbot/storage/models.py`
- `agentbot/storage/db.py`
- `agentbot/storage/bootstrap.py`
- `agentbot/storage/repositories/__init__.py`
- `agentbot/storage/repositories/conversations.py`
- `agentbot/storage/repositories/messages.py`
- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`
- `agentbot/storage/repositories/artifacts.py`

修改：

- `agentbot/api/app.py`
- `agentbot/app/cli.py`
- `docs/architecture/agent-runtime-redesign.md`

产物：

- `workspace/agent_runtime.db`

## 结论

本阶段完成后，项目已经具备新的本地 runtime storage 基础设施，但业务主链路仍然安全地停留在旧系统上。

这不是半成品状态，而是有意设计的迁移态。

后续所有关于：

- run
- step
- transcript clean-up
- 新 SSE 协议
- 前端 execution panel

的实现，都将建立在本阶段引入的 SQLite 存储层之上。
