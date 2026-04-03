# Graph Flow

## 当前图结构

当前 LangGraph 已经不是单一的 `chatbot -> tools -> chatbot`。
主图现在包含一个浏览器意图分流节点和一个浏览器子图：

```text
START
  -> browser_intent
    -> browser_subgraph -> END
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
- 输出浏览器结果消息并结束主图

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

关键节点职责：

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
- 为本轮交互元素注入稳定 selector 映射
- 生成给 LLM 使用的页面摘要

### `browser_decide`

负责：

- 基于页面摘要和历史动作规划单步浏览器动作
- 只返回结构化动作，不直接执行
- 对敏感动作做 approval gating

### `browser_act`

负责：

- 执行结构化浏览器动作
- 使用 `browser_observe` 生成的稳定 selector 绑定真实元素
- 产出动作结果和动作截图

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

- `conversation_id` 直接作为 `thread_id`
- 如果该 conversation 已有 checkpoint，则后续轮次从 checkpoint 恢复
- 浏览器子图也运行在同一条 LangGraph durable execution 链路内

## 同步与流式

两条执行路径继续复用同一份 graph：

- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

区别仍然不在 graph 结构，而在：

- 如何消费 runtime events
- 如何组织 transcript / active run / run_steps
- 如何把 graph 事件映射到前端时间线

## 当前边界

当前已经具备：

- 浏览器子图
- 浏览器意图分流
- 单会话浏览器观察/规划/执行闭环
- 基于稳定 selector 的页面元素动作绑定

当前仍未系统化引入：

- 多 browser session 编排
- browser event bus / watchdog 体系
- 跨 iframe / AX tree / CDP DOM 全量建模
- 多 agent orchestration
- long-term memory state
