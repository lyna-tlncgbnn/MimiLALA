# 架构总览

AgentBot 当前已经从单一 CLI 项目演进为一个本地桌面应用架构。

整体分层可以概括为：

```text
Electron Shell
  -> React UI
    -> FastAPI Local API
      -> Agent / Persistence / Tools
```

## 核心模块

- `desktop/`
  Electron 桌面壳，负责窗口管理与本地后端进程管理
- `ui/`
  React 前端，负责界面渲染、用户交互和本地 API 调用
- `agentbot/api/`
  FastAPI 本地服务入口，负责把 Python 能力暴露给前端
- `agentbot/services/`
  conversation 与 chat 的业务语义层
- `agentbot/app/`
  CLI 入口与运行调度
- `agentbot/graph/`
  LangGraph 主循环
- `agentbot/memory/`
  conversation 与 execution persistence
- `agentbot/tools/`
  工具定义与自动注册

## 关键流程

当前项目存在两条主要运行链路。

### 1. CLI 链路

- 用户通过 CLI 输入
- `runner` 加载配置、history、tools 和 graph
- graph 执行模型与工具
- 结果写回 conversation 与 execution storage

### 2. 桌面端链路

- Electron 启动桌面窗口
- Electron 启动本地 FastAPI
- React 前端通过 HTTP 调用本地 API
- API 通过 services 层调用 runner 与 persistence
- 返回 conversation 状态与消息结果给前端

## 当前阶段特征

当前架构已经具备：

- CLI 与桌面端双入口
- 本地 FastAPI 服务入口
- 多会话 persistence 内核
- 文件相关 tools
- Electron + React 桌面应用基础设施

当前仍未包含：

- checkpointer
- streaming
- execution 可视化面板
- 复杂设置系统
- subgraph
- multi-agent orchestration

## 相关文档

- `graph-flow.md`
- `frontend.md`
- `project-structure.md`
- `persistence.md`
- `tools.md`
