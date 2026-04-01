# 2026-03-31 Browser Subgraph Phase 1 Implementation

## 本次执行目标

本次执行基于 `docs/exec-plans/active/browser-subgraph-phase-1.md`，目标不是一次性做完整浏览器 agent，而是先落地一个**最小可运行的浏览器子图**。

本次阶段目标聚焦于：

- 在当前项目中引入独立的 LangGraph 浏览器子图
- 保留 LangGraph 作为唯一编排层
- 不直接复用 `browser-use` 的 agent loop
- 复用 `browser-use` 的浏览器执行层能力
- 提供一个可显式调用的最小浏览器入口
- 优先跑通启动、观察、规划、执行、结束这条链路

## 本次实际完成内容

### 1. 新增浏览器子图状态与数据模型

新增文件：

- `agentbot/models/browser.py`
- `agentbot/graph/browser_state.py`

本次新增了浏览器子图第一阶段所需的最小数据模型，包括：

- `BrowserActionPlan`
- `BrowserObservation`
- `BrowserActionResultModel`
- `BrowserStepRecord`
- `BrowserTaskResult`
- `BrowserSubgraphState`

这些模型承担的职责是：

- 把浏览器动作规划收敛为固定结构
- 让浏览器子图使用独立 typed state
- 让最终 API 返回有稳定结构

当前动作类型只保留了第一阶段最小集合：

- `navigate`
- `click`
- `input`
- `done`

### 2. 新增浏览器子图本体

新增文件：

- `agentbot/graph/browser_nodes.py`
- `agentbot/graph/browser_routes.py`
- `agentbot/graph/browser_builder.py`

本次落地了一个真正的 LangGraph 浏览器子图，而不是把另一个黑盒 agent 塞进单节点。

当前子图节点包括：

- `browser_enter`
- `browser_observe`
- `browser_plan`
- `browser_act`
- `browser_finish`

当前路由结构为：

```text
START
  -> browser_enter
  -> browser_observe
  -> browser_plan
     -> browser_act
     -> browser_finish
browser_act
  -> browser_observe
  -> browser_finish
browser_finish
  -> END
```

这意味着第一阶段已经具备：

- 独立浏览器子图
- 单步规划
- 单步执行
- 按条件继续或结束

### 3. 新增 browser-use 运行时桥

新增文件：

- `agentbot/services/browser_runtime.py`
- `agentbot/browser_worker.py`

这是本次实现里最关键的实际工程决策。

由于当前 `AgentBot` 自己的 `.venv` 中**没有**安装 `browser-use` 及其完整依赖，本次没有把 `browser-use` 直接装进 `AgentBot` 环境，而是采用了：

**主进程 + 独立 worker 子进程**

的方案。

具体方式：

- `AgentBot` 主进程继续使用当前项目自己的 `.venv`
- 浏览器 worker 使用 `F:\browser-use\.venv\Scripts\python.exe`
- worker 内部导入 `F:\browser-use` 下的真实 `browser_use` 包
- 主进程通过 stdin/stdout JSON 协议和 worker 通信

也就是说，当前集成方式不是“软链接”，也不是“本项目环境内直接 import browser-use 依赖”，而是：

**跨虚拟环境 subprocess 集成**

这样做的好处是：

- 第一阶段风险更小
- 不污染当前项目依赖
- 可以先跑通 browser-use 能力接入

### 4. worker 中实际复用的 browser-use 能力

当前 worker 实际复用了以下 browser-use 执行层能力：

- `BrowserSession`
- `Tools`
- `NavigateAction`
- `ClickElementActionIndexOnly`
- `InputTextAction`

当前没有复用：

- `browser_use.agent.service.Agent`
- `browser_use.agent.message_manager`
- `browser_use.agent.prompts`
- `browser_use.agent.judge`

也就是说，本次实现遵守了原计划的关键边界：

**LangGraph 负责编排，browser-use 负责 browser runtime。**

### 5. 新增显式浏览器任务服务入口

新增文件：

- `agentbot/services/browser.py`

该服务新增了：

- `BrowserTaskService.run_task(...)`

这一层负责：

- 构建浏览器子图
- 传入最小任务输入
- 接收最终结构化结果

当前仍然没有直接接入聊天主图自动路由。

本次先采用了“显式入口优先”的策略，目的是降低第一阶段改动面，避免影响已有聊天主链路。

### 6. 新增浏览器 API 路由

新增或修改文件：

- `agentbot/api/routes/browser.py`
- `agentbot/api/schemas.py`
- `agentbot/api/app.py`

当前新增了显式浏览器任务接口：

- `POST /api/browser/tasks`

请求体支持：

- `task`
- `start_url`
- `max_steps`

响应返回：

- `status`
- `final_response`
- `error_message`
- `current_url`
- `page_title`
- `step_count`
- `steps`

这意味着第一阶段已经有了一个不依赖聊天主链路的浏览器能力入口，便于独立联调。

## 本次过程中出现的实际问题与修正

### 1. browser-use 依赖不在 AgentBot 的虚拟环境中

在实现初期，直接从 `AgentBot` 当前环境导入 `browser_use` 会失败，因为：

- `python-dotenv` 等依赖缺失
- `pydantic_core` 的 Python 版本与当前解释器不匹配

最终没有在本次阶段里强行统一依赖，而是改为 worker 子进程方案。

这是一个明确的阶段性技术选择。

### 2. browser-use 默认下载目录在当前环境下触发权限问题

在 worker 首次启动中，`browser-use` 默认会在 `/tmp` 下创建下载目录。当前环境中这一行为触发了 Windows 权限问题。

本次修正：

- 强制把 `TMP` / `TEMP` / `TMPDIR` 指向项目 `workspace`
- 在 worker 中为浏览器运行显式指定下载目录

### 3. browser worker 启动阶段可能长时间阻塞

在调试过程中，worker 会在 browser-use 启动本地浏览器时长时间卡住。

本次修正：

- 在 `browser_runtime.py` 中为 worker 响应增加明确超时
- worker 超时后主动 kill 子进程
- 把错误信息回传给主进程

这样做之后，即使浏览器启动失败，也不会无限挂起。

### 4. API 初期会直接抛出 500 traceback

初期实现中，如果浏览器启动失败，FastAPI 会直接抛出 500。

本次修正：

- 在 `BrowserTaskService.run_task(...)` 中包裹异常
- 将失败统一转换为结构化 `BrowserTaskResult`

现在浏览器任务失败时会返回：

- `status="failed"`
- `error_message="..."`

而不是整段 traceback 直接透出给前端调用方。

### 5. 固定 profile 目录导致 Windows 文件锁冲突

在本地联调中，浏览器已经能够进入更深阶段，但出现了明显的 Windows 文件锁问题，典型报错文件包括：

- `Cookies`
- `Cookies-journal`
- `Safe Browsing Cookies`
- `Sessions/...`

问题原因是：

- 复用固定 `user_data_dir`
- Windows 下浏览器 profile 文件被进程占用

本次修正：

- 不再使用固定 `workspace/browser-profile`
- 改为每次浏览器任务启动时创建一个独立的临时 profile 目录

当前临时目录位于：

- `F:\AgentBot\workspace\browser-use-user-data-dir-<随机后缀>`

这一步修正后，用户本地已成功启动浏览器。

### 6. 改为可见模式便于人工联调

为了便于验证浏览器是否真实启动，本次将 worker 中的浏览器启动模式改为：

- `headless=False`

这样用户在本地调用浏览器任务接口时，可以直接看到浏览器窗口是否弹出。

## 本次新增的运行行为

### 1. 当前浏览器任务运行方式

当前执行链路为：

```text
POST /api/browser/tasks
  -> BrowserTaskService
  -> LangGraph browser subgraph
  -> BrowserRuntimeManager
  -> browser worker subprocess
  -> browser-use BrowserSession / Tools
```

### 2. 当前浏览器运行使用的 Python 环境

当前有两套 Python 环境：

#### AgentBot 主环境

- `F:\AgentBot\.venv`

负责：

- FastAPI
- LangGraph 子图
- 服务层
- 路由层
- runtime bridge

#### browser worker 环境

- `F:\browser-use\.venv`

负责：

- `browser_use` 真实运行时
- 浏览器启动
- DOM 状态观察
- 浏览器动作执行

### 3. 当前浏览器可执行入口

当前阶段支持显式调用：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/browser/tasks" -ContentType "application/json" -Body '{"task":"Open example.com and tell me the page title","start_url":"https://example.com","max_steps":3}'
```

当前这个入口已经被用户本地实际调用过，并完成了至少一次真实浏览器启动验证。

## 本次验证结果

### 1. 编译与导入验证

已验证：

- `agentbot` 目录 `compileall` 通过
- 浏览器子图 builder 可正常导入
- 浏览器任务服务可正常导入
- `/api/browser/tasks` 路由已成功注册

### 2. 初期失败验证

在本次实现过程中，先后复现并定位了以下问题：

- browser-use 依赖不在 AgentBot 主环境
- `/tmp` 下载目录权限问题
- worker 启动超时
- 浏览器 profile 文件锁

这些问题都已经被纳入当前实现记录，并通过阶段性修正收敛。

### 3. 本地真实启动验证

用户本地实际调用浏览器任务接口后，浏览器已经成功被拉起。

这意味着：

- 浏览器子图本体已经可执行
- runtime bridge 已经可用
- worker 方案在当前本地机器上已经打通

## 当前仍保留的限制

本次执行虽然已经打通第一阶段最关键的链路，但仍然明确保留以下限制。

### 1. 仍然没有接入聊天主图自动路由

当前浏览器能力仍然是显式入口：

- `/api/browser/tasks`

而不是：

- 聊天主图内自动识别浏览器任务并切入浏览器子图

### 2. 仍然是双环境运行方式

当前不是统一依赖方案，而是：

- `AgentBot` 一套环境
- `browser-use` 一套环境

这适合第一阶段快速接入，但后续如果长期维护，仍然需要重新评估依赖统一策略。

### 3. 临时 profile 目录当前不会自动删除

目前每次浏览器任务都会创建独立临时 profile 目录，但：

- 任务结束后不会自动清理

这是本次故意保留的阶段性行为，原因是：

- 先保证链路跑通
- 调试期保留现场更方便

后续可以考虑改成：

- 默认自动清理
- 通过环境变量选择保留

### 4. 仍然没有引入更丰富动作

当前仅支持最小动作集：

- `navigate`
- `click`
- `input`
- `done`

尚未引入：

- `scroll`
- `wait`
- `extract`
- `upload_file`
- `switch_tab`

### 5. 仍然没有做更细粒度 streaming

当前浏览器能力还没有接入专门的浏览器步骤流事件。

也就是说，本次虽然实现了浏览器子图，但尚未把：

- 每一步动作
- 每一步观察
- 每一步执行结果

以更细的 streaming 形式暴露给前端。

### 6. 仍然没有完整测试覆盖

本次以人工联调和最小运行验证为主，还没有为浏览器子图建立完整自动化测试。

## 当前结果如何理解

截至本次执行结束，项目已经具备了：

- 一个真正存在的 LangGraph 浏览器子图
- 一个可显式调用的浏览器任务服务
- 一个连接 `AgentBot` 与 `browser-use` 的运行时桥
- 一个在本地实际成功启动过浏览器的第一阶段能力入口

这意味着当前阶段完成的是：

- **Browser Subgraph Phase 1 的最小可运行闭环**

而不是：

- 完整浏览器 agent
- 聊天主图内完整浏览器调度
- 完整 execution 可视化
- 完整生产级依赖方案

## 后续最自然的下一步

基于当前实际落地结果，后续最自然的下一步是：

1. 把浏览器子图接入聊天主图的显式或半自动路由
2. 增加 `scroll` / `wait` / `extract`
3. 加入更明确的浏览器步骤日志与 streaming
4. 增加临时 profile 自动清理策略
5. 评估是否要把 `browser-use` 依赖逐步纳入 `AgentBot`

## 相关文件

本次实际新增或修改的核心文件包括：

- `agentbot/models/browser.py`
- `agentbot/graph/browser_state.py`
- `agentbot/graph/browser_nodes.py`
- `agentbot/graph/browser_routes.py`
- `agentbot/graph/browser_builder.py`
- `agentbot/services/browser_runtime.py`
- `agentbot/browser_worker.py`
- `agentbot/services/browser.py`
- `agentbot/api/routes/browser.py`
- `agentbot/api/schemas.py`
- `agentbot/api/app.py`
- `docs/exec-plans/active/browser-subgraph-phase-1.md`
