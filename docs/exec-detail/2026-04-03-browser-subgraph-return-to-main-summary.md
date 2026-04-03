# 2026-04-03 Browser Subgraph Return To Main Summary

## Goal

在浏览器子图已经具备内部失败收口能力之后，继续解决第二个体验问题：

- 浏览器 specialist 虽然能自己 finish
- 但最终呈现给用户的回答，仍然应该回到主图，由主 agent 做统一总结

## Change

### 1. 主图新增 `browser_summary`

在 [builder.py](/F:/AgentBot/agentbot/graph/builder.py) 中新增主图节点：

- `browser_summary`

主图路由从：

```text
browser_subgraph -> END
```

改为：

```text
browser_subgraph -> browser_summary -> END
```

### 2. `browser_summary` 负责用户向总结

在 [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py) 中新增：

- `browser_summary(state, llm)`

它会读取浏览器子图结果：

- `browser_task`
- `browser_status`
- `browser_result`
- `browser_failure_reason`
- `browser_failure_step`
- `browser_action_history`

再由主 agent 口吻生成最终用户回复。

如果 LLM 总结失败，则回退到模板化 fallback 文本，确保主图仍然有最终 assistant message。

### 3. 流式 token 输出接到 `browser_summary`

在 [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py) 中，`assistant_final_delta` 之前只接受来自 `chatbot` 的 token。

现在扩展为：

- `chatbot`
- `browser_summary`

这样浏览器任务的最终主图总结也能正常走前端流式显示。

## Result

现在浏览器任务路径变成两层收口：

1. 浏览器子图内部始终 finish
2. finish 后回到主图 summary 节点，再由主 agent 对用户说人话

这意味着即使浏览器被手动关闭、页面失效或浏览器任务中途失败，系统也不再只剩一条技术报错，而是能够：

- 先在子图内形成结构化失败结果
- 再在主图生成统一自然语言总结

## Validation

已完成本地验证：

- `python -m compileall agentbot`
- 直接调用 `browser_summary(...)` 的 fallback 路径，确认主图节点能产出最终 `AIMessage`
- `streaming_runner.py` 已接纳 `browser_summary` 的流式输出来源

## Boundary

这次改的是“浏览器任务如何回到主图做总结”。

还没有继续做的是：

- 浏览器 planner 为什么会在携程首页卡住不动
- 主 agent 的总结 prompt 进一步做强
- 浏览器任务的成功判定更细化
