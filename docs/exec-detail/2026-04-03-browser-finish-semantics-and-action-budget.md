# 2026-04-03 Browser Finish Semantics And Action Budget

## Background

浏览器子图之前存在两个直接问题：

1. `browser_prepare` 把 `browser_max_actions` 写死为 `4`
2. `browser_finish` 只要不是 `approval_required`，就默认输出“已完成浏览器任务”

这会导致真实执行没有完成时，最终 transcript 仍然出现“已完成”的错误结论。

## This Change

本次调整只覆盖浏览器子图内部，不改主链路、数据落盘模型和前后端通信协议。

### 1. 动作预算改为配置项

- 在 [settings.py](/F:/AgentBot/agentbot/config/settings.py) 为 `browser` 增加 `max_actions`
- 默认值从原先硬编码的 `4` 提升为 `12`
- `browser_prepare` 改为从 `Settings.browser.max_actions` 读取预算
- `browser_routes.py` 与 `browser_nodes.py` 的兜底值同步为 `12`

### 2. finish 语义改为真实状态

在 [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py) 中新增 `_assess_browser_completion(...)`，用来区分：

- `approval_required`
- `incomplete`
- `completed`

当前判断规则：

- 需要人工确认时，返回 `approval_required`
- 最后一次动作失败时，返回 `incomplete`
- 达到动作预算但尚未进入 `done` 时，返回 `incomplete`
- 因预算或循环信号触发的 `done`，返回 `incomplete`
- 其他 `done` 场景，暂按 `completed` 处理

### 3. 最终消息不再默认宣称完成

`browser_finish` 现在会根据状态分别输出：

- 暂停等待人工确认
- 任务已停止，但尚未确认完成
- 已完成浏览器任务

并在消息中附带：

- 停止原因
- 最后一步
- 待确认动作

## Validation

已完成的本地验证：

- `python -m compileall agentbot`
- 直接调用 `_assess_browser_completion(...)` 验证预算耗尽会得到 `(\"incomplete\", ...)`
- 直接调用 `browser_finish(...)` 验证预算耗尽场景不再返回 completed

## Follow-up

这次只修了“结束语义”和“预算配置”，还没有解决：

- planner 把“广州”串成“重庆”的任务理解问题
- 浏览器子图缺少更严格的“任务真正完成”判定
- 浏览器子图结束后仍由它自己直接生成最终 assistant 文本
