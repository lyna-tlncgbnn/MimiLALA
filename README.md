# AgentBot

> 一个以学习为先、逐步成长为桌面 AI 应用的 LangGraph Agent 项目。

AgentBot 最初是一个分阶段推进的 LangGraph 学习项目，用来从底层理解 Agent 系统是如何工作的：真实模型调用、tool routing、短期对话历史，以及本地 execution logs。

目前它已经不再只是一个 CLI demo，而是演进为一个带有本地 API、React 前端和 Electron 桌面壳的桌面应用雏形。

## 当前状态

项目目前已经具备以下能力：

- 基于 `langchain-openai` 的真实 LLM 调用
- 基于 LangGraph 的 agent loop
- 带条件路由的 tool calling
- 本地 conversation persistence
- 本地 execution event logging
- 多会话 persistence 内核
- FastAPI 本地服务入口
- React 前端工程骨架
- Electron 桌面壳

### 当前已经实现

当前项目已经可以：

- 通过 OpenAI-compatible 接口与真实模型对话
- 判断是否需要调用工具
- 执行工具并继续模型循环
- 保存 conversation 历史与 execution events
- 在 persistence 内核中支持多个 conversation
- 通过本地 API 完成 conversation CRUD
- 在桌面端展示会话列表和聊天界面

当前内置工具包括：

- `get_current_time`
- `multiply`
- `list_directory`
- `read_file`
- `write_file`
- `read_pdf`
- `read_docx`

## 项目结构

```text
desktop/         # Electron 桌面壳
ui/              # React 前端
agentbot/        # Python 后端核心
docs/            # roadmap、architecture、plans、decisions、runbooks
.agents/skills/  # 仓库级 Codex skills
main.py          # CLI 薄入口
config.json      # 本地运行配置
workspace/       # 本地运行数据
```

其中：

- `desktop/` 负责桌面窗口与本地后端进程管理
- `ui/` 负责前端页面与交互
- `agentbot/` 负责 Agent、API、persistence、services 和 tools

## 安装

### 环境要求

- Python `3.11+`
- Node.js 与 npm
- 一个 OpenAI-compatible model endpoint

### Python 依赖

推荐使用 `uv`：

```powershell
uv sync
```

或者：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

### 前端依赖

```powershell
cd ui
npm install
```

### Electron 依赖

```powershell
cd desktop
npm install
```

## 配置

在仓库根目录创建 `config.json`：

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "your-model-name",
    "temperature": 0.1
  },
  "debug": false
}
```

说明：

- `base_url` 支持 OpenAI-compatible provider，例如 Alibaba DashScope
- `debug` 只控制是否把 execution 摘要打印到控制台
- execution events 本身默认仍会落盘保存

## 运行方式

### 运行 CLI

```powershell
.\.venv\Scripts\python.exe main.py
```

### 单条输入

```powershell
.\.venv\Scripts\python.exe main.py "what time is it?"
```

### 启动本地 FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentbot.api.app:app --host 127.0.0.1 --port 8000
```

### 启动前端

```powershell
cd ui
npm run dev
```

### 启动 Electron 桌面端

```powershell
cd desktop
npm run dev
```

## 本地数据

当前项目的本地运行数据位于：

```text
workspace/
  conversations/
    default.json
    <conversation_id>.jsonl
  executions/
    <conversation_id>.jsonl
```

其中：

- `conversations/<conversation_id>.jsonl` 保存某个会话的消息历史
- `executions/<conversation_id>.jsonl` 保存同一会话的 execution events
- `conversations/default.json` 记录当前 CLI 默认会话指向的 `conversation_id`

## 当前 Roadmap

已经完成：

- Phase 1：project skeleton
- Phase 2：minimal agent loop
- Phase 3：default conversation persistence
- Phase 4：framework hardening
- Phase 5：conversation meta 和 local execution logs
- richer tools
- multi-conversation persistence
- desktop app foundation

下一步建议方向：

- execution log visualization
- streaming 交互体验
- 更完整的桌面设置与调试能力
- long-term memory
- subgraph 或 multi-agent 实验

更完整的结构化项目文档请从 `docs/index.md` 开始看。

## 设计原则

AgentBot 遵循几条简单原则：

- 每个阶段都保持项目可运行
- 优先保持清晰边界，而不是过早抽象
- 一次只增加一个有意义的 Agent 能力
- 优先使用本地可检查的数据，让运行行为可观察

## 当前边界

这个项目当前仍然不包含：

- checkpointer
- long-term memory
- streaming
- execution 可视化面板
- subgraph
- multi-agent orchestration
- 完整自动化测试体系
