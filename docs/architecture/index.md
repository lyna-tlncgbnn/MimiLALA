# 架构总览

当前 AgentBot 是一个本地桌面 Agent 应用，主结构如下：

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

- 主存储已经是 SQLite，而不是 JSONL
- LangGraph 已接入 SQLite checkpointer
- 聊天主链路已经是 run-oriented，而不是扁平 message-centric
- 前端当前按 transcript、active run、historical runs 分离渲染
- tools 不再作为普通聊天气泡渲染

## 当前核心模块

- `desktop/`
  Electron 窗口与本地进程壳层
- `ui/`
  React 前端和本地交互界面
- `agentbot/api/`
  FastAPI 入口与 HTTP/SSE 路由
- `agentbot/services/`
  conversation 与 chat 服务层
- `agentbot/app/`
  CLI、同步 runner、流式 runner
- `agentbot/graph/`
  LangGraph 构建与 checkpoint 接入
- `agentbot/storage/`
  SQLite schema、repository、shadow runtime
- `agentbot/tools/`
  tool 定义与注册

## 推荐阅读顺序

1. [runtime-architecture.md](/F:/AgentBot/docs/architecture/runtime-architecture.md)
   运行时主模型与整体设计
2. [database.md](/F:/AgentBot/docs/architecture/database.md)
   SQLite 数据模型与持久化边界
3. [runtime-flow.md](/F:/AgentBot/docs/architecture/runtime-flow.md)
   从前端到 LangGraph 再到持久化的主链路
4. [streaming-chat.md](/F:/AgentBot/docs/architecture/streaming-chat.md)
   SSE 事件、active run 与前端流式状态
5. [frontend.md](/F:/AgentBot/docs/architecture/frontend.md)
   前端读取模型与界面分层
6. [graph-flow.md](/F:/AgentBot/docs/architecture/graph-flow.md)
   LangGraph 图执行结构
7. [tools.md](/F:/AgentBot/docs/architecture/tools.md)
   tools 层设计
8. [project-structure.md](/F:/AgentBot/docs/architecture/project-structure.md)
   目录结构与模块职责

## 兼容说明

旧文件 [agent-runtime-redesign.md](/F:/AgentBot/docs/architecture/agent-runtime-redesign.md) 仍保留为历史入口兼容说明，但当前正式技术说明应以 `runtime-architecture.md` 为准。
