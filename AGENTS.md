# Agent 指南

这份文件是仓库入口，不是完整设计文档。

如果你要理解项目现状，优先看：

- `README.md`
- `docs/index.md`
- `docs/architecture/index.md`
- `docs/product/scope.md`
- `docs/runbooks/local-dev.md`

## 当前项目形态

当前仓库已经形成完整本地应用结构：

1. Electron 桌面壳
2. React 前端
3. FastAPI 本地 API
4. Python Agent Runtime
5. SQLite 主存储
6. LangGraph SQLite checkpoint

聊天主链路已经不是早期的 message-centric demo，而是：

- conversation transcript
- run
- run_steps
- checkpoints

这几层分离的运行模型。

## 当前主链路

```text
Electron
  -> React UI
    -> FastAPI
      -> ChatService
        -> runner / streaming_runner
          -> LangGraph
            -> LLM + Tools + SQLite + Checkpoints
```

前端当前主读取模型：

- transcript：用户消息 + 最终回答
- active run：当前执行态
- historical runs：历史任务摘要与执行步骤

## 当前主要目录

- `desktop/`
  Electron 壳层
- `ui/`
  React 前端
- `agentbot/api/`
  FastAPI 入口、schema、serializer、routes
- `agentbot/app/`
  CLI、同步 runner、流式 runner
- `agentbot/graph/`
  LangGraph builder、nodes、routes、checkpoint helpers
- `agentbot/services/`
  conversation / chat 服务层
- `agentbot/storage/`
  SQLite schema、repository、runtime shadow 持久化
- `agentbot/tools/`
  tool 定义与注册
- `docs/`
  产品、架构、runbook、执行记录

## 当前工作规则

- 优先保持主链路可运行。
- 不要随意加兜底代码。
- 修改行为、结构或流程后，必须同步更新文档。
- 先看清当前代码再改，不按旧文档盲改。
- 结构性结论优先以 `docs/architecture/` 为准。
- 执行记录写入 `docs/exec-detail/`，不要把实施过程混进技术说明文档。
- 项目级 skills 统一放在 `./.agents/skills`。

## 当前事实边界

当前已经具备：

- SQLite transcript / runs / run_steps
- LangGraph SQLite checkpointer
- run-oriented SSE stream
- 桌面端执行过程折叠时间线

当前还没有完整具备：

- 长期记忆
- approval / interrupt UI
- 多 agent 编排
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

启动 FastAPI：

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
