# Browser Subgraph Phase 1E

## 日期

- 2026-04-03

## 目标

为 browser 子图后续接入 approval / interrupt UI 预留稳定边界，而不是直接把敏感动作放开执行。

本阶段重点是：

- `requires_approval` 预留
- 敏感动作分类
- 在没有完整 UI 的情况下先安全收口

## 本次实现

### 1. browser state 新增 approval 相关字段

新增：

- `browser_requires_approval`
- `browser_approval_reason`

相关文件：

- [state.py](/F:/AgentBot/agentbot/graph/state.py)

### 2. browser action 模型支持 approval 标记

`BrowserAction` 现在支持：

- `approval_required`
- `approval_reason`

相关文件：

- [views.py](/F:/AgentBot/agentbot/browser/views.py)

### 3. 在 decide 阶段做敏感动作分类

当前会识别并拦下两类典型敏感动作：

- 向密码类输入框输入内容
- 点击带有提交/发送/确认/删除/支付/登录等语义的按钮或链接

如果命中，会在 `browser_decide` 后直接把子图状态置为：

- `browser_status = approval_required`

并跳过 `browser_act`，直接进入 `browser_finish`。

相关文件：

- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)
- [browser_routes.py](/F:/AgentBot/agentbot/graph/browser_routes.py)

### 4. 补齐 `file://` URL 识别

为本地页面测试和后续本地文件浏览场景，browser 子图现在也能识别：

- `file://`

相关文件：

- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

### 5. browser planner prompt 增加安全约束

browser planner prompt 现在会显式要求：

- 避免破坏性或账户相关动作
- 不确定时优先选择 `done`

相关文件：

- [browser_subgraph.py](/F:/AgentBot/agentbot/prompts/browser_subgraph.py)

## 当前行为

在还没有完整 approval / interrupt UI 的前提下，当前 browser 子图的行为是：

- 普通安全动作照常执行
- 命中敏感动作时不执行
- 生成 `approval_required` 状态
- 在最终 browser 结果里明确写出：
  - 当前页面
  - 待确认动作
  - 需要确认的原因

同时 timeline 中根步骤状态会显示为：

- `paused`

## 验证

已完成以下验证：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. `ui` 前端构建通过：`npm run build`
3. approval 烟测：
   在本地 `file://` 测试页上规划点击 `Submit Order`
4. 验证结果：
   browser 子图未执行点击动作，而是返回 `approval_required`

## 结果

Phase 1E 完成后，browser 子图已经具备：

- 对敏感动作的基础 gating
- 可供未来前端 approval / interrupt UI 直接消费的状态边界
- 在当前无 UI 情况下仍然相对安全的默认行为

这意味着 browser subgraph Phase 1 的主线已经收口完成：

- 真实页面读取
- 基础交互闭环
- artifacts / loop detection
- approval 预留边界
