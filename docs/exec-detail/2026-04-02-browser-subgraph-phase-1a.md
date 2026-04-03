# 2026-04-02 Browser Subgraph Phase 1A

## 本次执行目标

根据 `docs/exec-plans/active/browser-subgraph-phase-1.md`，先完成 Phase 1A：

- 搭建 browser 子图骨架
- 把 browser 子图接入主图
- 打通 browser 中间步骤的统一落库和前端可见性

本次不引入真实浏览器自动化动作，重点先落：

- graph 结构
- state 结构
- run_steps 数据流

## 本次实现

### 1. graph state 扩展

修改文件：

- `agentbot/graph/state.py`

当前主图 state 不再只是纯 `messages`，还加入了 browser 子图相关字段，例如：

- `browser_task`
- `browser_status`
- `browser_result`
- `browser_session_id`
- `browser_current_url`
- `browser_events`

其中 `browser_events` 作为子图到运行时落库层的桥接字段，用于携带 browser step 事件。

### 2. 新增 browser 支撑目录

新增文件：

- `agentbot/browser/__init__.py`
- `agentbot/browser/session.py`
- `agentbot/browser/views.py`

当前第一版只引入最小模型：

- `BrowserSessionState`
- `BrowserTabInfo`
- `BrowserPageInfo`
- `BrowserStateSummary`

这部分参考了 `browser-use` 的会话与状态摘要思路，但保持了明显精简。

### 3. 新增 browser 子图

新增文件：

- `agentbot/graph/browser_nodes.py`
- `agentbot/graph/browser_subgraph.py`

当前子图节点为：

- `browser_prepare`
- `browser_observe`
- `browser_finish`

当前能力仍是 skeleton：

- 检测 browser task
- 初始化最小 browser session
- 生成最小页面观察摘要
- 返回 browser 结果

### 4. 主图接入 browser subgraph

修改文件：

- `agentbot/graph/builder.py`
- `agentbot/graph/routes.py`

当前主图新增：

- `browser_intent` 节点
- `route_after_intent`
- `browser_subgraph` node

因此当前 graph 已变为：

```text
START
  -> browser_intent
    -> browser_subgraph
    -> chatbot
```

浏览器任务先按显式规则分流：

- 文本中出现 URL
- 或出现明显 browser / 网页相关关键词

这属于 Phase 1A 的最小接入策略，后续再继续优化 intent 判断。

### 5. browser 中间步骤落库打通

修改文件：

- `agentbot/storage/shadow_runtime.py`
- `agentbot/app/graph_runtime_events.py`
- `agentbot/app/runner.py`
- `agentbot/app/streaming_runner.py`

本次新增了通用 step 记录能力，不再只支持 tool_call：

- `record_step_started`
- `record_step_finished`

并新增：

- `named_steps`

用于管理 browser 子图中自定义 step key 到真实 `step_id` 的映射。

### 6. streaming 与 sync 两条链路都接入 browser updates

当前 browser 子图节点会产出 `browser_events`。

这些事件会被统一转换为：

- SQLite `run_steps`
- SSE `step_started / step_completed`

因此：

- 流式链路可以实时看到 browser 子图步骤
- 同步链路也能保持统一的 run_steps 落库

## 参考与借鉴

本次主要借鉴了 `F:\browser-use` 的以下思想：

- `browser/session.py`
  专属浏览器会话对象
- `browser/views.py`
  浏览器状态摘要建模
- `agent/views.py`
  将浏览器执行过程中的状态与动作抽成独立结构

本次没有迁移：

- `browser-use` 的 Agent 主循环
- 其 controller / cloud / watchdog 体系

LangGraph 仍然作为 AgentBot 的主执行大脑。

## 验证结果

本次完成后已验证：

1. `compileall agentbot` 通过
2. 主图可识别显式 browser task 并进入 `browser_subgraph`
3. browser 子图能产出多条 `browser_events`
4. `browser_events` 可转换为统一 `run_steps`
5. `run_steps` 中能够形成：
   - browser 根 step
   - browser_prepare
   - browser_observe
   - browser_finish
6. browser 子图可直接生成最终 assistant 消息，证明完整执行链条已经贯通

## 当前边界

当前 Phase 1A 仍是骨架版本：

- 还没有真实浏览器驱动
- 还没有真实 DOM snapshot
- 还没有 click / type / scroll 等动作
- browser intent 仍是显式规则分流

但已经完成了后续阶段最关键的底座：

- 子图接入
- 独立 browser state
- browser step 实时落库
- 前端 timeline 可见性通路

## 下一步建议

下一阶段进入 Phase 1B，优先补：

- 最小 browser action 接口
- 最小 `BrowserStateSummary` 丰富化
- 与真实浏览器/页面读取层的第一步接入
