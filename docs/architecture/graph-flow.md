# Graph Flow

## 当前图结构

当前 LangGraph 已经不是单一的 `chatbot -> tools -> chatbot`。主图现在包含一个浏览器意图分流节点、一个浏览器子图，以及一个主图侧的浏览器结果总结节点：

```text
START
  -> browser_intent
    -> browser_subgraph -> browser_summary -> END
    -> chatbot -> tools -> chatbot -> END
```

关键构建文件：

- [builder.py](/F:/AgentBot/agentbot/graph/builder.py)
- [browser_subgraph.py](/F:/AgentBot/agentbot/graph/browser_subgraph.py)

## 主图职责

### `browser_intent`

负责：

- 从最新用户消息判断是否进入浏览器任务
- 提取 `browser_task`
- 为浏览器子图准备状态字段

### `chatbot`

负责：

- 调用主聊天模型
- 产出普通 assistant 消息
- 决定是否触发普通 tools

### `tools`

负责：

- 执行已注册的普通工具
- 将结果回送给主图

### `browser_subgraph`

负责：

- 浏览器任务的专用执行闭环
- 处理页面观察、动作规划、动作执行、执行评估和完成收口
- 输出浏览器域结果，再回到主图

### `browser_summary`

负责：

- 接收浏览器子图的结构化结果
- 由主 agent 风格汇总给用户
- 在成功、未完成、失败、需人工确认等场景统一生成最终说明

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

- 创建浏览器会话
- 初始化浏览器子图状态
- 记录浏览器任务根 timeline event
- 把实际生效的浏览器配置写入 `run_steps`

当前准备阶段已经能够记录：

- `mode`
- `headless`
- `window_width / window_height`
- `no_viewport`
- `profile_directory`
- `temp_profile_dir`
- `downloads_dir`
- 下载相关 timeout

### `browser_observe`

负责：

- 通过 runtime 请求当前 browser state
- 获取 DOM summary、interactive elements、semantic groups、page info、recent events
- 生成 observation fingerprint
- 计算 stagnation / loop signal 所需输入
- 记录 observation step 到 timeline

当前链路已经不是 graph 自己直接读取页面，而是：

```text
browser_observe
  -> capture_page_state()
    -> request_browser_state()
      -> BrowserStateRequestEvent
        -> DOMWatchdog
          -> raw capture
          -> serialization
          -> screenshot
          -> runtime cache
```

这一步是当前子图结构升级的重点之一：graph 只拿 browser state summary，而不再自己承担 DOM 采集和 cache 管理职责。

### `browser_decide`

负责：

- 基于 browser state summary、planner state、action history、loop/progress signal 规划下一步
- 输出结构化动作序列，而不是自由文本
- 更新 planner state：
  - `evaluation_previous_goal`
  - `memory`
  - `next_goal`
  - `browser_plan`
  - `browser_current_plan_item`
- 在预算耗尽或 loop signal 触发时收口为 `done`

当前 prompt 已经大量借鉴 `browser-use`，但保留本项目的 LangGraph 状态模型。

### `browser_act`

负责：

- 执行结构化浏览器动作序列
- 截图并记录 action step 输出
- 处理中断：
  - `page_changed`
  - `observation_stale`
  - popup/new tab
  - download started / in progress / completed

当前链路已经变成：

```text
BrowserAction
  -> actions.py compatibility layer
    -> runtime action event
      -> DefaultActionWatchdog
        -> Playwright operation
        -> runtime effect collection
```

动作执行时，元素解析会优先使用 runtime cache 中的 selector map，而不是只依赖 graph state 里的 summary 副本。

### `browser_evaluate`

负责：

- 统计动作预算
- 写入 action history
- 基于 runtime effect 更新 progress signal
- 识别：
  - `download_started`
  - `download_in_progress`
  - `download`
  - `page_changed`
  - `failure`
- 决定继续 observe 还是 finish

这一步已经不再只是“动作有没有成功”，而开始消费 runtime 层对副作用的结构化判断。

### `browser_finish`

负责：

- 汇总浏览器任务结果
- 关闭浏览器会话
- 生成子图侧结束状态
- 输出 timeline 结束事件

当前浏览器子图已经保证：

- 成功会进入 `browser_finish`
- 未完成会进入 `browser_finish`
- 失败会进入 `browser_finish`
- 浏览器被关闭等异常也会被 funnel 到 `browser_finish`

然后再交给主图的 `browser_summary` 统一总结。

## graph 与 runtime 的当前边界

### graph 当前负责

- 子图循环编排
- planner prompt 与 planner state
- 预算控制
- run_steps / browser_events / timeline 输出
- 任务级汇总与主图总结

### runtime 当前负责

- 浏览器会话生命周期
- 本地 browser profile 与 downloads/artifacts
- event bus
- watchdog 分层
- 动作执行中间层
- browser state request
- DOM cache / selector map cache
- 副作用吸收：
  - download
  - dialog
  - navigation
  - popup/tab
  - page/browser close

## 为什么要把 DOM/watchdog 并进 runtime

如果 DOM 状态继续由 graph 直接调 `dom_service`：

- graph 会知道太多浏览器内部细节
- selector map 和 observation cache 无法由 runtime 统一管理
- 动作执行与页面状态之间会继续出现漂移
- 也不利于继续对齐 `browser-use`

当前 DOMWatchdog 接入以后，这个边界更清晰了：

- graph 请求 browser state
- runtime 决定如何构建、缓存、失效和返回 browser state

## 当前状态字段

浏览器子图当前重点字段包括：

- `browser_task`
- `browser_status`
- `browser_session_id`
- `browser_state_summary`
- `browser_pending_action`
- `browser_pending_actions`
- `browser_last_action_result`
- `browser_last_action_results`
- `browser_action_history`
- `browser_action_count`
- `browser_loop_signal`
- `browser_progress_signal`
- `browser_evaluation_previous_goal`
- `browser_memory`
- `browser_next_goal`
- `browser_plan`
- `browser_current_plan_item`
- `browser_events`

定义位置：

- [state.py](/F:/AgentBot/agentbot/graph/state.py)

## 当前演进位置

浏览器子图当前已经完成这些关键升级：

1. 观察、规划、执行、评估、结束的完整子图闭环
2. 浏览器结果返回主图总结，而不是子图直接终止整个主图
3. 多动作 step
4. planner state
5. runtime event bus + watchdog 初步成型
6. DOM/watchdog 开始并入 runtime

这意味着浏览器问题的主矛盾已经从“能不能打开浏览器”转向：

- browser state 是否由 runtime 正确管理
- runtime effect 是否能被 graph 正确消费
- planner 是否建立在足够稳定的 browser state 之上
