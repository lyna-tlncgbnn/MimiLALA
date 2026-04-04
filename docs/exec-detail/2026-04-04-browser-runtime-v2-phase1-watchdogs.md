# 2026-04-04 Browser Runtime V2 Phase 1-2: Event Bus and Watchdogs

## 背景

这一阶段的浏览器问题，已经不再是“能不能点到元素”，而是：

- 下载开始得比较慢，当前 step 看不到下载信号
- popup / new tab / page close 混在一起
- graph 层拿不到足够明确的 runtime 中间态

因此这次改动不是继续在 `actions.py` 上打补丁，而是把浏览器执行层升级成更接近 `browser-use` 的 runtime 结构。

## 目标

构建 Browser Runtime V2 的前两段基础设施：

1. 建立 event bus
2. 建立 watchdog 分层
3. 把动作执行改成“事件驱动的中间层”
4. 让下载、popup、dialog、navigation、page close、browser close 进入统一 runtime 模型

## 本次新增结构

### runtime 目录

- [runtime](/F:/AgentBot/agentbot/browser/runtime)
- [watchdogs](/F:/AgentBot/agentbot/browser/runtime/watchdogs)

### 基础文件

- [__init__.py](/F:/AgentBot/agentbot/browser/runtime/__init__.py)
- [event_bus.py](/F:/AgentBot/agentbot/browser/runtime/event_bus.py)
- [events.py](/F:/AgentBot/agentbot/browser/runtime/events.py)
- [watchdog_base.py](/F:/AgentBot/agentbot/browser/runtime/watchdog_base.py)

### watchdog 文件

- [default_action_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/default_action_watchdog.py)
- [downloads_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/downloads_watchdog.py)
- [popups_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/popups_watchdog.py)
- [dialogs_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/dialogs_watchdog.py)
- [navigation_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/navigation_watchdog.py)
- [lifecycle_watchdog.py](/F:/AgentBot/agentbot/browser/runtime/watchdogs/lifecycle_watchdog.py)

## 代码改动

### session 层

文件：

- [session.py](/F:/AgentBot/agentbot/browser/session.py)

新增：

- `event_bus`
- `downloads_watchdog`
- `popups_watchdog`
- `dialogs_watchdog`
- `navigation_watchdog`
- `lifecycle_watchdog`
- `default_action_watchdog`
- `active_downloads`
- `latest_download_id`
- 下载相关 timeout 配置

变化：

- page/context handler 不再直接承担全部业务逻辑
- page/download/dialog/navigation/close 事件优先转成 runtime event
- 再由 watchdog 把这些事件翻译成统一 runtime facts

### actions 层

文件：

- [actions.py](/F:/AgentBot/agentbot/browser/actions.py)

变化：

- 保持 graph 侧调用方式不变
- 内部改成把 `BrowserAction` 转成 runtime action event
- 再由 `default_action_watchdog` 执行具体动作

### graph 层

文件：

- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

新增对这些中间态的识别：

- `download_started`
- `download_in_progress`
- `download`

它们现在会影响：

- progress signal
- completion assessment
- finish summary

## 下载链路变化

### 旧链路

旧行为大致是：

1. click
2. 短时间扫一下目录 / recent events
3. 没看到下载
4. planner 误判无进展
5. 再点一次

### 新链路

新行为大致是：

1. `ClickActionEvent`
2. `default_action_watchdog` 执行 click
3. `downloads_watchdog` 在 download 开始时立刻发出 `download_started`
4. click 当前轮等待 grace period
5. 如果下载已开始：
   - 已完成则记 `download`
   - 未完成则记 `download_in_progress`
6. graph 层据此不再把这一轮当成“无反应”

### 后续修正：下载对象线程语义

在真实站点验证中，又发现了一类更深的下载问题：

- 下载开始事件确实触发了
- 但下载保存逻辑把 Playwright `Download` 对象丢进了新的 Python 线程
- 导致出现 `Cannot switch to a different thread`
- 最终变成“下载开始了，但保存失败；graph 又把它误解成没有下载”

后续修正后的做法是：

- 保留 `download_started` 作为 click 当轮的强信号
- 但不再用 `threading.Thread` 调 `download.save_as(...)`
- 改回当前 Playwright 执行线程语义里完成保存
- 保存失败时显式记录 `download_error`

这一步仍然遵循 `browser-use` 的核心原则：

- direct callback 负责让 click 立即知道下载开始
- 真正的下载处理不能把底层浏览器对象丢到错误的线程模型里

## lifecycle 语义变化

以前很多关闭类场景最后都会被上层模糊理解成：

- browser closed

这次开始拆成：

- `page_created`
- `page_closed`
- `active_page_closed`
- `browser_closed`

这给后续的 popup / page replacement / browser disconnect 分析打下了基础。

## 配置变化

文件：

- [config.json](/F:/AgentBot/config.json)
- [settings.py](/F:/AgentBot/agentbot/config/settings.py)

新增：

- `browser.download_start_timeout_seconds`
- `browser.download_complete_timeout_seconds`

## 验证

运行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果：通过。

## 阶段结论

这一阶段还不是浏览器 runtime 的最终形态，但已经完成了两个关键跃迁：

1. 从“直接调浏览器动作”升级成“动作事件 -> watchdog -> 结构化结果”
2. 从“下载 / 关闭 / 导航字符串日志”升级成“runtime 中间态模型”

这为后续继续把 DOM/watchdog、browser state request、selector map cache 并入 runtime 奠定了基础。

## 补充修正：system browser 默认下载目录

在把 system browser 模式切到“本地浏览器 profile -> workspace 临时 profile”之后，又暴露出一个更隐蔽的问题：

- runtime 状态里的 `downloads_dir` 已经指向了 [browser_downloads](/F:/AgentBot/workspace/browser_downloads)
- 但浏览器原生下载行为不一定真的使用这个目录
- 导致某些站点虽然下载触发了，最终文件却没有稳定落到配置目录

对照 `browser-use` 后，可以看到它的关键不是只在内存里记一个 downloads path，而是让浏览器下载行为本身也使用这个路径。

这次修正做了两件事：

1. 在 system browser 临时 profile 的 `Preferences` 中写入下载相关配置
   - `download.default_directory`
   - `download.prompt_for_download = false`
   - `download.directory_upgrade = true`
   - `savefile.default_directory`
2. 在 `launch_persistent_context(...)` 中显式传入 `downloads_path`

这样调整后，system 模式下的“浏览器原生默认下载目录”和“runtime 观察/汇总下载事件时使用的目录”会统一到同一个路径，不再继续分叉。

## 补充修正：临时 profile 自动清理

在 system browser 模式稳定后，又出现了一个工程性问题：`workspace/browser_profiles` 会随着多次调试留下大量 `browser_session_*` 临时目录。

这次补充的策略是：

1. 正常 `close_browser_session(...)` 时，删除当前 session 的 `temp_profile_dir`
2. 新的 system browser session 启动前，扫描 `browser_profiles` 根目录
3. 清理所有不属于当前活动会话的 `browser_session_*` 遗留目录

这样做不是“每次全删”，而是：

- 保留当前活动会话的临时 profile，不影响正在运行的浏览器
- 自动回收异常退出或历史调试留下的旧目录
- 让 `workspace/browser_profiles` 持续保持可控，不需要长期手动打扫

## 补充修正：下载文件名收口

在微信下载场景里，又暴露出另一个和 `browser-use` 行为差异较大的问题：

- `download_started` 事件里拿到的 `suggested_filename` 是正确的，例如 `WeChatWin_4.1.8.exe`
- 但 system browser 的原生下载目录里，最终有时只留下浏览器内部 GUID 文件名
- 这样用户看到的下载结果和 planner/summary 里描述的文件名会不一致

为此，这次把下载完成收口逻辑继续向 `browser-use` 靠拢：

1. 下载开始时，记录 `suggested_filename` 和下载前目录快照
2. 如果当前 action 轮次就能直接完成保存，则按 `suggested_filename` 生成最终路径
3. 如果 action 轮次里没来得及收口，后续在 `BrowserStateRequestEvent` / DOM 观察阶段，会再次对下载目录做 reconcile
4. 一旦发现新的浏览器原生下载文件，会优先把它映射并收口成 `suggested_filename`

这让下载链从“浏览器原生文件怎么落盘就怎么认”变成了：

- runtime 长期持有业务文件名语义
- 下载目录里的最终文件也尽量与业务文件名一致

不过真实验证后又发现，仅靠一次 `observe` 时的 reconcile 还不够稳：

- 微信安装包这种大文件，`download_started` 很快就会触发
- 但真正的浏览器原生文件可能要过几十秒才稳定出现在下载目录
- 如果 agent 在下载开始后很快就结束流程，单次 reconcile 经常赶不上最终文件出现

因此又补了一层更接近 `browser-use` 思路的“持续监控”：

1. `download_started` 时除了记录 `suggested_filename`，还会启动下载目录后台监控线程
2. 后台线程只做文件系统轮询，不跨线程触碰 Playwright `Download` 对象
3. 一旦发现新的浏览器原生文件，会尝试把它收口为 `suggested_filename`
4. 如果文件仍在占用中导致暂时无法重命名，会继续轮询直到超时或成功

这样下载完成收口不再依赖“某一次 observe 恰好发生在正确的时间点”，而是有了持续的完成态跟踪。

## 补充修正：system 模式切到本机浏览器进程 + CDP

后续继续验证时，又暴露出一个更根上的问题：

- 即使不是 agent 自动点击，而是人手动在 agent 打开的浏览器里点下载
- 最终落盘的仍然是 GUID 文件名

这说明问题已经不在 planner、action runtime 或下载后处理时机，而在 system browser 的底层运行模式本身。

之前的 system 模式虽然已经引入了本地 profile 和临时目录，但本质上仍然是：

- `playwright.chromium.launch_persistent_context(...)`

这意味着浏览器下载、tab、popup 等行为仍然带有明显的 Playwright persistent context 语义。

为此，这一轮把 system 模式主链真正切到了更接近 `browser-use` 的模式：

1. 复制本地 profile 到 `workspace/browser_profiles/<session_id>/...`
2. 直接启动本机浏览器子进程
3. 为该进程附加 `--remote-debugging-port`
4. 等待 CDP 端口就绪
5. 使用 `connect_over_cdp(...)` 连接回真实浏览器进程

这样 system 模式不再是“Playwright 自己拥有一个 persistent context”，而更像：

- 真实浏览器自己运行
- AgentBot 通过 CDP 连接、观察、执行动作

这一步还不是 browser runtime V3 的全部终点，但它已经完成了最关键的底盘换轨。
