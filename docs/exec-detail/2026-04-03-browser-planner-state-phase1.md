# 2026-04-03 Browser Planner State Phase 1

## 背景

browser observation 分层落地后，浏览器子图仍然偏像“单步动作选择器”，而不是完整 browser agent。

对照 `browser-use`，当前缺口主要在 planner state：

- 没有显式 `evaluation_previous_goal`
- 没有轻量 `memory`
- 没有明确 `next_goal`
- 没有稳定的 progress / failure 信号

这会导致复杂站点上容易退化成低价值动作，比如反复 scroll / wait。

## 本次改动

### 1. 扩展浏览器子图 state

更新：

- `agentbot/graph/state.py`

新增字段：

- `browser_evaluation_previous_goal`
- `browser_memory`
- `browser_next_goal`
- `browser_progress_signal`
- `browser_consecutive_failures`

### 2. 升级 browser planner prompt

更新：

- `agentbot/prompts/browser_subgraph.py`

现在 planner prompt 会显式接收：

- previous goal evaluation
- planner memory
- current next goal
- progress signal
- consecutive failures
- prioritized page hints
- semantic groups

同时要求模型在 JSON 中返回：

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- 单个 `action`

### 3. 升级 browser_decide

更新：

- `agentbot/graph/browser_nodes.py`

`browser_decide` 不再只产出动作，还会把：

- `evaluation_previous_goal`
- `memory`
- `next_goal`

并且继续往 `browser-use` 对齐，补上了：

- `current_plan_item`
- `plan_update`

子图内部现在已经会维护：

- `browser_plan`
- `browser_current_plan_item`
- `browser_plan_generation_step`

一起写回子图 state 和 step output。

### 4. 升级 browser_evaluate

`browser_evaluate` 现在会额外生成：

- `browser_progress_signal`
- `browser_consecutive_failures`

用于后续步骤判断：

- 上一步是否真的推进了任务
- 是否已经进入低进展 / 连续失败状态

### 4.1 注入 recovery / replan nudges

本次又继续补了一层更贴近 `browser-use` 的 planner context 注入：

- 当连续低进展达到阈值时，给 planner 注入 `REPLAN SUGGESTED`
- 当 loop signal 出现时，给 planner 注入 `LOOP DETECTION`
- 当 progress signal 说明页面变化有限时，给 planner 注入 `PROGRESS CHECK`

这层不是硬编码具体任务控件，而是把“该不该换策略”的判断显式交给 planner。

### 5. 让 action history 保留 planner context

`browser_act` 和失败兜底路径里，写入 action history 时也会带上：

- `evaluation_previous_goal`
- `memory`
- `next_goal`

这样后续 planner 可以看到的不只是“做过什么动作”，还能看到“当时为什么这么做”。

## 边界

本次没有改：

- 浏览器 agent 仍然是 LangGraph 子图
- 仍然保持单动作 `BrowserAction` 协议
- 没有引入多动作 step
- 没有把浏览器 runtime 改造成完整 event bus / watchdog 架构

## 验证

执行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

另外做了轻量检查：

- planner fallback 现在会返回 `evaluation_previous_goal / memory / next_goal / action`
- planner prompt 已包含 planner state 与 observation hints
- progress signal helper 可正常生成字符串

## 下一步

下一阶段更值得做的是：

1. 把 planner state 真正用于“换策略”而不只是“记下来”
2. 增强 task-relevance ranking，继续压低站点导航元素的优先级
3. 再评估是否把表单任务升级成多动作 step
