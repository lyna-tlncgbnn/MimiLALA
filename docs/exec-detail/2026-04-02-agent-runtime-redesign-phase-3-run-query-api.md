# 2026-04-02 Agent Runtime Redesign Phase 3 Run Query API

## 本次执行目标

本次执行是在第二阶段“影子写入”基础上的下一步推进。

第二阶段结束后，系统已经具备：

- 旧 JSONL 继续承载现有产品行为
- SQLite 开始影子接收 conversation / run / run_step / transcript 数据

但此时新 SQLite 模型仍然没有对外查询入口。

也就是说：

- 数据已经开始写进新库
- 但 API 还无法读取这些 run / step 数据
- 前端和调试工具还无法消费这套新结构

因此本次执行的目标是：

- 新增基于 SQLite 的 run 查询 API
- 新增基于 SQLite 的 run_steps 查询 API
- 保持现有 conversation API 完全不变
- 为后续前端 execution panel 改造提供可消费的数据接口

一句话概括，本次做的是：

> 把已经开始落盘的新 run / step 数据，正式通过 API 暴露出来。

## 为什么这一步要先做查询 API

当前系统已经处于迁移态：

- 写入侧开始影子写入 SQLite
- 读取侧仍然完全依赖旧 JSONL conversation

如果下一步直接切前端，而不先做稳定的查询 API，会出现两个问题：

1. 前端需要直接依赖 SQLite 表结构
2. 读取逻辑会分散在多个地方，后续难以维护

因此在迁移顺序上，run-query API 是一个必要的中间层：

- 它让新模型先对后端 API 层可见
- 它让后续前端可以切换到“读 API”，而不是“猜本地存储结构”
- 它也给我们提供了一个独立验证新数据模型的路径

所以本次不是“只是加了两个接口”，而是在新数据模型和后续 UI 之间补上了正式契约层。

## 本次实际改动

### 1. 扩展 SQLite repository 读取能力

修改文件：

- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`

#### 1.1 `RunRepository`

新增方法：

- `get_latest_for_conversation(conversation_id)`

虽然本次接口暂时没有直接使用这个方法，但它是下一步非常有价值的基础能力。

后续很可能会用在：

- conversation 页面显示“最近一次 run”
- 默认恢复当前 conversation 最新运行态
- 前端询问“这个 conversation 当前有没有正在运行的任务”

这一步提前补齐，是为了避免后续再次回头改 repository 边界。

#### 1.2 `RunStepRepository`

新增方法：

- `get(step_id)`

虽然当前 API 只使用 `list_for_run(run_id)`，但 step 单查能力补上以后，后续如果要做：

- 单 step 详情
- 卡片展开内容
- artifact 与 step 的局部联动

就不需要再改 repository 结构。

### 2. 新增 run / step API schema

修改文件：

- `agentbot/api/schemas.py`

本次新增了四个 schema：

- `RunSummary`
- `RunStepPayload`
- `RunDetail`
- `RunStepsDetail`

#### 2.1 `RunSummary`

描述一个 run 的核心元数据：

- `run_id`
- `conversation_id`
- `thread_id`
- `status`
- `started_at`
- `ended_at`
- `workflow_name`
- `user_message_id`
- `final_message_id`
- `error_message`

这层 schema 的意义是：

- 把 SQLite `runs` 表中的字段转换成稳定 API contract
- 让调用方看到的是业务对象，而不是数据库行

#### 2.2 `RunStepPayload`

描述单个 run step：

- `step_id`
- `run_id`
- `parent_step_id`
- `step_type`
- `title`
- `status`
- `display_mode`
- `sort_order`
- `started_at`
- `ended_at`
- `tool_name`
- `tool_call_id`
- `input_json`
- `output_json`
- `summary_text`

这一步实际上是第一次把“step 作为对外可消费对象”正式定型。

之前 step 只存在于：

- 架构文档
- SQLite schema
- 影子写入 bridge

本次之后，step 开始成为 API 层的一等对象。

#### 2.3 `RunDetail` 和 `RunStepsDetail`

这两个 schema 对应两个新接口：

- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/steps`

其中：

- `RunDetail` 只返回 run 摘要
- `RunStepsDetail` 返回 run 摘要 + step 列表

这让 run 元数据和 step timeline 既能拆开用，也能一起用。

### 3. 新增 run / step serializer

修改文件：

- `agentbot/api/serializers.py`

本次新增：

- `serialize_run(run: RunRow)`
- `serialize_run_step(step: RunStepRow)`

为什么要单独做 serializer，而不是在路由里直接拼 dict：

- 保持 API 层与 SQLite row model 解耦
- 让后续如果 `RunRow` / `RunStepRow` 调整时，修改集中在 serializer
- 与现有 `serialize_conversation_meta()` 风格保持一致

本次 serializer 设计保持了“尽量直接映射当前存储字段”的策略。

这是因为第三阶段目标是先让接口稳定存在，而不是此时就做复杂的 presentation-level 重新组织。

### 4. 新增独立的 runs 路由

新增文件：

- `agentbot/api/routes/runs.py`

这是本次执行的核心产物。

#### 4.1 新增接口：`GET /api/runs/{run_id}`

功能：

- 通过 SQLite 查询单个 run
- 如果不存在则返回 404
- 存在则返回 `RunDetail`

当前返回内容包括：

- run 的基础状态
- 所属 conversation
- thread_id
- started/ended 时间
- 关联的 user/final message id
- error_message

这个接口适合后续用于：

- 查询单次任务状态
- 打开某次任务详情页
- 轮询当前 run 是否完成

#### 4.2 新增接口：`GET /api/runs/{run_id}/steps`

功能：

- 先检查 run 是否存在
- 再查询该 run 下的所有 step
- 返回 `RunStepsDetail`

当前 step 列表按 repository 既定排序返回：

- `sort_order ASC`
- `started_at ASC`
- `step_id ASC`

这与未来前端时间线展示的需求一致。

### 5. 将新路由接入 FastAPI

修改文件：

- `agentbot/api/app.py`

本次新增：

- 引入 `runs_router`
- 在 app 创建时注册新 router

这意味着从应用结构上看，当前 FastAPI 已经进入“双轨 API”状态：

#### 旧轨

- `conversations` 路由
- 基于旧 JSONL conversation 语义

#### 新轨

- `runs` 路由
- 基于 SQLite run / step 语义

这正是迁移期应有的状态。

## 当前系统整体逻辑变成了什么

本次之后，系统不再只是“新模型能写，旧模型能读”，而是开始形成更完整的迁移闭环。

当前整体关系可以表示为：

```text
user request
  -> old runner / streaming runner
    -> old JSONL persistence (source of truth)
    -> shadow SQLite writes
         - conversations
         - runs
         - messages
         - run_steps

API layer
  -> old conversation endpoints
       read from JSONL-backed services
  -> new run endpoints
       read from SQLite repositories
```

也就是说，现在系统已经具备：

- 一套旧的可用主链路
- 一套新的结构化写入层
- 一套新的结构化读取接口

这正是后续切前端的前置条件。

## 本次验证

### 1. 手工注入一条 SQLite run 样本

为了验证新查询 API，本次使用 `RuntimeShadowWriter` 在工作区数据库中临时写入一条样本 run：

- user transcript
- tool step
- final assistant transcript

这条样本 run 使用固定的测试标识：

- `msg_api_probe_user`
- `msg_api_probe_assistant`
- `call_api_probe`

这样做的目的：

- 用真实的第二阶段写入逻辑生产样本
- 避免直接手工写 SQL 造成字段形态不一致

### 2. 直接调用新路由函数验证返回

验证了：

- `get_run(run_id)`
- `get_run_steps(run_id)`

返回结果确认：

- `get_run()` 能正确返回 run 摘要
- `get_run_steps()` 能正确返回：
  - run 摘要
  - step 列表
  - tool_call 相关字段
  - input/output/summary

验证结果说明：

- repository 查询正常
- serializer 正常
- route 层与 SQLite 连接正常
- 新 API contract 基本可用

### 3. 清理临时验证数据

验证完成后，本次删除了这条临时 run 相关数据：

- `runs`
- `messages`
- `run_steps`
- `artifacts`

最终确认工作区主数据库仍保持：

- `runs = 0`
- `messages = 0`
- `run_steps = 0`

当前主库中只保留：

- 通过 conversation 同步写入的 conversation 元数据

这样可以保证后续继续开发时，不会被这次 API 验证样本污染。

## 当前还没有做的事

本次虽然已经有了 run 查询 API，但仍然没有做以下内容：

- 没有把前端接到 `/api/runs/{run_id}` 或 `/api/runs/{run_id}/steps`
- 没有把 conversation detail 改成从 SQLite transcript 读取
- 没有新增“按 conversation 查询 runs”的 API
- 没有新增“最新 run”或“当前活跃 run”的 API
- 没有把 run / step 输出转成专门的前端展示结构
- 没有引入 LangGraph SQLite checkpointer

因此本次只是把新模型的“查询入口”打通了，但还没有切产品读路径。

## 当前遗留边界

### 1. 新 run API 与旧 conversation API 仍然是两套并存语义

当前：

- conversation API 还是 transcript-first
- run API 是 execution-first

这不是问题，而是迁移阶段的正常状态。

后续需要明确的是：

- 前端什么时候开始消费 run API
- 历史 transcript 是否继续全部从旧 conversation API 读取
- 是否要新增按 conversation 聚合 run 列表接口

### 2. `input_json` / `output_json` 当前仍以字符串暴露

当前 `RunStepPayload` 直接返回：

- `input_json`
- `output_json`

它们仍然是字符串，而不是结构化 JSON object。

这在当前阶段可以接受，因为：

- 先保证后端契约稳定
- 前端还没开始正式消费这组数据

但后续如果要给前端做卡片化展示，这两个字段大概率要改为结构化对象。

### 3. 路由当前直接使用 SQLite repository

当前 `runs.py` 路由是直接打开 `AgentDatabase` 并调用 repository。

这在当前阶段是合理的，因为：

- 目标是尽快把只读 API 建起来
- 还没有形成独立的 run service 层

但如果后续 run 查询逻辑继续变复杂，最好再抽一层：

- `agentbot/services/runs.py`

## 对下一步的影响

本次之后，后续工作已经具备了一个非常明确的切入点：

- 前端要做 execution panel，不再需要直连数据库，只要消费 run API
- 后端可以继续补：
  - `GET /api/conversations/{conversation_id}/runs`
  - `GET /api/conversations/{conversation_id}/runs/latest`
- conversation transcript 未来切 SQLite，也有了并行存在的 API 模型作参照

换句话说，这一步让新 runtime 模型第一次从“写得进去”变成了“读得出来”。

## 相关文件

本阶段新增或修改的主要文件如下。

新增：

- `agentbot/api/routes/runs.py`

修改：

- `agentbot/storage/repositories/runs.py`
- `agentbot/storage/repositories/run_steps.py`
- `agentbot/api/schemas.py`
- `agentbot/api/serializers.py`
- `agentbot/api/app.py`

## 结论

本次执行后，项目已经具备：

- SQLite 影子写入
- 基于 SQLite 的 run 查询 API
- 基于 SQLite 的 run_steps 查询 API

这意味着新 runtime 模型已经形成了“写入 + 查询”闭环。

虽然前端和主 API 还没有切过去，但从数据系统角度看，新 run / step 架构已经不再只是后备方案，而是已经成为一个可以被独立查询和验证的正式子系统。
