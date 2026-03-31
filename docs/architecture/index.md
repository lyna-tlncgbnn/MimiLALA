# 架构总览

AgentBot 当前已经从单一 CLI 学习项目演进成一个带有桌面端、前端、本地 API 和 Python Agent 核心的本地桌面应用架构。

整体分层可以概括为：

```text
Electron Shell
  -> React UI
    -> FastAPI Local API
      -> Agent / Persistence / Tools
```

在聊天主链路上，当前还新增了一条 streaming 路径：

```text
React UI
  -> POST /api/conversations/{id}/messages/stream
    -> FastAPI SSE
      -> streaming_runner
        -> LangGraph graph.stream(...)
```

## 核心模块

- `desktop/`
  Electron 桌面壳，负责窗口管理与本地后端进程管理
- `ui/`
  React 前端，负责会话列表、聊天区、输入区和本地 API 调用
- `agentbot/api/`
  FastAPI 本地服务入口，负责把 Python 能力暴露给前端
- `agentbot/services/`
  conversation 与 chat 的业务语义层
- `agentbot/app/`
  CLI 入口、同步 runner 与 streaming runner
- `agentbot/graph/`
  LangGraph 主循环
- `agentbot/memory/`
  conversation 与 execution persistence
- `agentbot/tools/`
  tools 定义与自动注册

## 关键链路

当前项目存在三条主要运行链路。

### 1. CLI 链路

- 用户通过 CLI 输入
- `runner` 加载配置、history、tools 和 graph
- graph 执行模型与工具循环
- 结果写回 conversation 与 execution storage

### 2. 桌面端非流式链路

- Electron 启动桌面窗口
- Electron 启动本地 FastAPI
- React 前端通过 HTTP 调用本地 API
- API 通过 services 层调用 runner 与 persistence
- 返回 conversation 状态与消息结果给前端

### 3. 桌面端流式聊天链路

- 前端调用 `POST /api/conversations/{conversation_id}/messages/stream`
- FastAPI 以 `text/event-stream` 持续推送事件
- `streaming_runner` 驱动单轮 LangGraph 流式执行
- assistant 文本增量、tool 生命周期事件和最终提交事件持续发回前端
- 前端用 live message 层叠加到持久化消息之上
- 流结束后重新拉取最终 conversation，保证 UI 与持久化结果一致

## 当前阶段特征

当前架构已经具备：

- CLI 与桌面端双入口
- 本地 FastAPI 服务入口
- 多会话 persistence 内核
- 文件相关 tools
- Electron + React 桌面应用基础设施
- 基于 `SSE` 的 streaming chat 主链路

当前仍未包含：

- checkpointer
- execution 可视化面板
- 更复杂的桌面设置系统
- subgraph
- multi-agent orchestration

## 相关文档

- `graph-flow.md`
- `frontend.md`
- `streaming-chat.md`
- `project-structure.md`
- `persistence.md`
- `tools.md`
