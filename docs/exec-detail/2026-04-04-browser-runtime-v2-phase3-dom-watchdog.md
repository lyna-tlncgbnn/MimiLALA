# 2026-04-04 Browser Runtime V2 Phase 3: DOMWatchdog Integration

## 背景

在 Runtime V2 Phase 1-2 之后，浏览器 runtime 已经有了：

- event bus
- default action watchdog
- downloads / popups / dialogs / navigation / lifecycle watchdog

但 browser state 这条链路仍然有一个明显缺口：

- graph 还是通过 `dom_service.py` 直接读取页面
- selector map 还没有真正归 runtime 管理
- browser state cache 也不在 runtime 内核里

这和 `browser-use` 的关键结构不一致。

`browser-use` 的做法是：

```text
BrowserStateRequestEvent
  -> DOMWatchdog
    -> DomService
    -> cache selector_map / dom_state / screenshot
```

所以这一阶段的目标是：把 DOM/watchdog 也并进 runtime 总线，让 graph 通过 runtime 请求 browser state，而不是自己越过 runtime 直接采页面。

## 目标

1. 新增 runtime 级 browser state request 事件。
2. 新增 DOMWatchdog。
3. 让 DOMWatchdog 负责 browser state 构建、截图和 cache。
4. 让 selector map 开始归 runtime 持有。
5. 收紧 graph/action 层对 runtime state 的消费方式。

## 本次代码改动

### 1. 新增 `BrowserStateRequestEvent`

文件：

- [events.py](/F:/AgentBot/agentbot/browser/runtime/events.py)

新增事件：

- `BrowserStateRequestEvent`

字段：

- `include_screenshot`
- `include_recent_events`

作用：

- graph 或兼容层不再直接假定如何构建 browser state
- 统一通过 runtime event bus 请求当前 browser state

### 2. 新增 `DOMWatchdog`

文件：

- [dom_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/dom_watchdog.py)

当前职责：

- 监听 `BrowserStateRequestEvent`
- 调用 raw capture 和 serialization
- 处理 screenshot capture
- 写入 runtime cache
- 在动作、下载、导航、page lifecycle 等事件后失效 cache

当前缓存内容：

- `cached_raw_observation`
- `cached_browser_state`
- `cached_selector_map`
- `cached_screenshot_path`
- `cached_observation_at`

### 3. session 接入 DOMWatchdog

文件：

- [session.py](/F:/AgentBot/agentbot/browser/session.py)

本次变更：

- `BrowserRuntimeSession` 增加 DOM 相关 cache 字段
- `BrowserRuntimeSession` 增加 `dom_watchdog`
- `_initialize_runtime_watchdogs()` 里注册 DOMWatchdog
- 新增 `request_browser_state(runtime, ...)`

现在 browser state 请求已经有了统一入口：

```text
request_browser_state(runtime)
  -> event_bus.request(BrowserStateRequestEvent)
```

### 4. `dom_service.py` 改成 runtime 入口封装

文件：

- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

本次变更：

- `capture_page_state()` 不再自己直接调 raw capture + serialize + screenshot
- 改为通过 `request_browser_state()` 走 runtime
- 新增 `build_browser_state_summary()` 作为 summary-only 入口

这一步让 `dom_service.py` 从“自己做 observation 的实现层”转成“对 graph 暴露的 browser state 入口层”。

### 5. 动作执行优先使用 runtime selector map

文件：

- [actions.py](/F:/AgentBot/agentbot/browser/actions.py)

本次变更：

- `_find_element(...)` 现在优先从 `runtime.cached_selector_map` 取元素
- 如果 runtime cache 没有，再退回 graph state 里的 summary

这样做的目的，是让“最新 observation 对应的元素映射”开始真正归 runtime 管理，而不是 graph 和 runtime 各拿一份副本各自理解。

### 6. observation capture / 类型依赖清理

文件：

- [observation_capture.py](/F:/AgentBot/agentbot/browser/observation_capture.py)
- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

本次变更：

- 把 `BrowserRuntimeSession` 的导入改成 type-only / string annotation
- 减少 session -> watchdog -> DOM -> session 之间的循环导入风险

## 当前链路变化

### 旧链路

```text
browser_observe
  -> dom_service.capture_page_state()
    -> capture_raw_observation()
    -> serialize_raw_observation()
    -> page.screenshot()
```

问题：

- graph 直接知道太多 observation 细节
- runtime 不持有 DOM state cache
- selector map 不归 runtime

### 新链路

```text
browser_observe
  -> dom_service.capture_page_state()
    -> request_browser_state()
      -> BrowserStateRequestEvent
        -> DOMWatchdog
          -> capture_raw_observation()
          -> serialize_raw_observation()
          -> screenshot
          -> runtime cache
```

好处：

- browser state 生产职责进入 runtime
- DOM cache 统一由 runtime 失效和管理
- selector map 与动作执行层开始共享同一份 runtime 语义

## 这一步和 browser-use 的对齐点

直接参考的核心逻辑是：

- browser state 应该通过事件请求，而不是 graph 直接构建
- DOMWatchdog 应该缓存 browser state 和 selector map
- DOM 状态变化后应由 runtime 主动失效缓存

虽然我们还没有整体迁移成 browser-use 那套完整 CDP DOM/AX tree 体系，但在架构职责上，这一阶段已经开始明显对齐它的：

- `BrowserStateRequestEvent`
- `DOMWatchdog`
- runtime cache
- graph 与 runtime 的分层边界

## 验证

运行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果：通过。

这次验证重点是：

- DOM/watchdog 接入后没有引入循环导入
- `dom_service.py` 改走 runtime 后仍然可以编译通过
- runtime package 与 session/watchdogs 的导入链保持可用

## 当前阶段结论

这一步的意义不在于“页面摘要看起来有什么变化”，而在于浏览器内核边界发生了变化：

- browser state 不再由 graph 直接拥有
- runtime 开始真正拥有 DOM state 和 selector map
- graph 开始更像 browser-use 那样，只请求 browser state，然后消费 runtime 给出的事实

这为后续继续做这些事情打下了基础：

1. 统一 runtime effect object
2. 收紧 graph 对 runtime effects 的消费
3. 继续把 DOM / lifecycle / downloads / popups 组织成更完整的 browser runtime
