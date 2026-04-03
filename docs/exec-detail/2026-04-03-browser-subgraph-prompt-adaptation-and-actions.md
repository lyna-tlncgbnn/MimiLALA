# 2026-04-03 Browser Subgraph Prompt Adaptation And Actions

## 背景

浏览器子图此前已经补强了 observation、稳定 selector 和 runtime 事件处理，但规划层提示词仍然过于轻量：

- 更像“页面摘要 -> 选一个动作”
- 缺少 `browser-use` 风格的浏览器行为规则
- 对搜索提交、新标签页研究、弹窗优先处理等模式约束不足

同时，当前动作集合也偏少，导致即使提示词告诉模型要“在新标签页搜索”或“输入后按 Enter 提交”，runtime 也不一定有对应动作可以执行。

## 本次实现

本次仍然保持浏览器 agent 属于 LangGraph 子图，没有修改上层 run/timeline/数据落盘和前后端沟通层。

涉及文件：

- `agentbot/prompts/browser_subgraph.py`
- `agentbot/browser/views.py`
- `agentbot/browser/actions.py`

## 1. 将 browser-use 的系统提示词思路适配到当前子图协议

参考来源：

- `F:/browser-use/browser_use/agent/system_prompts/system_prompt_no_thinking.md`

没有直接整份照搬，原因是 AgentBot 当前浏览器子图和 browser-use 的输入输出契约不同：

- browser-use 期望完整 agent step JSON
- AgentBot 当前子图只接受一个 `BrowserAction`

因此本次做的是“适配式迁移”：

- 保留当前单动作 JSON 输出协议
- 将 `browser-use` 中高价值的行为规则迁移进 planner prompt

主要迁移的规则包括：

- popup / modal / cookie banner 优先处理
- 搜索与自动完成场景优先看新出现元素
- 输入后无更好候选时可以按 Enter 提交
- 研究型任务优先使用新标签页，避免丢失当前页面
- 页面仍在变化时优先 wait
- 明确步骤型任务与开放任务的处理方式
- 过滤条件优先应用
- loop / 无效重复动作需要切换策略
- done 前要根据当前页面状态核验任务是否真的完成

## 2. 动作集合增加第一轮关键能力

### `press_enter`

新增动作：

- `press_enter`

用途：

- 在搜索框、表单、自动完成输入之后触发提交
- 衔接 browser-use 提示词中“输入后可能需要 Enter”的规则

执行后同样会收集：

- `page_changed`
- `observation_stale`
- `navigation_events`
- `tab_events`
- `downloads`
- `dialogs`

### `new_tab_navigate`

新增动作：

- `new_tab_navigate`

用途：

- 在研究、搜索、跳转到外部站点时保留当前页面
- 对齐 browser-use 提示词里“如果需要研究，优先开新标签页”的规则

执行方式：

- `context.new_page()`
- 切到新 tab
- 导航到目标 URL
- 继续通过 runtime 事件系统回收 tab / navigation 信号

## 3. 当前边界

这次没有把 browser-use 的完整 agent loop 输出结构搬进来，例如：

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `plan_update`
- 文件系统工具链
- 多动作序列输出

这些能力仍然留在后续阶段评估，不影响当前子图继续保持单动作 LangGraph 编排。

## 验证

### 编译验证

执行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果：通过。

### runtime 验证

本地检查两条新动作链路：

1. `type -> press_enter`

- 在本地 form fixture 中先输入文本
- 再执行 `press_enter`
- 成功导航到目标页面，并返回 `page_changed=True`

2. `new_tab_navigate`

- 从 `about:blank` 启动 session
- 执行 `new_tab_navigate`
- 成功创建第二个 tab，并返回 `tab_events` 与 `navigation_events`

## 结论

浏览器子图现在的规划层已经不再只是一个极简“选动作器”，而是开始具备 browser-use 风格的浏览器操作规则。同时 runtime 也具备了与这些规则配套的第一轮关键动作能力。

下一步如果继续往 browser-use 靠拢，比较自然的方向会是：

- 更强的 planner state（如 last-step evaluation / memory）
- 更丰富的浏览器动作集合
- 是否逐步支持多动作 step 输出
