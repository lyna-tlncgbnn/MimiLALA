# Browser Planner State

## 目标

这份文档描述浏览器子图当前第一阶段 planner state 的职责与边界。

它的目标不是替代 `browser-use` 的完整 agent loop，而是在保留 LangGraph 子图结构的前提下，让浏览器子图更像一个完整 browser agent。

## 当前字段

当前浏览器子图 state 已新增以下 planner state：

- `browser_evaluation_previous_goal`
- `browser_memory`
- `browser_next_goal`
- `browser_progress_signal`
- `browser_consecutive_failures`
- `browser_plan`
- `browser_current_plan_item`
- `browser_plan_generation_step`
- `browser_pending_actions`
- `browser_last_action_results`

## 当前职责

### `browser_evaluation_previous_goal`

用于显式描述上一轮目标是：

- 成功
- 失败
- 不确定
- 已停止

它让 planner 不再默认假设上一步已经成功。

### `browser_memory`

用于记录浏览器子图的短期记忆，例如：

- 当前已经尝试过什么
- 页面阻塞点在哪里
- 已经进入哪个表单/结果区
- 哪些策略失败过

它当前是轻量 browser memory，不是长期记忆系统。

### `browser_next_goal`

用于记录当前这一步的直接目标。

它的作用是让浏览器子图在复杂站点上保持短期任务连续性，而不是每一轮都重新从零猜动作。

### `browser_progress_signal`

由 `browser_evaluate` 产出，用于表达：

- 上一步有没有明显推进任务
- 是否只是页面发生了变化但还未确认任务推进
- 是否已经进入低进展状态

### `browser_consecutive_failures`

用于表达连续低进展/失败次数，帮助 planner 判断：

- 是否继续当前策略
- 是否需要换策略
- 是否应该停止并给出失败结果

## 当前输入输出位置

### 输入到 planner

`agentbot/prompts/browser_subgraph.py` 当前会把这些状态显式注入 planner prompt。

### 输出回子图 state

`agentbot/graph/browser_nodes.py` 里的 `browser_decide` 当前会从模型返回中写回：

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `current_plan_item`
- `plan_update`

`browser_evaluate` 会继续补：

- `progress_signal`
- `consecutive_failures`

同时 `browser_decide` 当前还会注入一组 browser-use 风格的 recovery nudges，用于提醒 planner：

- 是否已经连续低进展
- 是否已经触发 loop detection
- 是否应该换策略而不是继续重复 scroll / wait

## 当前边界

这一步仍然保持以下边界：

- 浏览器 agent 继续是 LangGraph 子图
- planner 输出已经支持 browser-use 风格的 `action: [...]` 动作序列
- 没有迁移完整 browser-use `plan_update / current_plan_item / todo.md / file system` agent loop
- 已迁移 `plan_update / current_plan_item` 的核心 planning 语义
- 仍然没有迁移 browser-use 的 `todo.md / file system` agent loop
- 已引入多动作 browser step，但仍保持 LangGraph 子图编排

## 下一步

planner state 下一阶段更值得做的是：

1. 把 state 真正接进“换策略”逻辑，而不只是记录
2. 把 task-relevance ranking 与 planner state 联动
3. 再评估是否升级成多动作 step
