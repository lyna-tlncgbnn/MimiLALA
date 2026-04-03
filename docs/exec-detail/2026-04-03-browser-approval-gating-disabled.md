# 2026-04-03 Browser Approval Gating Disabled

## 背景

浏览器子图此前在 `browser_decide` 阶段会对动作序列执行敏感动作判断：

- 调用 `_sensitive_action_reason_for_sequence(...)`
- 一旦命中 “submit / confirm / register / 登录 / 提交 / 支付” 等关键词
- 就把子图状态写成 `approval_required`

这在当前 AgentBot 架构下会稳定造成卡死，因为浏览器链路虽然保留了 approval 状态字段，但并没有完整的 approval / resume UI 闭环。

实际表现为：

- 查询类任务已经填完参数
- 下一步正常应该点击“搜索”或“查询”
- 但子图被拦在 `approval_required`
- 主图只能总结“等待授权”，任务无法继续

## 本次改动

更新：

- `agentbot/graph/browser_nodes.py`

改动内容：

- 关闭 `browser_decide` 中对动作序列的审批拦截
- 不再调用 `_sensitive_action_reason_for_sequence(...)` 的结果来阻断子图
- `browser_requires_approval` 固定写回 `False`
- `browser_approval_reason` 固定写回 `None`

## 结果

现在浏览器子图会继续直接执行：

- 搜索按钮点击
- 查询提交
- 普通页面流转

不会再因为“提交 / 搜索 / 注册风格词”进入暂停等待授权状态。

## 边界

这次只关闭了浏览器子图内部的 approval gating，不影响：

- 主图结构
- 浏览器子图作为 LangGraph subgraph 的边界
- run / run_steps / timeline / summary 落盘结构

如果未来要恢复审批，需要先补完整的前端确认与恢复执行闭环，而不是只保留状态字段。
