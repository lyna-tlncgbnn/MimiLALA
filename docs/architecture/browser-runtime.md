# Browser Runtime

## 背景

浏览器 agent 仍然是一个 LangGraph 子图，但子图下面的执行内核已经不再适合继续维持“几个 Playwright 函数 + 零散 handler”的结构。

前一阶段我们已经解决了这些问题：

- observation 太薄
- 元素映射不稳定
- planner 缺少持续状态
- 浏览器会话没有本地 profile 语义

这之后，主要矛盾变成了 runtime：

- 点击之后出现下载、popup、dialog、page close、navigation 时，如何统一建模
- 如何在动作执行期就把这些副作用回馈给 planner
- 如何避免“下载已经开始了，但 agent 以为没有开始又重复点击”
- 如何把 DOM 状态采集也并进统一 runtime，而不是 graph 直接绕过 runtime 去调页面

`browser-use` 在这部分更稳定，关键不是 prompt，而是它有完整的：

- session 容器
- event bus
- watchdog 分层
- 动作执行中间层
- BrowserStateRequestEvent -> DOMWatchdog -> cached browser state 链路

当前 AgentBot 的目标，就是在不破坏现有 LangGraph 子图外壳和 run-oriented persistence 主链路的前提下，把浏览器内核逐步对齐到这条结构。

## 当前分层

```text
browser_subgraph
  -> browser_nodes.py
    -> browser/actions.py
      -> browser/runtime/*
        -> browser/session.py
          -> Playwright / system browser session
```

其中：

- `browser_subgraph`
  负责 LangGraph 层的 prepare / observe / decide / act / evaluate / finish 闭环
- `browser_nodes.py`
  负责 graph state 更新、timeline event 和 planner/result 汇总
- `browser/actions.py`
  作为 graph 与 runtime 之间的兼容层，把 `BrowserAction` 翻译成 runtime 事件
- `browser/runtime/*`
  负责事件模型、watchdog 分层和动作执行中间层
- `browser/session.py`
  负责浏览器进程、本地 profile、downloads、artifacts、page/context 生命周期，以及 runtime 初始化

## Runtime V2 设计目标

当前 Runtime V2 的设计目标是：

1. 浏览器动作不再直接“执行一个 Playwright 调用就返回”，而是经过动作执行中间层。
2. 下载、popup、dialog、navigation、page lifecycle 这些副作用由 runtime 统一吸收。
3. DOM 状态不再由 graph 直接读页面，而是通过 runtime 请求当前 browser state。
4. graph 层尽量只消费结构化的 runtime effect 和 browser state，不直接推断底层浏览器细节。

## 代码结构

### 1. Session 层

核心文件：

- [session.py](/F:/AgentBot/agentbot/browser/session.py)

`BrowserRuntimeSession` 当前负责：

- 持有 `playwright / browser / context / page`
- 持有 `artifacts_dir / downloads_dir`
- 持有 system browser 模式下的：
  - `executable_path`
  - `user_data_dir`
  - `profile_directory`
  - `temp_profile_dir`
- 持有 runtime cache：
  - `cached_raw_observation`
  - `cached_browser_state`
  - `cached_selector_map`
  - `cached_screenshot_path`
  - `cached_observation_at`
- 持有 runtime effects：
  - `recent_events`
  - `downloaded_files`
  - `active_downloads`
  - `closed_popup_messages`
- 初始化并持有：
  - `event_bus`
  - `dom_watchdog`
  - `downloads_watchdog`
  - `popups_watchdog`
  - `dialogs_watchdog`
  - `navigation_watchdog`
  - `lifecycle_watchdog`
  - `default_action_watchdog`

当前它已经开始承担 `browser-use` 里 `BrowserSession` 的职责，但仍保持本项目现有的数据协议和生命周期接口。

### 2. Action compatibility 层

核心文件：

- [actions.py](/F:/AgentBot/agentbot/browser/actions.py)

当前职责：

- 保持 graph 侧仍然调用 `execute_browser_action()` / `execute_browser_actions()`
- 把 `BrowserAction` 翻译成 runtime action event
- 优先从 runtime cache 的 selector map 里取元素，而不是只依赖 graph state 里那份 summary
- 保持外层接口稳定，避免 graph 在 runtime 重构期间大面积改动

这层的目标不是长期承载所有逻辑，而是作为 runtime 演进阶段的稳定外壳。

### 3. Runtime event bus

核心文件：

- [event_bus.py](/F:/AgentBot/agentbot/browser/runtime/event_bus.py)
- [events.py](/F:/AgentBot/agentbot/browser/runtime/events.py)

当前事件分为三类。

动作事件：

- `NavigateActionEvent`
- `NewTabNavigateActionEvent`
- `ClickActionEvent`
- `TypeActionEvent`
- `PressEnterActionEvent`
- `ScrollActionEvent`
- `WaitActionEvent`
- `GoBackActionEvent`
- `SwitchTabActionEvent`

browser state 请求事件：

- `BrowserStateRequestEvent`

副作用事件：

- `PageCreatedEvent`
- `PageClosedEvent`
- `BrowserClosedEvent`
- `DialogHandledEvent`
- `NavigationCompletedEvent`
- `DownloadStartedEvent`
- `DownloadProgressEvent`
- `DownloadCompletedEvent`

当前 `BrowserStateRequestEvent` 是 DOM/watchdog 并入 runtime 的关键节点。它让 browser state 获取开始从“graph 直接调 `dom_service`”转向“graph 通过 runtime 请求当前 browser state”。

### 4. Watchdogs

核心目录：

- [watchdogs](/F:/AgentBot/agentbot/browser/runtime/watchdogs)

当前已经落地的 watchdog 有：

#### `default_action_watchdog`

文件：

- [default_action_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/default_action_watchdog.py)

负责：

- 真正执行 click / type / navigate / wait / switch_tab 等动作
- 收集动作之后的副作用
- 汇总成结构化 `BrowserActionResult`

这是当前最接近 `browser-use` 动作执行中间层的部分。

#### `downloads_watchdog`

文件：

- [downloads_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/downloads_watchdog.py)

负责：

- 接住 `DownloadStartedEvent`
- 在当前 Playwright 执行线程语义内保存文件到配置目录
- 发出 `DownloadCompletedEvent`
- 维护 `active_downloads`
- 给 click 动作提供 direct callbacks

它借鉴的是 `browser-use` 里“下载开始就是一等事件”的思路，而不是等文件最终保存完才知道发生了下载。

当前特别注意：

- 不再把 Playwright `Download` 对象丢给新的 Python 线程处理
- 否则会出现 `Cannot switch to a different thread` 这类 greenlet / thread 绑定错误
- 下载失败时现在会显式产出 `download_error`

#### `popups_watchdog`

文件：

- [popups_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/popups_watchdog.py)

负责：

- 统一记录新 tab / popup 创建
- 记录 page close 事件

#### `dialogs_watchdog`

文件：

- [dialogs_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/dialogs_watchdog.py)

负责：

- 统一记录 JS dialog 的处理结果

#### `navigation_watchdog`

文件：

- [navigation_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/navigation_watchdog.py)

负责：

- 统一记录主 frame 导航完成事件

#### `lifecycle_watchdog`

文件：

- [lifecycle_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/lifecycle_watchdog.py)

负责区分：

- `page_created`
- `page_closed`
- `active_page_closed`
- `browser_closed`

这一步很重要，因为以前很多关闭类异常都会被上层模糊理解成一句“浏览器关闭了”。

#### `dom_watchdog`

文件：

- [dom_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/dom_watchdog.py)

负责：

- 处理 `BrowserStateRequestEvent`
- 调用 raw capture + serialization
- 统一截图采集
- 缓存：
  - `cached_raw_observation`
  - `cached_browser_state`
  - `cached_selector_map`
  - `cached_screenshot_path`
- 在动作、导航、下载、page lifecycle 等事件发生后失效缓存

这部分直接借鉴的是 `browser-use` 的 `DOMWatchdog` 思路：

- browser state 应该由 runtime 统一提供
- selector map 应该是 runtime cache，而不是 graph 临时拼出来的一次性结果
- DOM 状态变化时，缓存应该由 runtime 自己失效

## 当前 browser state 链路

当前链路已经变成：

```text
browser_observe
  -> dom_service.capture_page_state()
    -> session.request_browser_state()
      -> BrowserStateRequestEvent
        -> DOMWatchdog
          -> observation_capture.capture_raw_observation()
          -> observation_serialize.serialize_raw_observation()
          -> runtime cache update
          -> optional screenshot capture
```

也就是说：

- graph 层不再自己组装 browser state
- `dom_service` 现在只是 runtime request 的入口封装
- 真正的 browser state 生产者已经变成 DOMWatchdog

## 当前动作执行链

对一个 `click` 来说，当前链路大致是：

```text
browser_decide
  -> BrowserAction(click)
    -> actions.py
      -> runtime cached selector map / summary resolve
  -> ClickActionEvent

## System Browser 下载目录对齐

这一步专门对齐了 `browser-use` 在下载目录上的核心思路：浏览器原生下载目录和 runtime 感知到的下载目录，不能是两套路径。

`browser-use` 在这层的关键点是：

- profile 层有统一的 `downloads_path`
- downloads watchdog 会围绕这一个目录建模
- 浏览器启动后，下载行为本身就会被配置到这个目录，而不是只在 agent 内部记一个“希望保存到哪里”

AgentBot 之前的 system browser 模式存在一个分叉：

- `runtime.downloads_dir` 可能已经是 [browser_downloads](/F:/AgentBot/workspace/browser_downloads)
- 但复制出来的临时浏览器 profile 仍然可能沿用浏览器自己的默认下载目录
- 于是“配置里写的是一个目录，浏览器自己实际下载去的又是另一个目录”

当前修正后的做法是两层同时生效：

1. 在 `workspace/browser_profiles/<session_id>/...` 的临时 profile 中写入 `Preferences`
   - `download.default_directory`
   - `download.prompt_for_download = false`
   - `download.directory_upgrade = true`
   - `savefile.default_directory`
2. 在 `launch_persistent_context(...)` 时显式传入 `downloads_path`

这样 system browser 模式下：

- 浏览器原生下载默认落到 [browser_downloads](/F:/AgentBot/workspace/browser_downloads)
- runtime 下载 watchdog 看到的目录也是这个目录
- 下载目录不再只是一条 runtime 状态，而是浏览器自身的默认行为

## System Browser 启动模式

当前 system browser 模式已经不再把 `Playwright launch_persistent_context(...)` 当作主运行时。

这一步是为了更接近 `browser-use` 的本机浏览器模式。当前链路变成：

1. 读取本地浏览器可执行文件、`User Data` 和 `profile_directory`
2. 把指定 profile 复制到 [browser_profiles](/F:/AgentBot/workspace/browser_profiles) 下的临时 session 目录
3. 直接启动本机浏览器子进程，并附加：
   - `--user-data-dir=...`
   - `--profile-directory=...`
   - `--remote-debugging-port=...`
4. 等待 CDP 端口就绪
5. 通过 `connect_over_cdp(...)` 接回这个真实浏览器进程

这样 system 模式的本质就从：

- “Playwright 自己创建 persistent context，并顺带借用本地 profile”

变成了：

- “真实本机浏览器进程自己运行，AgentBot 通过 CDP 接管和观察”

这一步的直接收益是：

- 手动操作浏览器更接近真实本机浏览器行为
- tab / popup / 下载等副作用不再被过度包裹在 Playwright persistent context 语义里
- 后续继续对齐 `browser-use` 的 downloads / lifecycle / DOM watchdog 会更自然

## 下载文件名收口策略

对齐 `browser-use` 后，下载链路不再只关心“文件有没有落盘”，还要保证最终文件名尽量贴近站点给出的业务文件名。

这是因为在 system browser / persistent context 模式下，浏览器原生下载目录里有时会先出现内部 GUID 文件名，而不是用户期望的安装包名字。

当前 runtime 的处理策略是：

1. `download_started` 时先记录：
   - `download_id`
   - `suggested_filename`
   - 当时下载目录里的已有文件快照
2. 同时启动一个下载目录后台监控线程，持续观察新的浏览器原生文件是否出现
3. 如果 click 那一轮就顺利拿到了 Playwright `Download` 完成态，则直接按 `suggested_filename` 收口
4. 如果 click 当轮没来得及收口，后台监控和后续 `BrowserStateRequestEvent` 都会继续扫描下载目录
5. 发现新的浏览器原生文件后，会优先映射回 `suggested_filename`，并把 GUID / 原生文件路径收口成最终文件名

这一步的目标是：

- planner 看到的下载文件名和用户实际得到的文件名一致
- 避免目录里长期留下浏览器内部 GUID 名称
- 让 system browser 模式更接近 `browser-use` 那种“下载事件和最终文件路径围绕 suggested filename 对齐”的行为

## 临时 Profile 清理策略

`browser.mode = "system"` 时，AgentBot 会把本地浏览器 profile 复制到 [browser_profiles](/F:/AgentBot/workspace/browser_profiles) 下的临时 session 目录，再用它启动浏览器。

当前清理策略是：

1. 浏览器正常关闭时，删除当前 session 的临时 profile 目录
2. 每次新的 system browser session 启动前，再扫描 [browser_profiles](/F:/AgentBot/workspace/browser_profiles)
3. 清理所有不属于当前活动会话的 `browser_session_*` 遗留目录

这样做的目标是：

- 正常运行时尽量不留下临时 profile 垃圾
- 上一次异常退出后遗留的目录，下次启动前也会自动兜底清理
- 避免误删当前还在运行中的活跃会话目录
        -> default_action_watchdog
          -> locator.click()
          -> wait popup/new tab
          -> wait download_started
          -> wait download_completed or mark download_in_progress
          -> collect runtime effects
          -> BrowserActionResult
```

planner 现在已经不只是知道“点了一个按钮”，还可以知道：

- 页面是否变化
- 是否新开 tab
- 是否出现 dialog
- 是否已经开始下载
- 是否下载完成
- 是否下载保存失败
- 是否处于下载中
- 是否出现 active page close / browser close

## DOM/watchdog 并入 runtime 后带来的变化

### 1. selector map 开始归 runtime 持有

以前稳定 selector 虽然已经有了，但 graph 仍然强依赖 state 里那份 summary。

现在：

- DOMWatchdog 会把 `interactive_elements` 缓存成 runtime selector map
- 动作层优先从 runtime cache 解析 element index
- 这让“当前 observation 对应的元素映射”开始真正归 runtime 管

### 2. browser state cache 开始明确失效

DOMWatchdog 会在这些事件后失效缓存：

- navigate
- new_tab_navigate
- click
- type
- press_enter
- scroll
- wait
- go_back
- switch_tab
- page_created
- page_closed
- navigation_completed
- download_started
- download_completed
- dialog_handled

也就是说，DOM cache 不再只是“最后一次 observe 的偶然结果”，而开始成为 runtime 管理的资源。

### 3. screenshot 也归入 browser state 请求

`capture_page_state()` 现在不再自己直接截图，而是由 DOMWatchdog 在处理 browser state request 时决定是否截图并把路径一起返回。

### 4. recent events 继续保留，但降级成 runtime 输出的一部分

recent events 仍然会进入 planner 可见的 browser state summary，但它们不再是浏览器副作用的唯一表达方式。副作用的真实来源已经开始变成 runtime events + watchdog cache。

## 下载问题是怎么被修的

以前的问题是：

1. agent 点击下载按钮
2. 网站在 1 到 2 秒后才真正触发下载
3. 当前 step 没看到下载信号
4. planner 误以为“没反应”
5. 又点一次

现在的做法是：

1. click 执行时注册下载 callbacks
2. 在 grace period 内如果收到 `download_started`
   这一轮就已经算“有有效进展”
3. 如果很快完成，就带 `download`
4. 如果还没完成，就带 `download_in_progress`
5. graph 层据此不再把这一轮理解成“无反应”

相关配置：

- `browser.download_start_timeout_seconds`
- `browser.download_complete_timeout_seconds`

定义位置：

- [settings.py](/F:/AgentBot/agentbot/config/settings.py)
- [config.json](/F:/AgentBot/config.json)

## 当前和 browser-use 的对齐情况

### 已经明显对齐的部分

- session 作为统一 runtime 容器
- event bus + watchdog 分层
- 下载开始就是一等事件
- 动作执行中间层开始稳定化
- BrowserStateRequestEvent -> DOMWatchdog -> cached state 链路
- selector map 和 browser state cache 开始归 runtime 持有

### 仍未完全对齐的部分

- 还没有 browser-use 那种更完整的 CDP target/session 管理
- 还没有完整的 DOM / AX tree CDP 建模
- 还没有统一的 runtime effect object 类型层
- graph 仍然会消费一些由旧结构保留下来的平铺字段
- 还没有完全实现 browser-use 等级的 session/watchdog 生命周期管理

## 当前边界

当前继续保持这些边界不变：

- 浏览器 agent 仍然是 LangGraph 子图
- transcript / runs / run_steps / checkpoints 不改协议
- 前后端时间线仍然基于 `browser_events`
- graph 仍然通过 `execute_browser_action(s)` 和 `capture_page_state()` 进入浏览器域

也就是说，这一轮仍然是“内核升级”，不是“外层重写”。

## 当前阶段

这一阶段可以称为：

**Browser Runtime V2**

目前已经完成：

### Phase 1

- runtime skeleton
- event bus
- default action / downloads / popups watchdog
- system browser profile 模式
- 下载开始与下载中的语义进入 graph

### Phase 2

- dialogs watchdog
- navigation watchdog
- lifecycle watchdog
- `page_closed / active_page_closed / browser_closed` 区分

### Phase 3

- DOMWatchdog
- BrowserStateRequestEvent
- runtime browser state cache
- runtime selector map cache
- `dom_service` 切到 runtime request 入口
- graph 动作执行优先使用 runtime selector map

## 下一步

接下来最自然的方向是：

1. 继续把更多 browser state 元数据并进 runtime，而不是由 graph 自己推断
2. 把 runtime effect 逐步收紧成统一结构，而不是平铺在多个 output 字段里
3. 继续对齐 `browser-use` 的 page lifecycle / target lifecycle 组织方式
4. 再评估是否继续推进更重的 CDP DOM/AX tree 建模
