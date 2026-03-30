# AgentBot

> 一个以学习为先、逐步成长为完整 AI 应用框架的 LangGraph Agent 项目。

AgentBot 是一个分阶段推进的 LangGraph 项目，用来从底层理解 Agent 系统是如何工作的：真实模型调用、tool routing、短期对话历史，以及本地 execution logs。

它不是一开始就做成“大而全”的框架，而是一次只增加一个清晰能力，并始终保持项目可运行。

## 当前状态

项目的第一大阶段已经可以端到端运行。

- 通过 `langchain-openai` 进行真实 LLM 调用
- 基于 LangGraph 的 agent loop
- 带条件路由的 tool calling
- 默认 conversation persistence
- 本地 execution event logging
- 可交互的 CLI chat loop

### 当前已经实现

AgentBot 目前已经可以：

- 通过 OpenAI-compatible 接口与真实模型对话
- 判断是否需要调用工具
- 执行工具后继续回到模型生成最终结果
- 通过本地文件记住最近对话历史
- 为每次会话保存 execution events

当前内置工具：

- `get_current_time`
- `multiply`

## 项目结构

```text
agentbot/
  app/          # CLI、runner、控制台 debug 输出
  config/       # 配置读取与校验
  graph/        # LangGraph builder、nodes、routes、state
  memory/       # conversation 与 execution 持久化
  models/       # LLM 构造
  prompts/      # system prompt
  tools/        # 工具定义与注册
docs/           # roadmap、architecture、plans、decisions、runbooks
.agents/skills/ # 仓库级 Codex skills
main.py         # 薄入口
config.json     # 本地运行配置
workspace/      # 本地运行数据
```

## 安装

### 环境要求

- Python `3.11+`
- 一个 OpenAI-compatible model endpoint

### 方式一：`uv`（推荐）

```powershell
uv sync
```

### 方式二：`venv + pip`

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
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

- `base_url` 支持 OpenAI-compatible provider，例如 Alibaba DashScope。
- `debug` 只控制是否把 execution events 摘要打印到控制台。
- execution events 本身默认仍会落盘保存。

## 运行

### 单条输入

```powershell
.\.venv\Scripts\python.exe main.py "what time is it?"
```

### 交互模式

```powershell
.\.venv\Scripts\python.exe main.py
```

交互模式下，每轮回复后会继续等待下一条输入。

退出命令：

- `exit`
- `quit`
- `/exit`
- `/quit`

输出示例：

```text
You: what is 13 times 7?
AgentBot:
13 times 7 equals 91.
```

## 本地数据

AgentBot 会把本地运行数据写到：

```text
workspace/
  conversations/
    default.jsonl
  executions/
    default.jsonl
```

### `conversations/default.jsonl`

用于保存一条 conversation：

- 第一行是一个 `meta` record
- 后续每一行是一个 `message` record

### `executions/default.jsonl`

用于保存执行事件：

- 第一行是同一个 conversation 的 `meta` record
- 后续每一行是一个 `event` record

这两个文件属于同一个 conversation，因为它们第一行中的 `conversation_id` 是一致的。

常见 execution events 包括：

- `conversation_loaded`
- `tools_registered`
- `graph_started`
- `tool_call_emitted`
- `tool_completed`
- `final_answer`
- `run_failed`

## 示例输入

```powershell
.\.venv\Scripts\python.exe main.py "what time is it?"
.\.venv\Scripts\python.exe main.py "what is 13 times 7?"
.\.venv\Scripts\python.exe main.py "my name is Tom"
.\.venv\Scripts\python.exe main.py "what is my name?"
```

## Roadmap

已经完成：

- Phase 1：project skeleton
- Phase 2：minimal agent loop
- Phase 3：default conversation persistence
- Phase 4：framework hardening
- Phase 5：conversation meta 和 local execution logs

下一步建议方向：

- richer tools
- 更强的 persistence 与 checkpointer 支持
- API server
- execution log visualization
- long-term memory
- subgraph 与 multi-agent

更完整的结构化项目文档请从 `docs/index.md` 开始看。

## 设计原则

AgentBot 遵循几条简单原则：

- 每个阶段都保持项目可运行
- 优先保持清晰边界，而不是过早抽象
- 一次只增加一个有意义的 Agent 能力
- 优先使用本地可检查的数据，让运行行为可观察

## 当前边界

这个项目目前还不包含：

- API server
- tracing platform integration
- long-term memory
- subgraph
- multi-agent orchestration
- 自动化测试
