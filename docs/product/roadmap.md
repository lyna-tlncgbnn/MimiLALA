# Product Roadmap

## 当前阶段

AgentBot 当前已经从“学习型 CLI 项目”演进成一个可运行的本地桌面 Agent 应用。

已经落地的关键阶段包括：

- Python Agent 核心
- FastAPI 本地 API
- React 前端
- Electron 桌面壳
- SQLite 主存储
- run / step 数据模型
- LangGraph checkpoint 集成
- run-oriented streaming chat
- 可展开执行区 UI

## 当前近期方向

当前最自然的下一阶段不是继续做“基础设施迁移”，而是围绕当前主链路做体验增强和稳定性增强。

近期重点建议：

1. 执行区进一步打磨
2. 更完善的 streaming stop / retry / recovery
3. artifacts 体系落地
4. 更系统的调试与 tracing 体验
5. 测试与验收自动化

## 中期方向

中期可继续推进：

1. 更丰富的工具生态
2. 更完善的任务型 UI
3. artifacts 浏览与管理
4. 更强的 checkpoint 调试能力
5. 更规范的 runbook / diagnostics 体系

## 长期探索

当前长期探索方向包括：

1. long-term memory
2. subgraph
3. multi-agent orchestration
4. 更完整的桌面工作台能力

## Roadmap 规则

Roadmap 只表达产品演进方向。

具体实施仍然应落到：

- `docs/exec-plans/active/`
- `docs/exec-plans/completed/`
- `docs/exec-detail/`
