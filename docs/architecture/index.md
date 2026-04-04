# 架构总览

当前 AgentBot 是一个本地桌面 Agent 应用，主链路如下：

```text
Electron Shell
  -> React UI
    -> FastAPI Local API
      -> ChatService
        -> runner / streaming_runner
          -> LangGraph
            -> LLM + Tools + SQLite + Checkpoints
```

## 当前架构事实

- 主存储是 SQLite
- LangGraph 已接入 SQLite checkpointer
- 聊天主链路是 run-oriented，而不是早期的 message-centric demo
- 前端按 `transcript`、`active run`、`historical runs` 分层读取
- 浏览器能力已经演进成专门的 LangGraph 子图
- 浏览器 runtime 正在逐步对齐 `browser-use` 的 session / event bus / watchdog 结构

## 推荐阅读顺序

1. [runtime-architecture.md](/F:/AgentBot/docs/architecture/runtime-architecture.md)
   运行时主模型与整体边界
2. [runtime-flow.md](/F:/AgentBot/docs/architecture/runtime-flow.md)
   从前端到 LangGraph 再到持久化的主链路
3. [graph-flow.md](/F:/AgentBot/docs/architecture/graph-flow.md)
   主图与浏览器子图的真实执行结构
4. [browser-observation-pipeline.md](/F:/AgentBot/docs/architecture/browser-observation-pipeline.md)
   浏览器 observation 的 raw capture -> serialization 两段式
5. [browser-planner-state.md](/F:/AgentBot/docs/architecture/browser-planner-state.md)
   浏览器 planner state
6. [browser-runtime.md](/F:/AgentBot/docs/architecture/browser-runtime.md)
   浏览器 runtime、event bus、watchdogs、DOMWatchdog 与动作执行中间层
7. [browser-use-migration-todo.md](/F:/AgentBot/docs/architecture/browser-use-migration-todo.md)
   继续向 `browser-use` 靠拢的迁移清单
8. [database.md](/F:/AgentBot/docs/architecture/database.md)
   SQLite 数据模型与持久化边界
9. [project-structure.md](/F:/AgentBot/docs/architecture/project-structure.md)
   目录结构与模块职责

## 当前阶段重点

当前浏览器部分的重点已经从“能不能打开页面”转成：

- observation 是否足够稳定
- planner 是否有持续状态
- runtime 是否能吸收下载、popup、page close 等副作用
- DOM 状态是否已经归入 runtime 管理

当前做法是：

- 保持浏览器 agent 继续作为 LangGraph 子图
- 逐步把子图下面的 runtime 内核对齐到 `browser-use` 的结构
- 保留本项目自己的 transcript / runs / run_steps / checkpoints 主链路
- 把 DOM/watchdog、下载/watchdog、popup/watchdog、lifecycle/watchdog 等逐步并进 runtime 总线
