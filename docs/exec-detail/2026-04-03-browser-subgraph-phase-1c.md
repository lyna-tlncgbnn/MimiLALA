# Browser Subgraph Phase 1C

## 日期

- 2026-04-03

## 目标

在 Phase 1B 的真实页面读取基础上，为 browser 子图补齐最小基础交互闭环：

- `observe`
- `decide`
- `act`
- `evaluate`

并接入：

- `click`
- `type`
- `scroll`
- `wait`
- `go_back`
- `switch_tab`

## 本次实现

### 1. 新增浏览器动作模型

在浏览器视图模型中新增：

- `BrowserInteractiveElement`
- `BrowserAction`
- `BrowserActionResult`

用于把页面可交互元素和子图待执行动作结构化。

相关文件：

- [views.py](/F:/AgentBot/agentbot/browser/views.py)

### 2. 增强页面观察层

`dom_service` 现在会抽取统一的交互元素列表，而不只是简单分开链接和表单控件。  
这让后续动作执行可以基于稳定的 `element_index` 和 `dom_index` 工作。

相关文件：

- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

### 3. 新增 Playwright 动作执行层

新增低层动作模块，当前支持：

- `navigate`
- `click`
- `type`
- `scroll`
- `wait`
- `go_back`
- `switch_tab`

并在动作后补截图，供后续 timeline / artifact 扩展使用。

相关文件：

- [actions.py](/F:/AgentBot/agentbot/browser/actions.py)

### 4. 子图接成真正的小闭环

browser 子图从原来的直线流程：

- `prepare -> observe -> finish`

升级为：

- `prepare -> observe -> decide -> act -> evaluate -> observe/finish`

相关文件：

- [browser_subgraph.py](/F:/AgentBot/agentbot/graph/browser_subgraph.py)
- [browser_routes.py](/F:/AgentBot/agentbot/graph/browser_routes.py)
- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

### 5. 引入 browser planner prompt

新增 browser 子图自己的 planner prompt，用于要求模型返回单步动作 JSON，避免把浏览器决策逻辑散落在节点实现里。

相关文件：

- [browser_subgraph.py](/F:/AgentBot/agentbot/prompts/browser_subgraph.py)

### 6. 扩展 graph state

新增 browser 子图运行字段，包括：

- `browser_state_summary`
- `browser_pending_action`
- `browser_last_action_result`
- `browser_action_history`
- `browser_action_count`
- `browser_max_actions`

相关文件：

- [state.py](/F:/AgentBot/agentbot/graph/state.py)

## 当前能力边界

Phase 1C 完成后，browser 子图已经可以：

- 读取页面
- 决定下一步交互动作
- 点击页面元素
- 在输入框填写内容
- 页面滚动
- 返回上一页
- 切换标签页
- 把完整中间步骤写入统一 `run_steps`

当前仍未覆盖：

- approval / interrupt
- 更强的错误恢复
- loop detection
- 更细粒度 artifacts
- 复杂表单、文件上传、下载管理

这些留给后续阶段。

## 验证

已完成以下验证：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. 真实 browser 子图烟测：
   打开 `https://example.com/`，点击 `Learn more`，成功跳转并生成最终摘要
3. 低层交互烟测：
   在临时本地 HTML 页面中验证 `type / scroll / go_back`
4. 持久化烟测：
   确认以下步骤已写入统一 `run_steps`

- `进入浏览器任务`
- `初始化浏览器会话`
- `观察页面状态`
- `决定下一步动作`
- `执行动作: click`
- `评估动作结果`
- `汇总浏览器结果`

## 结果

Phase 1C 完成后，browser 子图已经具备：

- 最小真实浏览器交互循环
- 可结构化规划的 browser action
- 基础页面交互能力
- 与主运行时共享的统一执行时间线

这为后续的：

- loop detection
- browser artifacts
- approval / interrupt

打下了稳定的执行层基础。
