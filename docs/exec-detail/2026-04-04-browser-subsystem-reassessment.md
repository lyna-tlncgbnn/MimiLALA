# 2026-04-04 Browser Subsystem Reassessment

## 背景

在完成 backend reorganization 的 Phase 1-3 后，原蓝图中的 Phase 4 计划继续拆分 browser 子系统：

- `agentbot/browser/session.py`
- `agentbot/browser/actions.py`
- `agentbot/graph/browser_nodes.py`

但在真正执行前，需要先确认这一步是否仍然必要，以及拆分方向是否准确。

## 本次评估方法

本次重新对照了同级参考项目 `browser-use`，重点查看：

- `browser_use/browser/session.py`
- `browser_use/browser/session_manager.py`
- `browser_use/agent/service.py`
- `browser_use/browser/watchdogs/*`

同时对照 AgentBot 当前结构：

- `agentbot/browser/session.py`
- `agentbot/browser/actions.py`
- `agentbot/browser/observation_capture.py`
- `agentbot/browser/runtime/watchdogs/*`
- `agentbot/graph/browser_nodes.py`

## 评估结论

结论不是“browser 子系统不需要治理”，而是：

1. `agentbot/browser/` 当前整体组织并没有明显偏离 `browser-use`
2. 当前最需要收口的不是整个 browser 包，而是 LangGraph browser adapter
3. 原蓝图中的 Phase 4 需要收窄，而不是照原方案整块展开

## 为什么说 `agentbot/browser/` 方向基本正确

对照 `browser-use` 后，可以看到粗粒度映射关系已经成立：

- `agentbot/browser/runtime/` 对应 browser runtime / watchdog 这一层
- `agentbot/browser/session.py` 对应 browser session lifecycle
- `agentbot/browser/actions.py` 对应 browser action execution
- `agentbot/browser/observation_*` 对应 DOM / observation capture 与 serialization

换句话说，AgentBot 不是“browser 目录组织错了”，而是已经基本采用了参考项目的思路，只是把 agent loop 换成了 LangGraph。

## 真正的问题点

当前最重的文件不是 `agentbot/browser/` 下面的 runtime 结构本身，而是：

- `agentbot/graph/browser_nodes.py`

这个文件承载了过多 LangGraph browser adapter 职责，包括：

- browser intent detection
- browser prepare
- observation 调度
- planner prompt 组装
- action execution 编排
- browser event 汇总
- graph state update
- finish / failure / timeline event 组织

这说明当前最需要拆细的是“graph 到 browser runtime 的适配层”，而不是为了目录规整去优先拆 runtime。

## 对 `session.py` 的判断

`agentbot/browser/session.py` 当前体量较大，但它的大部分职责仍然属于同一层：

- process launch
- profile preparation
- session registry
- runtime event / watchdog wiring

这类组织方式与 `browser-use` 的 `browser/session.py` 并不冲突。
因此它是“可轻拆”，但不是“必须先拆”。

## 对蓝图的调整

原蓝图中的 Phase 4 调整为：

- 先拆 `agentbot/graph/browser_nodes.py`
- 保持 `agentbot/browser/` 现有 runtime 结构稳定
- 仅在后续需要时，再轻拆 `agentbot/browser/session.py`

## 执行建议

后续若继续推进 Phase 4，建议分成两步：

1. Phase 4A：LangGraph browser adapter 拆分
   - intent / prepare
   - observe
   - plan
   - act
   - evaluate / finish
   - shared helpers
2. Phase 4B：按需轻拆 `session.py`
   - process launch
   - profile preparation
   - registry
   - runtime attachment

## 最终判断

原计划中的“browser 子系统拆分”有必要调整口径。

更准确的实施方向应是：

- 不大拆 `agentbot/browser/`
- 优先收口 `agentbot/graph/browser_nodes.py`
- 保持与 `browser-use` 的粗粒度结构对齐
