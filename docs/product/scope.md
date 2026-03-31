# 产品范围

## 项目定位

AgentBot 是一个以学习为先、同时保持实用性的 LangGraph 项目。

它的目标不是一开始就做成复杂框架，而是通过渐进方式理解并构建一个真实可运行的 Agent 系统，并逐步把它演进成桌面应用。

## 当前范围内

- CLI 交互入口
- Electron 桌面应用入口
- React 前端界面
- FastAPI 本地 API
- 通过 OpenAI-compatible chat API 进行真实模型调用
- 基于 LangGraph 的 agent loop
- tool calling 与 tool execution
- 本地 conversation persistence
- 本地 execution event logging
- 多会话 persistence 内核
- 桌面端 streaming chat
- 可以继续扩展而不必重写的代码结构

## 当前阶段暂不包含

- long-term memory
- checkpointer integration
- execution 可视化面板
- tracing platform integration
- subgraph
- multi-agent orchestration
- 浏览器版独立 Web 产品
- 生产部署相关能力

## 工程原则

- 每个阶段都保持项目可运行。
- 优先保持清晰模块边界，而不是过早抽象。
- 一次只增加一个有意义的新能力。
- 优先使用可检查的本地数据，而不是隐藏的运行时状态。
