# Browser Subgraph Phase 1B

## 日期

- 2026-04-02

## 目标

把 browser 子图从 Phase 1A 的骨架推进到最小真实浏览器观察层，采用：

- Playwright 作为执行底座

而不是继续停留在占位 session 或纯文本模拟。

## 本次实现

### 1. 引入 Playwright 运行时

已安装：

- `playwright`
- Chromium runtime

并将 browser 子图的最小会话管理切换为真实 Playwright 浏览器会话。

相关文件：

- [session.py](/F:/AgentBot/agentbot/browser/session.py)

### 2. 新增页面观察层

新增最小 `dom_service`，负责从真实页面提取：

- 页面标题
- 页面 URL
- 主可见文本
- 前若干个链接
- 前若干个表单控件
- viewport / scroll 信息
- 截图

相关文件：

- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

### 3. 增强 browser state summary

`BrowserStateSummary` 现在支持记录：

- screenshot 路径

相关文件：

- [views.py](/F:/AgentBot/agentbot/browser/views.py)

### 4. 子图节点切到真实页面读取

`browser_prepare` 现在会真正创建 Chromium 会话。  
`browser_observe` 现在会读取真实页面并生成结构化页面摘要。  
`browser_finish` 会关闭会话并返回页面读取结果。

相关文件：

- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

## 当前能力边界

Phase 1B 完成后，browser 子图已经支持：

- 打开 URL
- 读取真实页面
- 生成结构化页面摘要
- 保存页面截图
- 把中间步骤实时写入统一的 `run_steps`

当前仍未支持：

- click
- type
- scroll
- switch tab
- approval / interrupt

这些留到后续 Phase 1C 及之后阶段。

## 验证

已完成以下验证：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. 真实 Playwright 烟测：browser 子图成功读取 `https://example.com/`
3. 页面摘要验证：成功提取标题、正文、链接，并生成截图
4. 持久化验证：browser 子图步骤成功落入统一 `run_steps`，包含父子层级关系

持久化验证结果中，已确认以下步骤写入：

- `进入浏览器任务`
- `初始化浏览器会话`
- `观察页面状态`
- `汇总浏览器结果`

## 结果

Phase 1B 完成后，browser 子图已经不再只是“流程骨架”，而是具备了：

- 真实浏览器会话
- 真实页面读取
- timeline 可见的 browser 步骤
- 与主链路共享的持久化执行模型

这为下一阶段补 `click / type / scroll` 这类真实交互动作提供了稳定底座。
