# 2026-04-03 Browser Subgraph Failure Funneling

## Background

浏览器子图之前有一个明显缺口：

- 正常完成时，由 `browser_finish` 生成最终 assistant 消息
- 但只要在 `browser_prepare / browser_observe / browser_act / browser_evaluate` 任一步抛出异常，整个 graph 就会直接 `run_failed`

这会导致两类体验问题：

1. 用户手动关闭浏览器后，只看到技术错误，没有最终说明
2. 子图失败时没有自然语言收口，看起来像“主 agent 没回复”

## Why This Happened

当前主图结构仍然是：

```text
START
  -> browser_intent
    -> browser_subgraph -> END
    -> chatbot -> tools -> chatbot -> END
```

也就是说，浏览器任务不会回到主图做统一总结。  
因此浏览器子图内部必须像一个完整的 specialist agent 那样，自己保证：

- 正常时能 finish
- 异常时也能 finish

这次改动借鉴的是 `browser-use` 的核心 loop 思路：

- 单步异常先收口为 agent state
- 再由统一的 finalize / finish 逻辑产出结果

而不是让底层浏览器异常直接炸穿整个执行链。

## Change

### 1. 为浏览器子图增加显式失败状态

在 [state.py](/F:/AgentBot/agentbot/graph/state.py) 中新增：

- `browser_failure_reason`
- `browser_failure_step`

### 2. 子图节点改为 safe wrappers

在 [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py) 中新增：

- `browser_prepare_safe`
- `browser_observe_safe`
- `browser_decide_safe`
- `browser_act_safe`
- `browser_evaluate_safe`

这些 wrapper 会：

- 执行原始节点逻辑
- 捕获异常
- 将异常归一化为用户可读的 `browser_failure_reason`
- 写入失败事件
- 把子图状态导向 `browser_finish`

### 3. 路由改为“失败也去 finish”

在 [browser_routes.py](/F:/AgentBot/agentbot/graph/browser_routes.py) 中新增 prepare/observe/act 的失败路由判断，并在 decide/evaluate 中补上：

- 只要存在 `browser_failure_reason`
- 立即转向 `browser_finish`

### 4. `browser_finish` 支持 failed 状态

`browser_finish` 现在会区分：

- `approval_required`
- `failed`
- `incomplete`
- `completed`

并输出：

- 停止原因
- 失败节点
- 最后一步

这意味着像 “Target page, context or browser has been closed” 这类 Playwright 错误，现在会被翻译成：

- 浏览器任务执行失败
- 浏览器窗口、页面或浏览器上下文在执行过程中被关闭

而不是直接让整条 graph 崩掉。

## Validation

已完成的本地验证：

- `python -m compileall agentbot`
- 直接调用 `_friendly_browser_error(...)`，验证浏览器关闭错误会被归一化
- 直接调用 `browser_finish(...)`，验证失败状态能产出最终消息
- 直接调用 `browser_observe_safe(...)`，验证缺失 session 时会返回 `failed` 状态，而不是抛异常

## Current Boundary

这次只做了第一步：

- 保证浏览器子图内部总能收口到 `browser_finish`

还没有做第二步：

- 子图结束后回到主图，再由主 agent 做统一自然语言总结
