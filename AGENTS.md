# Agent 指南

这个仓库是一个以学习为先、逐步演进为桌面应用的 LangGraph Agent 项目。

## 如何使用这份文件

把这份文件当作仓库入口，而不是完整文档本体。

更详细的项目信息请看：

- `README.md`：快速上手和当前能力概览
- `docs/index.md`：文档总索引
- `docs/product/roadmap.md`：产品方向和后续里程碑
- `docs/architecture/index.md`：系统架构总览
- `docs/exec-plans/active/`：当前正在执行的计划
- `docs/exec-plans/completed/`：已完成阶段归档
- `docs/decisions/`：关键技术决策
- `.agents/skills/`：仓库级 Codex skills

## 当前项目形态

当前项目已经形成四层结构：

1. Electron 桌面壳
2. React 前端
3. FastAPI 本地服务
4. Python Agent 核心

也就是说，它已经不再只是一个 CLI 工具。

## 当前目标

继续把这个项目建设成一个可维护的 LangGraph Agent 工程，具备：

1. 真实模型调用
2. tool routing
3. 本地 conversation persistence
4. execution event logging
5. 可扩展的桌面应用结构
6. 继续向 execution 可视化、streaming 和更完整桌面体验扩展的空间

## 工作规则

- 优先做小步、可运行的改动，不做大范围重构。
- 保持主流程可读、可检查。
- 只有在当前代码真的需要时，才引入新的抽象。
- 代码行为、结构或工作流变化后，要同步更新文档。
- 项目级 skills 统一放在 `./.agents/skills`。
- 涉及 LangGraph / LangChain 相关能力判断时，优先先查可靠资料再做决定。

## 当前边界

这个仓库目前还不包含：

- checkpointer
- long-term memory
- streaming
- execution 可视化面板
- subgraph
- multi-agent orchestration
- 完整自动化测试体系

## 常用命令

安装 Python 依赖：

```powershell
uv sync
```

运行 CLI：

```powershell
.\.venv\Scripts\python.exe main.py
```

启动本地 FastAPI：

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentbot.api.app:app --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
cd ui
npm run dev
```

启动 Electron：

```powershell
cd desktop
npm run dev
```
