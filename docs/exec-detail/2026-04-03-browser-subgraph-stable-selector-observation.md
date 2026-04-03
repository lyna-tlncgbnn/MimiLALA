# Browser Subgraph Stable Selector Observation

## 日期

- 2026-04-03

## 目标

修正当前 browser subgraph 的核心稳定性问题，同时保持以下边界不变：

- 浏览器 agent 仍然是 LangGraph 子图
- transcript / runs / run_steps / UI 时间线这条链路不改
- 数据落盘和前后端沟通层不改

本次重点解决的问题：

1. `browser_observe` 只做轻量 `querySelectorAll`，会把隐藏或无效元素带进摘要
2. `browser_act` 用 `locator(...).nth(dom_index)` 回放动作，元素绑定不稳定
3. LLM 看到的页面元素与执行层实际点击的元素可能不是同一个对象

## 本次实现

### 1. 重构浏览器观测层

文件：

- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

调整：

- 不再只返回 `dom_index`
- 在页面观察阶段为候选交互元素注入 `data-agentbot-id`
- 给每个交互元素生成稳定 selector，例如：
  - `[data-agentbot-id="ab-1"]`
- 过滤隐藏、透明、尺寸过小、`aria-hidden=true`、`pointer-events:none`、`input[type=hidden]` 等无效元素
- 为每个元素补充更丰富的字段：
  - `selector`
  - `enabled`
  - `visible`
  - `in_viewport`
  - `bounds`
  - `aria_label`
  - `title`

### 2. 重构动作执行绑定

文件：

- [actions.py](/F:/AgentBot/agentbot/browser/actions.py)

调整：

- 不再使用 `locator(INTERACTIVE_SELECTOR).nth(dom_index)`
- 改为使用 `browser_observe` 生成的稳定 selector 来定位元素
- 在点击/输入前增加更明确的准备逻辑：
  - `attached`
  - `scroll_into_view_if_needed`
  - `visible`
  - 输入时额外检查 `is_editable()`

这使得执行层不再依赖“重新猜一遍 DOM 顺序”。

### 3. 扩充浏览器视图模型

文件：

- [views.py](/F:/AgentBot/agentbot/browser/views.py)
- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

调整：

- `BrowserInteractiveElement` 支持稳定 selector 与更多运行态字段
- `browser_state_summary` 的反序列化逻辑同步更新
- 子图 state 与时间线结构保持不变

### 4. 更新架构文档

文件：

- [graph-flow.md](/F:/AgentBot/docs/architecture/graph-flow.md)

调整：

- 补齐浏览器意图分流与浏览器子图的真实主图结构
- 说明浏览器子图的 `prepare -> observe -> decide -> act -> evaluate -> finish` 链路
- 明确当前已经使用“稳定 selector 绑定”的浏览器执行方式

## 验证

已完成：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. 本地 fixture 验证：
   `workspace/browser_fixture_hidden_textarea.html`
3. 验证结果：
   - 隐藏 `textarea` 不再进入交互元素列表
   - 可见 `input` / `button` 会被正确编号
   - `type -> observe -> click` 端到端链路可正常执行

## 结果

本次调整后，browser subgraph 的核心运行模型变为：

- 先观察并生成稳定元素映射
- 再让 LLM 规划结构化动作
- 最后按稳定 selector 执行动作

这比之前的“轻量摘要 + DOM 序号回放”稳定得多，也更接近 browser-use 的核心思想。

## 当前仍未引入的能力

本次没有引入：

- browser-use 风格的 event bus / watchdog 架构
- 基于 CDP 的完整 DOM / AX tree / iframe 建模
- 多步动作批处理与页面变化守卫

这些属于后续可继续演进的 runtime 基础设施，不是本轮修复当前点击失真的必要前提。
