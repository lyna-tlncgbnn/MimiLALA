# 2026-04-03 Browser Multi-Action Step Alignment

## 背景

浏览器子图此前仍然使用单动作 `BrowserAction` 协议：

- planner 每轮只返回一个动作
- runtime 每轮只执行一个动作
- `browser_pending_action` / `browser_last_action_result` 都是单条结构

这和 `browser-use` 的核心 step 语义还有明显差距。`browser-use` 的 planner 输出是 `action: [...]`，并且会在顺序执行时因为页面变化中断剩余动作。

## 本次改动

### 1. planner 输出升级为动作序列

更新：

- `agentbot/prompts/browser_subgraph.py`
- `agentbot/graph/browser_nodes.py`

现在 planner prompt 明确要求返回：

```json
{
  "evaluation_previous_goal": "...",
  "memory": "...",
  "next_goal": "...",
  "current_plan_item": null,
  "plan_update": null,
  "action": [
    {
      "action_type": "type",
      "element_index": 3,
      "text": "广州"
    },
    {
      "action_type": "press_enter"
    }
  ]
}
```

同时解析层兼容两种格式：

- AgentBot 当前的扁平动作对象
- 更接近 `browser-use` 的单键工具对象，如 `{"click": {"index": 5}}`

### 2. subgraph state 增加 step 级动作队列

更新：

- `agentbot/graph/state.py`
- `agentbot/graph/browser_nodes.py`

新增状态：

- `browser_pending_actions`
- `browser_last_action_results`
- `browser_max_actions_per_step`

兼容保留：

- `browser_pending_action`
- `browser_last_action_result`

这样不会破坏现有主图、timeline、summary、run-step 落盘边界。

### 3. runtime 执行升级为顺序执行

更新：

- `agentbot/browser/views.py`
- `agentbot/browser/actions.py`
- `agentbot/graph/browser_nodes.py`

新增：

- `BrowserActionSequenceResult`
- `execute_browser_actions(...)`

执行规则对齐 `browser-use` 主干思路：

- 同一步可以顺序执行多个动作
- 如果中途页面变化或 observation 失效，剩余动作中断
- 中断原因进入 step result，交给下一轮 observe/decide 重新判断

### 4. evaluate / finish 适配 step 语义

更新：

- `agentbot/graph/browser_nodes.py`

现在：

- `browser_evaluate` 会根据 `browser_last_action_results` 计算本轮实际执行动作数
- `browser_finish` 会展示整个待确认动作序列，而不是只显示单个动作

## 为什么这样做

这次不是简单“提速”或“少一轮 observe”，而是为了把浏览器子图真正往 `browser-use` 的 agent loop 靠：

- planner 不再被迫每轮只猜一个动作
- 表单类任务可以自然表达 `type -> click / press_enter`
- 页面变化会像 `browser-use` 一样中断序列，而不是继续盲点后续动作

同时保留了 AgentBot 当前稳定边界：

- 浏览器 agent 仍然是 LangGraph 子图
- 主图 / transcript / runs / run_steps / SSE 不改协议
- browser summary 仍然回主图收口

## 验证

执行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

以及轻量检查：

1. `_parse_browser_actions_payload(...)` 可解析扁平动作列表
2. `_parse_browser_actions_payload(...)` 可解析 `browser-use` 风格单键工具动作
3. planner prompt 已明确要求返回 `action: [...]`
