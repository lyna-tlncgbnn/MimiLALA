# 2026-04-04 Backend Reorganization Blueprint

## 目标

本方案用于指导 `agentbot/` 后端代码的增量重组。

目标不是推倒重写，也不是替换当前 FastAPI / LangGraph / SQLite / Playwright 技术路线，而是在保持主链路持续可运行的前提下，收紧模块边界、降低认知负担、减少重复逻辑，并为后续浏览器 runtime、memory、approval、multi-agent 等能力预留更稳定的扩展位置。

本蓝图覆盖：

- 当前后端结构问题诊断
- 重构原则与不变量
- 目标目录结构
- 旧目录到新目录的迁移映射
- 分阶段实施顺序
- 每阶段验收标准
- 风险与回滚策略

本蓝图不覆盖：

- 前端界面重构
- 数据库从 SQLite 切换到其他存储
- LangGraph 主链路重写
- 浏览器 runtime 行为语义变更

## 当前诊断

结合当前仓库代码、现有架构文档以及 FastAPI / LangGraph 官方推荐组织方式，当前后端不是“架构错误”，而是已经进入“需要做结构收口”的阶段。

### 当前优点

- 已经形成明确的主链路：`API -> Service -> Runner -> LangGraph -> Tools / Storage / Checkpoints`
- 已经区分 transcript、runs、run_steps、checkpoints 四类不同层次的数据
- 已经把 browser 能力从普通 tool 提升为独立子系统
- 已经具备基础分层：`api / services / graph / storage / browser / tools / config`
- 主链路当前仍然可运行，且文档与代码基本对齐

### 当前主要问题

#### 1. 接口层和应用层边界不够稳定

`agentbot/api/routes/` 中有部分逻辑直接读取数据库或 repository，而不是统一经由 service 或用例层。

这会带来几个问题：

- 调用路径不一致
- 请求层容易泄漏存储细节
- 后续做权限、审计、事务、缓存时不容易集中处理

典型例子：

- `agentbot/api/routes/conversations.py`
- `agentbot/api/routes/runs.py`

#### 2. 执行编排逻辑在多个位置重复

同步执行和流式执行分别位于：

- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

两者存在较多重复逻辑：

- 读取配置
- 初始化模型
- 读取会话历史
- 启动 run
- 构建 graph
- 处理 graph updates / values
- 落 run 完成或失败状态

这会导致：

- 任何执行流程变更都需要改两处
- 同步与流式的行为容易逐步漂移
- 调试和测试粒度难以统一

#### 3. service 层偏薄，职责没有完全收口

当前 `services/` 提供了 `ConversationService` 和 `ChatService`，但部分业务逻辑仍分散在：

- API route
- runner / streaming runner
- storage.shadow_runtime

这说明目前“业务用例层”还没有成为真正的唯一入口。

#### 4. browser 相关代码的主要问题在 LangGraph 适配层，而不是整个 browser 包

当前 browser 相关代码体量已经很大：

- `agentbot/graph/browser_nodes.py`
- `agentbot/browser/session.py`
- `agentbot/browser/actions.py`
- `agentbot/browser/observation_capture.py`
- `agentbot/browser/observation_serialize.py`

对照 `browser-use` 的参考结构后，可以确认 `agentbot/browser/` 当前的大方向并没有明显走偏：

- `runtime/` 已经承载 event bus 与 watchdog
- `session.py` 负责 browser session lifecycle
- `actions.py` 负责动作执行
- `observation_*` 负责观察与序列化

当前真正最重、最容易继续膨胀的，是 `agentbot/graph/browser_nodes.py` 这层 LangGraph browser adapter。问题不在于文件大本身，而在于多个职责已经耦合在一起：

- browser intent / prepare
- observation capture 的调度
- planner prompt 组装与状态解释
- action execution 编排
- browser event 转换
- graph node orchestration

因此 Phase 4 的重点不应是“整块 browser 子系统大拆”，而应是“先把 LangGraph browser adapter 拆细，必要时再轻拆 session 层”。

#### 5. legacy 模块仍暴露在主包结构里

`agentbot/memory/` 当前已经不是主链路真相来源，但它仍位于主包一级目录下。

这会带来两个问题：

- 新读代码的人容易误判它仍是主存储
- 后续重构时容易出现“旧逻辑被意外复用”的路径污染

#### 6. 当前目录更偏“技术归类”，而不是“稳定边界 + 用例入口”

目前的目录大致按技术分类：

- `api`
- `app`
- `browser`
- `graph`
- `storage`
- `tools`

这在项目早期是合理的，但随着运行模型变复杂，建议逐步增加“用例入口”和“基础设施边界”的组织方式，否则：

- 业务规则容易散落
- 调用链容易变长
- 很难快速判断一个改动应该落在哪一层

## 外部参考结论

### FastAPI 官方建议

FastAPI 官方对较大应用的建议可以概括为：

- `main` 保持很薄，只做应用组装
- router 按资源或能力拆分
- 依赖注入、配置、公共依赖集中管理
- 路由层主要负责 HTTP 协议，不承载过多业务逻辑

参考：

- [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI Full Stack Template](https://github.com/fastapi/full-stack-fastapi-template)

### LangGraph 官方建议

LangGraph 官方资料更强调按图来组织：

- `graph`
- `state`
- `nodes`
- `tools`
- `persistence`

核心思想不是追求层数多，而是保持：

- 图状态边界清晰
- node 职责清晰
- persistence 边界清晰
- 工具能力与编排能力分离

参考：

- [LangGraph Overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Application Structure](https://docs.langchain.com/oss/python/langgraph/application-structure)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

### 对本项目的启发

对 AgentBot 来说，不应照搬典型 CRUD Web 项目的组织方式，也不应完全沿着 demo 级 agent 项目的轻量结构继续生长。

更合适的方向是：

- 保留 FastAPI 的路由边界
- 保留 LangGraph 的 graph/state/nodes 核心组织
- 新增一层明确的“应用用例层”
- 把 SQLite / browser / tools / llm / config 视为基础设施
- 让 API、CLI、未来 automation 或桌面端能力共享同一套用例入口

## 重构原则

### 1. 主链路持续可运行

任何阶段都不允许出现“重构进行中，主链路不可运行数天”的状态。

必须保持至少以下链路始终可用：

- CLI 单轮执行
- `/api/conversations`
- `/api/conversations/{id}/runs`
- `/api/conversations/{id}/runs/stream`
- `/api/runs/{run_id}/steps`

### 2. 先收口边界，再做大规模搬迁

优先处理：

- 入口统一
- 调用链统一
- 逻辑重复收敛

不要一开始就进行全仓大挪目录。

### 3. 先抽共用执行内核，再调整 API 和文件位置

同步与流式执行的重复是当前最容易产生持续维护成本的问题之一。

因此执行编排层应优先收敛。

### 4. 不把“目录变化”误当成“架构改进”

仅仅移动文件不能改善系统。

每一步重构都必须回答：

- 入口是否更统一
- 依赖是否更单向
- 修改一个功能时涉及文件是否减少
- 测试和文档是否更容易补齐

### 5. browser 子系统单独治理，但优先收口 adapter 层

browser 子系统已经有足够复杂度，不应再把它当成普通工具的一部分看待。
但治理重点应放在 `graph -> browser runtime` 的适配层，而不是为了目录整齐去提前打散已经较稳定的 runtime 结构。

### 6. 文档与代码同步演进

阶段性重构完成后，需要同步更新：

- `docs/architecture/project-structure.md`
- `docs/architecture/runtime-architecture.md`
- `docs/architecture/runtime-flow.md`
- 必要时补充新文档

执行细节记录到：

- `docs/exec-detail/`

## 本次重构不变量

以下事实在本轮重构中不改变：

- 主 API 协议保持 run-oriented
- transcript / runs / run_steps / checkpoints 四层数据模型保持不变
- SQLite 仍是产品层 read model 的主存储
- LangGraph SQLite saver 仍负责 durable execution
- browser 仍以 LangGraph subgraph 接入主链路
- tools 仍使用现有注册机制，除非某阶段明确调整
- 前端对当前 SSE 事件语义的依赖暂不改变

## 目标结构

### 顶层目标

将 `agentbot/` 逐步收敛为以下几层：

```text
agentbot/
  api/                HTTP / SSE 协议层
  application/        用例层，统一业务入口
  domain/             核心运行概念与类型
  graph/              LangGraph 主图与子图
  infrastructure/     外部能力适配层
```

这不是要求一次性完成的最终目录，而是重构方向。

### 目标职责划分

#### `api/`

只处理：

- FastAPI app 组装
- router
- request / response schema
- serializer
- SSE 输出适配

不应直接负责：

- repository 查询
- run 生命周期控制
- graph 执行编排

#### `application/`

作为统一业务入口，按用例组织，例如：

- `conversation_queries.py`
- `conversation_commands.py`
- `run_queries.py`
- `run_execution.py`
- `run_streaming.py`

职责：

- 编排一次完整业务用例
- 协调 graph、storage、llm、browser、serializer 等能力
- 作为 API / CLI / automation 的共同调用入口

#### `domain/`

放核心概念和边界，而不是技术实现。

可逐步承载：

- run state 概念
- transcript message 概念
- step/event 类型
- 可读性更强的业务枚举
- 后续 approval / interrupt / multi-agent 的公共模型

如果短期不引入也可以，但应作为目标方向。

#### `graph/`

继续保留 LangGraph 组织中心地位：

- graph builder
- state
- nodes
- routes
- browser subgraph

但 graph 应更聚焦“图编排”，减少直接承担具体 runtime 细节。

#### `infrastructure/`

承载外部系统和实现细节：

- SQLite
- LLM provider
- Config
- Browser runtime
- Tools registry
- Search provider

它们是可替换或可演进的实现层。

## 推荐阶段性目标结构

为了降低一次性迁移风险，本项目建议采用两步式目标结构。

### 阶段 A：轻量收口结构

先在不大规模搬迁的情况下把边界收紧：

```text
agentbot/
  api/
  app/
  browser/
  config/
  graph/
  services/
  storage/
  tools/
```

但约束变更为：

- `api` 不直接查 repository
- `services` 成为用例入口
- `app` 只保留 CLI / execution adapters
- `storage` 只负责持久化
- `graph` 只负责 LangGraph 编排
- `browser` 只负责浏览器 runtime

### 阶段 B：正式目标结构

在阶段 A 稳定后，再按需要收敛为：

```text
agentbot/
  api/
  application/
  domain/
  graph/
  infrastructure/
```

这一步可以渐进，不必一次迁完全部文件。

## 旧结构到目标结构映射

### `agentbot/api/`

当前状态：基本合理。

目标：

- 保留
- 进一步变薄

迁移要求：

- route 内不直接访问 repository
- route 中数据库初始化逻辑移出
- SSE event formatting 可保留在 `api` 层

### `agentbot/app/`

当前状态：混合了入口和执行编排。

建议：

- 保留 `cli.py`
- 抽出统一执行内核
- `runner.py` / `streaming_runner.py` 变为薄 adapter

后续目标：

- 逐步迁向 `application/`

### `agentbot/services/`

当前状态：方向正确，但范围太窄。

建议：

- 作为阶段 A 的“应用层”承载位置
- 逐步新增更明确的用例模块

例如：

- `services/conversation_queries.py`
- `services/conversation_commands.py`
- `services/run_queries.py`
- `services/run_execution.py`
- `services/run_streaming.py`

后续在阶段 B 再整体改名为 `application/`。

### `agentbot/storage/`

当前状态：整体比较健康。

建议：

- 保持 repository 模式
- 保持 schema / db / bootstrap 分离
- 避免业务逻辑继续流入 repository

后续目标：

- 可迁入 `infrastructure/storage/`

### `agentbot/models/`

当前状态：只有 `llm.py`，名称容易误导。

问题：

- “models” 这个名字在 Python Web 项目中通常让人联想到 ORM 模型
- 实际这里只有 LLM factory

建议：

- 阶段 A 保持不动或移到 `config`/`services` 附近都行
- 阶段 B 迁入 `infrastructure/llm/`

### `agentbot/config/`

当前状态：配置较集中，但 `settings.py` 体量偏大。

建议：

- 保留集中配置入口
- 后续可按主题拆成：
  - `llm.py`
  - `search.py`
  - `command.py`
  - `browser.py`

阶段 A 不必优先做。

### `agentbot/tools/`

当前状态：作为能力注册层是合理的。

建议：

- 保留
- 明确其角色是“graph 可调用能力集合”
- 不把浏览器 runtime 再塞进 tools

后续目标：

- 可迁入 `infrastructure/tools/`

### `agentbot/browser/`

当前状态：整体方向基本合理，已经与 `browser-use` 的粗粒度结构对齐。

建议方向：

- 保持 `runtime/` 继续承载 event bus、watchdogs、runtime coordination
- 保持 `session.py` 作为 browser session lifecycle 的主要入口
- 保持 `actions.py` / `observation_*` 的现有职责边界
- 仅在后续变更频率继续升高时，再把 `session.py` 轻拆为更小的实现模块

这一层当前不是优先的大拆目标。

### `agentbot/graph/`

当前状态：主图组织方向正确。

建议：

- 保持 graph builder / routes / state 的中心地位
- 优先拆细 `browser_nodes.py`
- 把 browser node 里混在一起的 intent、prepare、observe、plan、act、evaluate helper 拆成更清晰的 adapter 模块
- graph 层只做编排和状态转换

### `agentbot/memory/`

当前状态：遗留模块。

建议：

- 短期保留但标记为 legacy
- 从主链路引用中彻底清空
- 文档中明确不是 source of truth

中期目标：

- 迁到 `agentbot/legacy/memory/`
  或
- 彻底移除

## 分阶段实施计划

## Phase 0：蓝图落地与边界对齐

目标：

- 形成统一重构蓝图
- 明确不变量、目标结构、优先级

产出：

- 本文档

验收：

- 团队对“为什么重构、先重构什么、哪些不动”达成一致

## Phase 1：收紧 API 到 service 的边界

目标：

- API route 不再直接访问 repository / database
- API 只处理 HTTP 协议与响应格式

具体工作：

1. 为 conversations / runs 补齐 service 或 query facade
2. 将 route 中的 `AgentDatabase` / `RunRepository` / `RunStepRepository` / `ArtifactRepository` 访问迁出
3. 将 conversation、run、step 的读取逻辑统一收口到 services
4. 保持 API schema 和响应格式不变

验收标准：

- `agentbot/api/routes/*.py` 不再直接 import `AgentDatabase`
- `agentbot/api/routes/*.py` 不再直接 import storage repository
- HTTP 接口行为不变

风险：

- service 层可能先变厚

接受策略：

- 阶段 A 允许 service 偏厚，只要边界更清晰

## Phase 2：统一执行编排内核

目标：

- 收敛 `runner.py` 与 `streaming_runner.py` 的重复逻辑

建议做法：

抽取一个共享执行核心，例如：

- `services/run_execution_core.py`
  或
- `app/execution_core.py`

它应统一负责：

- settings 加载
- llm 初始化
- conversation history seed
- run start
- graph build
- graph event interpretation
- run complete / fail persistence

同步与流式差异仅体现在：

- 输出接口
- 是否持续产出 UI/SSE 事件

验收标准：

- 同步与流式入口共享绝大部分执行逻辑
- 新增一个 graph 行为变更时，核心逻辑只需改一处

风险：

- event 处理抽象过度导致代码可读性下降

控制方式：

- 优先抽共享步骤，不强行抽象所有分支

## Phase 3：明确用例层，弱化“services”这个泛命名

目标：

- 把当前 service 层从“两个大 service”变成“按用例组织”

建议组织：

```text
agentbot/services/
  conversation_queries.py
  conversation_commands.py
  run_queries.py
  run_execution.py
  run_streaming.py
```

或直接：

```text
agentbot/application/
  conversations.py
  runs.py
  streaming_runs.py
```

本阶段建议优先做前者，减少大搬迁。

验收标准：

- API 和 CLI 都经由明确用例入口
- 不再依赖“万能 service 类”

## Phase 4：收口 LangGraph browser adapter

目标：

- 减少 browser 相关大文件的职责缠绕
- 优先解决 LangGraph browser adapter 膨胀问题
- 不为目录迁移而提前拆散已较稳定的 runtime 结构

优先拆分对象：

1. `agentbot/graph/browser_nodes.py`
2. 视需要再处理 `agentbot/browser/session.py`

建议次序：

1. 先拆 `browser_nodes.py`
   - `intent / prepare`
   - `observe`
   - `plan`
   - `act`
   - `evaluate / finish`
   - browser events 与 state update helper
2. 保持 `agentbot/browser/` 现有 runtime 结构不动
3. 只有在 `session.py` 持续频繁变更、且单文件认知成本明显上升时，再轻拆：
   - process launch
   - profile preparation
   - session registry
   - runtime event attachment

验收标准：

- browser graph node 主要负责状态流转，不再堆放大量实现细节
- `agentbot/browser/` 仍与 `browser-use` 的粗粒度分层保持一致
- 普通非 browser 对话与 browser subgraph 行为保持不变

## Phase 5：基础设施归类与 legacy 收口

目标：

- 逐步形成 `infrastructure` 语义
- 清理容易误导的目录命名

候选动作：

- `models/llm.py` -> `infrastructure/llm/factory.py`
- `storage/` -> `infrastructure/storage/`
- `tools/` -> `infrastructure/tools/`
- `config/` -> `infrastructure/config/`
- `memory/` -> `legacy/memory/`

这一阶段不应优先做，必须在 Phase 1-4 稳定后再进行。

验收标准：

- 新人读目录时更容易判断职责
- “核心概念”和“外部实现”分得更开

## 推荐迁移顺序

建议按以下顺序推进，不建议跳步：

1. Phase 0：落蓝图
2. Phase 1：API 与 service 边界收紧
3. Phase 2：执行编排内核收敛
4. Phase 3：service 用例化
5. Phase 4：收口 LangGraph browser adapter
6. Phase 5：基础设施归类与 legacy 收口

原因：

- Phase 1 和 Phase 2 直接降低日常维护成本
- Phase 3 建立稳定演进入口
- Phase 4 风险大，但收益高，且应聚焦 adapter 层而不是整块 browser 包
- Phase 5 更偏目录语义优化，不应抢先

## 每阶段必须保持的验证项

每完成一个 phase，至少验证：

### API

- 能创建 conversation
- 能获取 conversation transcript
- 能发起同步 run
- 能发起流式 run
- 能获取 run steps

### Runtime

- transcript 正常落库
- runs 正常落库
- run_steps 正常落库
- checkpoints 正常写入

### Browser

- 普通非 browser 对话不受影响
- browser intent 仍能正常进入 subgraph
- browser artifacts 仍能生成

## 风险清单

### 1. 目录先搬太多，导致 import 大面积破裂

应对：

- 先收口调用边界，再搬目录

### 2. 抽象执行核心时把同步与流式差异抹平过度

应对：

- 只抽共享骨架，不强行统一所有输出形式

### 3. browser 大文件拆分后出现状态传递断裂

应对：

- 优先保留原有 state shape 和 event shape
- 每拆一块都要跑一次 browser 主链路

### 4. 旧文档与新结构脱节

应对：

- 每完成一阶段就同步更新 architecture 文档

## 明确不建议现在做的事

- 不建议现在引入 ORM 大迁移
- 不建议为了“更标准”而改写 SQLite repository 层
- 不建议把 browser runtime 退回普通 tool
- 不建议重写 LangGraph 主图
- 不建议在未建立统一执行内核前就大规模改目录

## 对当前仓库的最终判断

当前仓库不是“必须重写”，而是“值得做结构收口”。

最有价值的动作不是换框架，而是：

1. 统一业务入口
2. 收掉执行重复
3. 让 graph、browser、storage 各自回到更明确的边界

只要按照本蓝图增量推进，就能在不破坏当前主链路的前提下，把后端整理成更适合长期演进的结构。

## 下一步实施建议

建议从 Phase 1 开始落地：

- 先把 `api/routes` 中直接访问 storage 的逻辑收回 service
- 同时为 `runs` 和 `artifacts` 补齐对应 query service

完成后再进入 Phase 2，统一同步与流式执行内核。
