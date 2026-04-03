# 执行计划：Browser Subgraph 集成 Phase 1

## 状态

ACTIVE

## 背景

当前 AgentBot 已经具备：

- Electron + React + FastAPI + Python Agent Runtime 主链路
- run-oriented execution 模型
- `runs / run_steps / checkpoints` 持久化
- 流式执行与执行时间线展示

接下来的目标不是把浏览器能力作为一组零散 tools 直接挂到主 agent，而是引入一个：

- 结构清晰
- 可观察
- 可扩展
- 适合后续 interrupt / approval 演进

的浏览器子 agent。

结合前期调研，本阶段采用：

- `LangGraph browser subgraph`

而不是：

- 主 agent 直接持有完整 browser tools
- browser 子 agent 作为隐藏在 tool 内部的黑盒

## 选型结论

### 总体方案

采用：

- 主图负责任务总控
- browser 子图负责浏览器域执行
- 子图内部自行执行 `observe / decide / act / evaluate`
- 子图中间过程直接写统一的 `run_steps`
- 子图结果摘要返回主图

### 为什么选 subgraph

这个方案最符合当前项目现状：

- 已有 LangGraph
- 已有 run-oriented execution
- 已有 checkpoint 持久化
- 前端已经具备 execution timeline

同时也更符合官方建议：

- LangGraph subgraph 默认支持 per-invocation 持久化
- 子图会继承父图 checkpointer
- 适合 multi-agent / specialist graph

### 为什么不选“浏览器 tools 直接挂主 agent”

不采用该方案的原因：

- 主 agent 上下文容易被浏览器状态污染
- browser tools 数量多，调度复杂
- 中间步骤和页面状态难以形成明确边界
- 后续做 approval / interrupt 更难演进

### 为什么不把 browser agent 包成普通 tool

不采用该方案的原因：

- LangGraph 对隐藏在 tool 内部的子 agent 状态可见性较弱
- 不利于后续 checkpoint 调试
- 不利于显式展示 browser 子图中间执行层级

## 参考来源与借鉴边界

### LangGraph / LangChain 官方方向

本阶段重点参考：

- LangGraph Subgraphs
- LangGraph Persistence
- LangGraph Durable Execution
- LangChain Subagents / Multi-agent

结论：

- 子图内部状态应独立
- 执行持久化不必另起一套系统
- 子图过程应通过统一执行日志和 checkpoint 体系观察

### `browser-use` 借鉴范围

参考项目：

- `F:\browser-use`

本阶段借鉴：

- `browser/session.py`
  持久浏览器会话设计思路
- `browser/views.py`
  `BrowserStateSummary`、`TabInfo`、`PageInfo`
- `browser/events.py`
  浏览器动作边界建模
- `dom/service.py`
  DOM 快照与页面观察层设计
- `dom/enhanced_snapshot.py`
  必要样式抽取、快照优化
- `agent/views.py`
  loop detection / page stagnation detection

本阶段不迁移：

- `browser-use` 自身 Agent 主循环
- 其完整 controller / tool registry 体系
- cloud browser / watchdog / telemetry / skill_cli

原则是：

- 借“浏览器执行内核”
- 不借“它自己的大脑”

## 本阶段目标

Phase 1 的目标不是一次性做完整 browser automation framework，而是先把：

1. browser subgraph 骨架
2. browser state 模型
3. browser 执行步骤落库机制
4. 第一批 browser 动作
5. 前端可见的 browser timeline

跑通。

## 核心架构

### 执行层级

```text
Main Graph
  -> regular nodes
  -> browser_subgraph node
       -> browser_prepare
       -> browser_observe
       -> browser_decide
       -> browser_act
       -> browser_evaluate
       -> browser_finish
  -> regular nodes
```

对主图来说：

- browser 子图是一个 specialist node

对 browser 子图内部来说：

- 它本身是一个独立 graph
- 有自己的 state 和节点循环

### 数据流分层

分为三条数据线：

1. 主图 <-> 子图运行时结果线
   - 只传摘要结果
2. 子图 -> storage 执行记录线
   - 及时写 `run_steps / artifacts`
3. storage -> frontend 展示线
   - 前端主要读取落地后的执行数据

### 关键原则

- 主图拿结果，不拿全部内部细节
- 子图过程直接写库，不通过主图转述
- 前端看 `run_steps / artifacts`
- checkpoint 用于恢复，不是前端主展示来源

## 子图 state 设计

建议新增 browser 专属 state 模型，至少包含：

- `browser_task`
- `browser_goal`
- `browser_session_id`
- `browser_current_url`
- `browser_state_summary`
- `browser_last_observation`
- `browser_action_history`
- `browser_failures`
- `browser_done`
- `browser_result`
- `browser_requires_approval`
- `browser_pending_action`
- `browser_loop_signal`
- `browser_parent_step_id`

### 主图传入字段

- `run_id`
- `conversation_id`
- `browser_task`
- `browser_parent_step_id`
- 必要的用户目标描述

### 子图返回字段

- `browser_status`
- `browser_result`
- `browser_summary`
- `browser_artifact_ids`
- `browser_error`

## 数据存储方案

### 总体原则

browser 子图的执行数据：

- 不单独新建 `browser_runs`
- 继续复用主链路的 `runs / run_steps / checkpoints`

### 为什么不单独建 browser run 主表

原因：

- 用户视角仍然是一个任务，而不是两套任务
- 前端 timeline 更容易统一展示
- checkpoint 恢复不会裂成两套执行体系
- approval / interrupt 语义更清晰

### `run_steps` 扩展方向

建议扩展字段：

- `step_scope`
  - `main`
  - `browser`
- `parent_step_id`
- `step_kind`
- `metadata_json`

### `metadata_json` 建议字段

- `browser_session_id`
- `url`
- `title`
- `tab_id`
- `action_type`
- `element_index`
- `element_hint`
- `loop_signal`
- `requires_approval`

### artifacts 方案

浏览器重资产不直接塞进 step 文本，优先作为 artifact：

- screenshot
- extracted page text
- DOM snapshot summary
- later: downloaded files

artifact 通过：

- `run_id`
- `step_id`

关联回 timeline。

### checkpoint 方案

继续使用现有 LangGraph SQLite checkpointer：

- 主图和子图共享同一套 checkpointer
- 用 subgraph namespace 区分主图与 browser 子图

## 前端展示要求

本阶段明确要求：

- browser 子图的中间核心步骤，前端必须实时可见

### 实现原则

browser 子图内部每个“用户可理解的动作”都要及时写 step，例如：

- 进入浏览器任务
- 打开网址
- 页面观察
- 点击元素
- 输入文本
- 滚动页面
- 切换标签页
- 提取信息
- 出错 / 重试
- 浏览器任务完成

### 不必直接展示为 timeline 的内部细节

- DOM hash 变化
- loop detector 内部计数
- visibility 过滤细节
- 原始 snapshot 中间结构

这些作为内部 state 或 artifact 辅助信息即可。

## 浏览器能力边界

### 第一版动作集合

建议第一版只做：

- `browser_navigate`
- `browser_snapshot`
- `browser_click`
- `browser_type`
- `browser_scroll`
- `browser_wait`
- `browser_go_back`
- `browser_switch_tab`
- `browser_extract_text`
- `browser_screenshot`

### 第一版暂不做

- 上传文件
- 复杂 dropdown
- 拖拽
- PDF 保存
- 自动下载管理
- captcha
- cloud browser
- 跨任务登录态复用

## 目录与模块建议

建议新增目录：

```text
agentbot/
  browser/
    __init__.py
    session.py
    views.py
    events.py
    dom_service.py
    actions.py
    loop_detection.py
    artifacts.py
  graph/
    browser_subgraph.py
    browser_nodes.py
    browser_routes.py
```

### 模块职责建议

- `session.py`
  浏览器会话管理
- `views.py`
  browser state / tab / page / action 数据模型
- `events.py`
  浏览器动作事件边界
- `dom_service.py`
  页面观察、snapshot、可点击元素提取
- `actions.py`
  低层浏览器动作执行
- `loop_detection.py`
  页面停滞与循环检测
- `artifacts.py`
  screenshot / extraction artifact 封装
- `browser_subgraph.py`
  子图装配入口
- `browser_nodes.py`
  子图节点实现
- `browser_routes.py`
  子图内部条件路由

## 节点设计

### `browser_prepare`

职责：

- 初始化 browser task
- 创建或绑定 session
- 写入 browser 父 step

### `browser_observe`

职责：

- 获取当前 `BrowserStateSummary`
- 生成页面摘要
- 写入观察 step

### `browser_decide`

职责：

- 根据当前 browser state 决定下一步动作
- 产出结构化 `BrowserAction`

### `browser_act`

职责：

- 执行动作
- 写入 action step
- 捕获错误和超时

### `browser_evaluate`

职责：

- 更新 loop detector
- 判断是否完成
- 判断是否需要继续观察 / 重试 / 结束

### `browser_finish`

职责：

- 汇总 browser 结果
- 生成返回主图的摘要字段
- 写入 browser 完成 step

## 分阶段实施

### Phase 1A：骨架与数据流

目标：

- 建立 browser 子图最小骨架
- 跑通主图 -> browser 子图 -> 主图
- 确认 `run_steps` 可承接 browser scope

内容：

- 新增 browser 目录和 state 模型
- 新增 browser 子图装配
- 新增最小节点：`prepare / observe / finish`
- 主图能切入和退出 browser 子图
- 写入 browser 基础 steps

### Phase 1B：最小动作能力

目标：

- 让 browser 子图能做最基础网页访问与页面读取

内容：

- 基于 Playwright 的 `browser_navigate`
- 基于 Playwright 的 `browser_snapshot`
- 基于 Playwright 的 `browser_extract_text`
- 基于 Playwright 的 `browser_screenshot`
- 初版 `BrowserStateSummary`
- 最小 `dom_service` 页面观察层

状态：

- 已完成

### Phase 1C：基础交互

目标：

- 让 browser 子图具备基础交互闭环

内容：

- `browser_click`
- `browser_type`
- `browser_scroll`
- `browser_wait`
- `browser_go_back`
- `browser_switch_tab`

状态：

- 已完成

### Phase 1D：执行可观察性增强

目标：

- 让 browser 执行过程更适合 timeline 和恢复

内容：

- `step_scope`
- `parent_step_id`
- browser artifacts
- loop detection
- 更细的错误边界

状态：

- 已完成

### Phase 1E：安全与后续扩展预留

目标：

- 为 approval / interrupt 演进打基础

内容：

- `requires_approval` 预留
- 敏感动作分类
- browser session 生命周期边界
- artifact 类型扩展点

状态：

- 已完成

## 风险与注意点

### 1. 不要把主 agent 变成浏览器调度器

browser 细节留在子图内部，主图只负责任务层级调度。

### 2. 不要把整页 HTML 原样塞给模型

优先结构化 snapshot 与可点击元素摘要。

### 3. 不要把 browser 子图步骤延迟到结束后再统一写库

必须边执行边写 step，否则前端无法实时显示。

### 4. 不要一开始就做跨 run 浏览器会话复用

先把单次 run 内会话复用跑通。

### 5. 不要一开始就做完整 browser-use 迁移

只借关键内核层，保持 AgentBot 主链路主导。

## 本阶段完成标准

本计划阶段完成后，至少满足：

1. 主图可以进入 browser 子图
2. browser 子图拥有独立 state
3. browser 子图中间步骤能实时写入 `run_steps`
4. 前端可以看到 browser scope 的执行步骤
5. browser 子图结束后能把摘要结果回传主图
6. checkpoint 恢复不需要另起 browser 持久化体系

## 后续执行规则

后续执行时遵守：

- 先实现骨架和数据流，再补动作
- 每完成一个阶段，补 `exec-detail`
- 修改数据结构或执行流程后，及时更新架构文档
- 优先保持主链路可运行，不一次性引入过多 browser 复杂能力
