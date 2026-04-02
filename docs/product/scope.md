# Product Scope

## 项目定位

AgentBot 是一个以学习为起点、但当前已经具备工程化主链路的本地桌面 Agent 应用。

它不是通用云端平台，也不是浏览器 SaaS，而是：

- 本地桌面宿主
- 本地 FastAPI 服务
- 本地 SQLite 持久化
- LangGraph 驱动的任务执行系统

## 当前范围内

当前明确包含：

- CLI 入口
- Electron 桌面壳
- React 前端
- FastAPI 本地 API
- OpenAI-compatible 模型调用
- LangGraph agent loop
- tool routing
- SQLite transcript / runs / run_steps
- LangGraph SQLite checkpoints
- run-oriented SSE streaming
- 执行区时间线 UI

## 当前范围外

当前明确不包含：

- long-term memory 产品化能力
- multi-agent orchestration
- subgraph 产品化编排
- 云端部署平台
- 团队协作后台
- 完整 tracing SaaS

## 当前工程原则

- 主链路优先
- 数据模型先稳定，再扩功能
- transcript 与 execution 分层
- 前端以 persisted read model 为最终真相
- 文档与代码同步更新
