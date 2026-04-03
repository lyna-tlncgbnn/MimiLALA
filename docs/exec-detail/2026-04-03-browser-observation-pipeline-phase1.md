# 2026-04-03 Browser Observation Pipeline Phase 1

## 背景

浏览器子图在复杂站点上仍然容易卡在首页不动。对照 `browser-use` 之后，发现核心短板不只是 selector 稳定性，而是 observation 仍然过于扁平：

- raw capture 与 serialization 混在一个函数里
- planner 看到的是平铺的 interactive list
- 任务相关控件和站点导航控件没有被很好地区分

## 本次改动

本次先落 observation pipeline 的第一阶段分层。

### 1. 新增 raw capture 层

新增：

- `agentbot/browser/observation_capture.py`

职责：

- 采集 main document / iframe document
- 采集 interactive candidates
- 采集 headings / landmarks / page info
- 保留 tab metadata 与 recent runtime events

### 2. 新增 serialization 层

新增：

- `agentbot/browser/observation_serialize.py`

职责：

- 对 raw candidates 做 ranking
- 把表单控件、搜索控件、导航控件做语义分组
- 输出 `semantic_groups`
- 输出 `prioritized_hints`
- 生成新的 `BrowserStateSummary`

### 3. 收口 dom_service

`agentbot/browser/dom_service.py` 现在只保留 observation 入口职责：

- raw capture
- serialization
- screenshot output

不再继续承担所有 DOM/排序/摘要细节。

### 4. 扩展 BrowserStateSummary

更新：

- `agentbot/browser/views.py`

新增字段：

- `BrowserInteractiveElement.label_text`
- `BrowserInteractiveElement.section_hint`
- `BrowserInteractiveElement.landmark_hint`
- `BrowserInteractiveElement.semantic_group`
- `BrowserInteractiveElement.semantic_score`
- `BrowserStateSummary.semantic_groups`
- `BrowserStateSummary.prioritized_hints`

### 5. 接通现有子图接口

更新：

- `agentbot/graph/browser_nodes.py`
- `agentbot/browser/actions.py`

让现有子图仍然通过 `BrowserStateSummary` 工作，同时能消费新的 semantic metadata。

## 边界

本次没有改动：

- 浏览器 agent 作为 LangGraph 子图的边界
- transcript / run / run_steps / artifacts 主落盘模型
- 前后端通信层
- browser_summary 主图收口逻辑

## 验证

执行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果：

- 编译通过
- 新的 raw observation -> serialized summary 链路可正常构造 `BrowserStateSummary`

## 后续

这一阶段只完成了 observation pipeline 分层。

下一阶段应继续做：

1. planner state 增强
2. planner prompt 接 richer observation state
3. 再评估是否升级成多动作 step
