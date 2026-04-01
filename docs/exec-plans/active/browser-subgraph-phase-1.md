# 执行计划：Browser Subgraph Phase 1

## 状态

ACTIVE

## 背景

当前项目已经具备：

- Electron 桌面壳
- React 前端
- FastAPI 本地服务
- Python Agent 主链路
- 基于 SSE 的 streaming chat
- 基于 LangGraph 的主图工具调用循环

当前图结构仍然是以聊天主链路为核心的最小工具循环，浏览器自动化能力还没有进入项目主流程。

与此同时，仓库同级目录下存在 `F:\browser-use` 项目。该项目已经提供了比较完整的浏览器执行层能力，包括：

- 浏览器会话管理
- DOM 抽取与序列化
- 页面状态摘要
- 浏览器动作注册与执行
- 事件驱动的浏览器底层能力

但 `browser-use` 自身也包含完整的 agent loop。对于本仓库来说，第一阶段不应直接复用它的 agent loop，而应保留 LangGraph 作为主编排层，只复用 `browser-use` 的浏览器执行层。

## 第一阶段目标

第一阶段的单一目标是：

**构建一个最小可运行的 LangGraph 浏览器子图，并复用 `browser-use` 的浏览器执行层完成页面观察与基础动作执行。**

这里的“最小可运行”具体指：

- 主图可以进入浏览器子图
- 浏览器子图可以启动浏览器会话
- 浏览器子图可以观察当前页面状态
- 浏览器子图可以规划并执行最小动作集
- 浏览器子图可以返回最终结果
- 现有 CLI / FastAPI / SSE 主链路不被破坏

## 第一阶段不做什么

为了把阶段边界收紧，以下内容明确不在本阶段内：

- 不引入 `browser-use` 自己的 `Agent.run()` 主循环
- 不做完整 multi-agent orchestration
- 不做多个 browser subgraph 并发
- 不做 checkpointer
- 不做 long-term memory
- 不做 execution 可视化面板
- 不做 browser session persistence
- 不做复杂 extraction / schema extraction
- 不做 human-in-the-loop approval
- 不做多 tab 调度策略
- 不做 gif / replay / judge
- 不做完整自动化测试体系

## 设计原则

本阶段遵循以下原则：

1. LangGraph 负责 orchestration，`browser-use` 负责 browser runtime。
2. 子图先独立封装，不与主图共享复杂状态。
3. state 只存可序列化数据，不直接存第三方运行时对象。
4. prompt 在节点内即时生成，不把大段 prompt 文本持久写入 state。
5. 先做最小动作集，优先打通链路，再逐步增强。
6. 保持现有主图、runner、streaming runner 的可读性。

## 官方资料依据

本计划主要参考以下资料：

- LangGraph `Subgraphs`
- LangGraph `Graph API`
- LangGraph `Streaming`
- LangGraph `Thinking in LangGraph`
- `browser-use` 中的 `BrowserSession`、`DomService`、`Tools`

这些资料支撑了本阶段的几个核心决策：

- 使用真正的 LangGraph 子图，而不是在单个节点里塞一个黑盒浏览器 agent
- 父图与子图先采用“包装节点调用子图”的方式对接
- state 使用独立 typed state
- streaming 先接节点级更新，不追求一开始就做浏览器动作级细粒度事件

## 核心决策

### 1. 保留 LangGraph 作为唯一编排层

本阶段不直接使用 `browser-use` 的 agent loop。

原因：

- 本仓库已经有自己的 LangGraph 主链路
- 如果复用 `browser-use` 的 agent loop，会产生双重编排层
- 这样会削弱子图状态可观测性
- 也会让后续 SSE、execution logs、可视化更难对齐

因此，本阶段只复用 `browser-use` 的执行层。

### 2. 先做独立浏览器子图

浏览器能力不是先扩展成“主图里的一组 browser tools”，而是先落成一个独立子图。

原因：

- 浏览器任务天然是多步流程
- 需要保留中间状态
- 后续要扩展 execution 可视化与 streaming 时，子图比工具集更自然
- 主聊天链路也不需要直接面对大量低级浏览器动作

### 3. 父图与子图通过包装节点连接

第一阶段不让父图和浏览器子图共享完整状态结构。

推荐方式：

- 主图增加一个包装节点
- 包装节点组装浏览器子图输入
- 调用浏览器子图
- 把子图结果转换回主图可消费结果

这样能把第一阶段的风险控制在浏览器功能域内。

### 4. 子图 state 使用 typed state

浏览器子图不继续沿用纯 `MessagesState`。

原因：

- 浏览器流程需要显式表达页面状态、动作、动作结果、步骤计数、会话 id
- 如果全部塞进 messages，后续维护和 streaming 会快速变乱

因此本阶段新增独立的浏览器子图 state。

## browser-use 复用范围

第一阶段优先复用以下能力。

### 1. 浏览器会话层

来源：

- `F:\browser-use\browser_use\browser\session.py`
- `F:\browser-use\browser_use\browser\views.py`

重点接口：

- `BrowserSession.start()`
- `BrowserSession.kill()`
- `BrowserSession.get_browser_state_summary()`
- `BrowserSession.get_selector_map()`
- `BrowserSession.get_tabs()`

用途：

- 启动和关闭浏览器
- 获取当前聚焦 tab
- 获取页面与 tab 摘要
- 获取 selector map

### 2. DOM 观察层

来源：

- `F:\browser-use\browser_use\dom\service.py`

重点接口：

- `DomService.get_serialized_dom_tree()`

用途：

- 获取序列化 DOM
- 获取增强 DOM 结构
- 为后续 prompt 构建提供页面观察数据

### 3. 动作执行层

来源：

- `F:\browser-use\browser_use\tools\service.py`
- `F:\browser-use\browser_use\tools\views.py`

重点接口：

- `Tools.act(...)`

第一阶段重点动作模型：

- `NavigateAction`
- `ClickElementActionIndexOnly`
- `InputTextAction`
- `DoneAction`

用途：

- 用统一入口执行最小动作集
- 复用现成的浏览器事件分发与错误处理

## browser-use 明确不复用的部分

第一阶段不直接复用以下模块作为主逻辑：

- `F:\browser-use\browser_use\agent\service.py`
- `F:\browser-use\browser_use\agent\prompts.py`
- `F:\browser-use\browser_use\agent\message_manager\...`
- `F:\browser-use\browser_use\agent\judge.py`
- `F:\browser-use\browser_use\agent\gif.py`
- `F:\browser-use\browser_use\agent\cloud_events.py`

原因是这些模块已经承担了 agent orchestration 职责，与本仓库的 LangGraph 编排职责重叠。

## 第一阶段最小动作集

第一阶段只支持 4 类动作：

1. `navigate`
2. `click`
3. `input`
4. `done`

动作选择依据：

- `navigate` 用于起始导航与错误恢复
- `click` 是最基本页面推进动作
- `input` 是最基本表单动作
- `done` 用于子图退出

暂不纳入第一批的动作：

- `scroll`
- `wait`
- `extract`
- `switch_tab`
- `close_tab`
- `upload_file`
- `select_dropdown`

这些动作都可以放到 Phase 1 后半段或下一阶段。

## 浏览器子图状态模型

第一阶段建议新增 `BrowserSubgraphState`，字段先控制在最小必要范围。

建议字段：

- `task: str`
- `start_url: str | None`
- `current_url: str | None`
- `page_title: str | None`
- `browser_session_id: str | None`
- `step_count: int`
- `max_steps: int`
- `status: str`
- `browser_state_summary: dict | None`
- `selector_map_digest: str | None`
- `last_action: dict | None`
- `last_action_result: dict | None`
- `final_response: str | None`
- `error_message: str | None`

补充说明：

- state 中不直接保存 `BrowserSession` 对象
- state 中不直接保存完整增强 DOM 对象
- state 中只保存节点间需要共享的可序列化摘要

## 运行时对象管理策略

由于 `BrowserSession` 和相关运行时对象不适合直接进入 LangGraph state，本阶段新增一层运行时封装。

建议新增：

- `agentbot/services/browser_runtime.py`

这一层负责：

- 创建和关闭 `BrowserSession`
- 管理 session id 到会话对象的映射
- 提供统一的 `observe()` 与 `execute_action()` 封装
- 隔离 `browser-use` 具体实现细节

这是第一阶段非常关键的边界。

## 文件级落地方案

第一阶段建议新增以下文件。

### 1. `agentbot/graph/browser_state.py`

职责：

- 定义浏览器子图 state 类型
- 定义浏览器计划动作的结构化模型

### 2. `agentbot/graph/browser_nodes.py`

职责：

- 放置浏览器子图所有节点
- 每个节点只负责一个明确步骤

### 3. `agentbot/graph/browser_routes.py`

职责：

- 定义浏览器子图条件路由
- 例如 `continue` / `finish` / `error`

### 4. `agentbot/graph/browser_builder.py`

职责：

- 构建浏览器子图
- 编译成可被主图调用的 graph

### 5. `agentbot/services/browser_runtime.py`

职责：

- 封装 `browser-use` 运行时对象
- 统一暴露：
  - `create_session`
  - `observe`
  - `execute_action`
  - `close_session`

### 6. `agentbot/models/browser.py`

职责：

- 放置浏览器动作计划的 Pydantic 模型
- 放置浏览器子图最终输出模型

### 7. 视情况新增 `agentbot/integrations/browser_use/adapter.py`

第一阶段可选。

如果接入过程发现第三方耦合开始变重，再补这层适配；否则先用 `browser_runtime.py` 直接封装即可。

## 子图节点设计

第一阶段只构建 5 个节点。

### 1. `browser_enter`

职责：

- 初始化浏览器 session
- 建立 session id
- 初始化 step 计数和状态

输入：

- `task`
- `start_url`
- `max_steps`

输出：

- `browser_session_id`
- `status="running"`
- `step_count=0`

### 2. `browser_observe`

职责：

- 读取当前页面状态
- 提取最小页面摘要
- 生成供 LLM 规划使用的结构化页面上下文

建议调用：

- `BrowserSession.get_browser_state_summary()`
- 必要时 `DomService.get_serialized_dom_tree()`

输出建议包括：

- `current_url`
- `page_title`
- `browser_state_summary`
- `selector_map_digest`

### 3. `browser_plan`

职责：

- 基于任务和当前页面状态，生成下一步结构化动作

动作限制：

- `navigate`
- `click`
- `input`
- `done`

要求：

- `click` 和 `input` 必须基于当前可见 selector map index
- 如果任务已完成或无法继续，应返回 `done`

### 4. `browser_act`

职责：

- 将 `browser_plan` 产出的结构化动作转换为 `browser-use` 动作
- 调用 `Tools.act(...)`
- 记录动作结果

输出：

- `last_action`
- `last_action_result`
- `step_count += 1`

### 5. `browser_finish`

职责：

- 汇总最终结果
- 根据策略关闭 session
- 输出子图最终结果

输出：

- `final_response`
- `status="completed"` 或 `status="failed"`
- `error_message`

## 子图路由设计

推荐路由：

- `browser_enter -> browser_observe`
- `browser_observe -> browser_plan`
- `browser_plan -> browser_finish`
  条件：动作类型是 `done`
- `browser_plan -> browser_act`
  条件：动作类型是 `navigate/click/input`
- `browser_act -> browser_finish`
  条件：动作失败且不可恢复
- `browser_act -> browser_finish`
  条件：达到 `max_steps`
- `browser_act -> browser_observe`
  条件：继续执行

第一阶段不引入更复杂的 planner / assessor 双层规划结构。

## 主图接入方案

第一阶段不重做主图主循环，只增加一层包装调用。

建议方式：

1. 在主图中新增一个 `call_browser_subgraph` 包装节点
2. 该节点负责：
   - 识别浏览器任务输入
   - 组装浏览器子图输入
   - 调用浏览器子图
   - 把子图输出转换回主图可用结果

第一阶段可以先用非常直接的方式接入：

- 显式入口或显式 tool / service 调用触发

如果主图当前还不适合自动 route 到浏览器子图，也可以先在服务层做显式调用，等链路跑通后再接主图自动路由。

## Prompt 与动作规划策略

第一阶段 prompt 应该尽量收敛，目标是减少模型胡乱操作。

建议规则：

- 只允许输出最小动作集
- 只允许输出单步动作
- 不做多动作 batch
- 不做模糊动作描述
- index 必须来自当前页面摘要
- 如果页面与任务不匹配或缺少可执行目标，优先 `done` 并说明原因

第一阶段不追求“聪明”，追求“可控”。

## Streaming 策略

第一阶段只接节点级 streaming。

建议：

- 继续使用现有 streaming runner 主链路
- 浏览器子图输出先通过节点级 state update 暴露
- 不额外引入浏览器动作级 custom stream writer

原因：

- 节点级 streaming 已足够验证子图是否能接入现有 SSE
- 动作级细流可以放在后续阶段增强

## Execution Logging 策略

第一阶段只记录必要执行摘要，不在此阶段重做完整浏览器事件日志模型。

建议记录：

- 浏览器子图启动
- 当前页面 URL / title
- 本轮计划动作
- 动作执行结果
- 子图结束状态

这样做的目标是先保证主执行日志中能看见浏览器子图存在和主要步骤。

## 验收标准

第一阶段完成后，至少应满足以下验收条件。

### 最小功能验收

- 可以启动浏览器 session
- 可以观察当前页面状态
- 可以执行一次 `navigate`
- 可以执行一次 `click`
- 可以执行一次 `input`
- 可以通过 `done` 正常退出子图

### 主链路验收

- CLI 不被破坏
- FastAPI 不被破坏
- 现有 streaming chat 主链路不被破坏
- execution logs 中可以看见浏览器子图的关键节点执行摘要

### 结构验收

- LangGraph 仍然是唯一编排层
- `browser-use` 没有被整包作为黑盒 agent 引入
- 浏览器运行时对象没有直接进入 graph state

## 实施顺序

建议按下面顺序执行。

### Step 1

定义浏览器子图的数据模型。

产出：

- `browser_state.py`
- `models/browser.py`

### Step 2

实现 `browser_runtime.py`，封装最小运行时能力。

产出：

- session 创建与回收
- 页面观察封装
- 动作执行封装

### Step 3

实现浏览器子图节点与路由。

产出：

- `browser_nodes.py`
- `browser_routes.py`
- `browser_builder.py`

### Step 4

让子图在本地最小场景跑通。

最小场景建议：

- 打开指定 URL
- 观察页面
- 执行一次导航或点击
- 返回结果

### Step 5

把子图接入主图或服务入口。

要求：

- 尽量少改现有主图
- 优先使用包装节点或服务层集成

### Step 6

接入最小 streaming 与 execution logging。

### Step 7

补文档更新。

建议同步更新：

- `README.md`
- `docs/architecture/graph-flow.md`
- 新增 browser integration 架构文档或更新现有 architecture 文档

## 风险与应对

### 风险 1：browser-use 依赖较重

表现：

- 初始集成较慢
- 环境问题较多

应对：

- 第一阶段只接入最小模块
- 优先验证本地浏览器启动与单页面操作

### 风险 2：selector index 不稳定

表现：

- 页面变化后 click / input 可能失败

应对：

- 每一轮动作前都重新观察页面
- 第一阶段不做复杂重试策略

### 风险 3：session 对象不可序列化

表现：

- 如果直接进入 graph state，会导致状态问题

应对：

- 始终通过 `browser_runtime.py` 管理运行时对象
- state 中只放 `browser_session_id`

### 风险 4：一次性做太多动作导致链路不稳

应对：

- 第一阶段只保留最小动作集
- 一次只计划一步动作

## 阶段完成后的下一步

当第一阶段完成后，最自然的下一步是：

**增强浏览器子图的可执行动作与可观测性。**

下一阶段优先候选包括：

- `scroll`
- `wait`
- `extract`
- 更细粒度 streaming
- 更明确的 browser execution events
- 更稳的页面重观察与重试策略
- 主图自动 route 到浏览器子图

## 本计划的完成定义

当以下条件同时成立时，本计划可视为完成：

- 浏览器子图已在 LangGraph 中构建完成
- 已接入 `browser-use` 的最小执行层能力
- 至少一个最小浏览器任务可跑通
- 主链路未回归
- 文档已同步

## 相关参考

- `F:\browser-use\browser_use\browser\session.py`
- `F:\browser-use\browser_use\browser\views.py`
- `F:\browser-use\browser_use\dom\service.py`
- `F:\browser-use\browser_use\tools\service.py`
- `F:\browser-use\browser_use\tools\views.py`
- `https://docs.langchain.com/oss/python/langgraph/use-subgraphs`
- `https://docs.langchain.com/oss/python/langgraph/graph-api`
- `https://docs.langchain.com/oss/python/langgraph/streaming`
- `https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph`
