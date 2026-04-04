# 2026-04-04 Backend Reorganization Phase 4A Browser Adapter Split

## 目标

执行调整后的 Phase 4A：

- 不大拆 `agentbot/browser/` runtime
- 优先收口 `agentbot/graph/browser_nodes.py`
- 把 LangGraph browser adapter 中的纯决策、执行、评估和公共 helper 拆出

## 本次改动

新增模块：

- `agentbot/graph/browser_nodes_common.py`
- `agentbot/graph/browser_nodes_decide.py`
- `agentbot/graph/browser_nodes_act.py`
- `agentbot/graph/browser_nodes_evaluate.py`

保留在 `agentbot/graph/browser_nodes.py` 的内容：

- browser intent detection
- browser prepare / observe
- browser finish
- browser step failure payload 组装
- 对新模块的 safe wrapper

## 调整后的职责分布

### `browser_nodes_common.py`

承载公共 helper：

- browser keyword / URL / task 提取
- timeline timestamp
- browser state summary 反序列化
- action summary / sequence summary
- progress signal / completion assessment
- planner 输入解析所需的基础工具

### `browser_nodes_decide.py`

承载规划阶段逻辑：

- `browser_decide`
- planner prompt 调用
- planner JSON 解析
- fallback planning
- plan update / current item 更新

### `browser_nodes_act.py`

承载执行阶段逻辑：

- `browser_act`
- action sequence 执行
- screenshot 注入结果
- action history 记录
- action 失败结果构造

### `browser_nodes_evaluate.py`

承载评估阶段逻辑：

- `browser_evaluate`
- progress signal 更新
- action budget 推进
- consecutive failure 统计

## 结果

`agentbot/graph/browser_nodes.py` 从原先的大文件收缩到更聚焦的 adapter 装配层。

本次调整后：

- `browser_nodes.py` 为 502 行
- `browser_nodes_decide.py` 为 357 行
- `browser_nodes_common.py` 为 337 行

核心收益不是“总行数减少”，而是：

- graph 层文件不再同时承载所有 browser helper
- planning / acting / evaluating 的改动点更清晰
- 后续如果继续推进 Phase 4B，可以独立评估 `session.py`，不会再和 graph adapter 缠在一起

## 未在本阶段处理的内容

以下内容刻意未动：

- `agentbot/browser/session.py`
- `agentbot/browser/actions.py`
- `agentbot/browser/runtime/`
- browser state shape
- browser events shape
- browser subgraph 路由结构

## 验证

本次至少验证：

- `py_compile` 可通过：
  - `agentbot/graph/browser_nodes.py`
  - `agentbot/graph/browser_nodes_common.py`
  - `agentbot/graph/browser_nodes_decide.py`
  - `agentbot/graph/browser_nodes_act.py`
  - `agentbot/graph/browser_nodes_evaluate.py`
- FastAPI app 仍可正常导入
- browser node safe wrapper 入口可正常导入

## 判断

这一步符合调整后的蓝图口径：

- 拆的是 LangGraph browser adapter
- 没有误拆与 `browser-use` 已经对齐的 runtime 结构
- 为后续是否继续处理 `session.py` 留出了更清晰的决策边界
