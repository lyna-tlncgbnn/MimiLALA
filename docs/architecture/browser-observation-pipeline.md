# Browser Observation Pipeline

## 目标

这份文档描述浏览器子图 observation 层当前的内部结构，以及它如何继续向 `browser-use` 的 DOM/AX/layout capture -> serialization 链路靠拢。

这不是主图说明文档；主图与子图关系以 [graph-flow.md](/F:/AgentBot/docs/architecture/graph-flow.md) 为准。

## 当前分层

当前浏览器 observation 已拆成 3 层：

1. `agentbot/browser/observation_capture.py`
   raw capture 层。
   负责从 Playwright 页面与 iframe 读取原始页面状态，包括：
   - main document / iframe document
   - interactive candidates
   - headings
   - landmarks
   - page info
   - tab metadata
   - recent runtime events

2. `agentbot/browser/observation_serialize.py`
   serialization 层。
   负责把 raw capture 结果转换成面向 planner 的页面状态，包括：
   - candidate ranking
   - semantic groups
   - prioritized hints
   - `BrowserStateSummary`
   - `dom_summary`
   - observation fingerprint

3. `agentbot/browser/dom_service.py`
   observation 入口层。
   只负责串联 raw capture、serialization 和 screenshot output，不再承担所有 DOM 逻辑。

## 与 browser-use 的关系

当前实现已经开始对齐 `browser-use` 的核心思路：

- 先拿 richer raw page state
- 再做 serialization
- 再把结果提供给 planner

但当前还没有完全等同于 `browser-use`：

- 还没有完整 CDP DOM tree / AX tree / layout tree
- 还没有完整 selector map lifecycle
- 还没有完整 serializer tree 优化与 node-level paint-order filtering

所以当前阶段的定位是：

`browser-use` 风格 observation pipeline 的第一阶段落地。

## 当前输出给子图的状态

当前子图继续消费 `BrowserStateSummary`，但它已经比早期版本 richer：

- `interactive_elements`
- `semantic_groups`
- `prioritized_hints`
- `iframe_summaries`
- `recent_events`
- `observation_fingerprint`

这意味着：

- LangGraph 子图接口没有变
- `browser_nodes.py` 不需要感知 raw capture 的内部细节
- 前后端通信层与落盘结构也不需要重构

## 当前边界

这次 observation 分层不改变以下边界：

- 浏览器 agent 继续作为 LangGraph 子图存在
- `run / run_steps / artifacts / timeline` 保持现有模型
- 主图与 transcript 主链路不感知 observation 内部分层
- 不为了 observation 升级而引入完整 `browser-use` event bus / watchdog 架构

## 下一步

observation pipeline 后续继续向 `browser-use` 靠拢时，优先顺序是：

1. 继续丰富 raw capture
   补更完整的 DOM/AX/layout 信号。
2. 继续增强 serialization
   提升任务相关性排序、主表单识别、overlay/modal/cookie banner 识别。
3. 再把 richer observation 接入 planner state
   让子图更像完整 browser agent，而不是单步动作选择器。
