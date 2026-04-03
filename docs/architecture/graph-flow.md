# Graph Flow

## 当前图结构

当前 LangGraph 已经不是单一的 `chatbot -> tools -> chatbot`。主图现在包含一个浏览器意图分流节点和一个浏览器子图：

```text
START
  -> browser_intent
    -> browser_subgraph -> browser_summary -> END
    -> chatbot -> tools -> chatbot -> END
```

关键构建文件：

- `agentbot/graph/builder.py`
- `agentbot/graph/browser_subgraph.py`

## 主图职责

### `browser_intent`

负责：

- 从最新用户消息判断是否进入浏览器任务
- 提取 `browser_task`
- 为后续子图准备浏览器相关状态字段

### `chatbot`

负责：

- 调用绑定普通 tools 的 chat model
- 产出 assistant 消息
- 决定是否发起 tool calls

### `tools`

负责：

- 执行注册的普通工具
- 将工具结果回送给 graph

### `browser_subgraph`

负责：

- 浏览器任务的专用执行闭环
- 页面观察、动作规划、动作执行、结果评估
- 输出浏览器域结果并回到主图总结节点
- 将浏览器域复杂度留在子图内部，而不是上浮到主图

### `browser_summary`

负责：

- 接收浏览器子图的结构化执行结果
- 以主 agent 口吻向用户总结浏览器任务 outcome
- 在浏览器完成、未完成、失败、人工确认等场景下统一生成最终用户回复

## 浏览器子图

当前浏览器子图结构：

```text
browser_prepare
  -> browser_observe
  -> browser_decide
  -> browser_act
  -> browser_evaluate
  -> browser_observe ... (loop)
  -> browser_finish
```

### `browser_prepare`

负责：

- 创建 Playwright 浏览器会话
- 初始化浏览器子图状态
- 写入浏览器任务根时间线事件

### `browser_observe`

负责：

- 读取当前页面状态
- 提取主文本、分页/滚动信息、标签页信息
- 提取经过可见性过滤后的交互元素列表
- 为本轮交互元素生成稳定 selector 映射
- 生成面向 LLM 的页面摘要
- 回收近期浏览器事件

### `browser_decide`

负责：

- 基于页面摘要和历史动作规划单步浏览器动作
- 只返回结构化动作，不直接执行
- 对敏感动作做 approval gating
- 使用适配后的 browser-use 风格规则进行单步规划

当前仍保持单动作 `BrowserAction` 协议，而不是完整多动作 agent loop。

### `browser_act`

负责：

- 执行结构化浏览器动作
- 使用 `browser_observe` 生成的稳定 selector 绑定真实元素
- 产出动作结果和动作截图
- 回收 runtime 级副作用信号，例如 navigation / dialog / download / tab

### `browser_evaluate`

负责：

- 统计动作预算
- 更新 loop signal
- 判断继续观察还是结束

### `browser_finish`

负责：

- 汇总浏览器结果
- 关闭浏览器会话
- 生成最终 assistant 消息
- 输出浏览器时间线结束事件

## 状态模型

主状态仍然基于 `MessagesState` 扩展，但现在增加了浏览器子图字段：

- `browser_task`
- `browser_status`
- `browser_session_id`
- `browser_state_summary`
- `browser_pending_action`
- `browser_pending_actions`
- `browser_last_action_results`
- `browser_action_history`
- `browser_action_count`
- `browser_loop_signal`
- `browser_requires_approval`
- `browser_events`

定义位置：

- `agentbot/graph/state.py`

## Checkpoint 集成

当前 graph 编译时仍然接入：

- `agentbot/graph/checkpoints.py`

核心对象：

- `SqliteSaver`

当前规则：

- 每个 `run` 使用自己的 `thread_id`
- `thread_id` 当前与 `run_id` 对齐，用于隔离单轮 LangGraph checkpoint state
- 每轮都会从 transcript 重新构建输入消息，而不是复用上一轮的 graph state
- 浏览器子图也运行在同一条 LangGraph durable execution 链路内

## 同步与流式

两条执行路径继续复用同一份 graph：

- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

区别不在 graph 结构，而在：

- 如何消费 runtime events
- 如何组织 transcript / active run / run_steps
- 如何把 graph 事件映射到前端时间线

## 当前边界

当前已经具备：

- 浏览器子图
- 浏览器意图分流
- 单会话浏览器观察/规划/执行闭环
- 基于稳定 selector 的页面元素动作绑定
- iframe-aware observation 与 AX / aria 辅助信息
- browser-use 风格规则适配后的 planner prompt
- `press_enter` / `new_tab_navigate` 等搜索与研究场景动作
- navigation / dialog / download / tab 的 runtime 事件回收

当前仍未系统化引入：

- 多 browser session 编排
- browser event bus / watchdog 体系
- CDP DOM / AX tree 全量建模
- browser-use 完整多动作 agent loop 协议
- long-term memory state
- 多 agent orchestration

## 浏览器子图职责边界

浏览器子图当前负责：

- 单浏览器会话生命周期管理
- 单任务范围内的浏览器动作循环
- 面向浏览器域的 observation、planner prompt、结构化动作和 runtime 副作用处理
- 浏览器 artifacts、页面摘要和子图 timeline 输出

浏览器子图当前不负责：

- 主图普通 tools 的调度策略
- 多浏览器会话协同
- `browser-use` 完整 event bus / watchdog 基础设施
- `browser-use` 完整文件工具链和多动作 step 输出

## 下一步

继续向 `browser-use` 靠拢时，当前优先顺序是：

1. planner state 增强，例如显式上一步评估和轻量 memory
2. 第二轮关键浏览器动作补充，例如 overlay / popup / extract / select_option
3. observation 继续加强阻塞态识别、页面差异表达和可操作视图质量

具体迁移清单以 [browser-use-migration-todo.md](/F:/AgentBot/docs/architecture/browser-use-migration-todo.md) 为准。
