# Agent 指南

这个仓库是一个以学习为先、逐步演进的 LangGraph Agent 项目。

## 如何使用这份文件

把这份文件当作仓库入口，而不是完整文档本体。

更详细的项目信息请看：

- `README.md`：快速上手和当前能力概览
- `docs/index.md`：文档总索引
- `docs/product/roadmap.md`：产品方向和后续里程碑
- `docs/architecture/index.md`：系统架构与数据流
- `docs/exec-plans/active/`：当前正在执行的计划
- `docs/exec-plans/completed/`：已完成阶段归档
- `docs/decisions/`：关键技术决策
- `.agents/skills/`：仓库级 Codex skills

## 当前目标

把这个项目逐步建设成一个可维护的 LangGraph Agent 工程，具备：

1. 真实模型调用
2. tool routing
3. 本地 conversation persistence
4. execution event logging
5. 继续向 richer tools、checkpointer 和更多入口扩展的空间

## 工作规则

- 优先做小步、可运行的改动，不做大范围重构。
- 保持主流程可读、可检查。
- 只有在当前代码真的需要时，才引入新的抽象。
- 代码行为、结构或工作流变化后，要同步更新文档。
- 项目级 skills 统一放在 `./.agents/skills`。
- 跟langGraph 和 langchain相关的必须先通过mcp查资料以后再做决定。

## 当前边界

这个仓库目前还不包含：

- API server
- long-term memory
- checkpointer
- tracing platform integration
- subgraph
- multi-agent orchestration
- 自动化测试

## 常用命令

安装依赖：

```powershell
uv sync
```

运行 CLI：

```powershell
.\.venv\Scripts\python.exe main.py
```

运行单条输入：

```powershell
.\.venv\Scripts\python.exe main.py "what time is it?"
```
