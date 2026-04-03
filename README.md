# AgentBot

一个已经完成桌面化主链路的 LangGraph Agent 工程项目。

当前项目不再是早期的 CLI demo，而是一个完整的本地应用栈：

- Electron 桌面壳
- React 前端
- FastAPI 本地 API
- Python Agent Runtime
- SQLite 应用数据存储
- LangGraph SQLite Checkpoint

## 当前项目定位

这个仓库的目标不是做“最小可运行玩具”，而是把一个可运行的 LangGraph Agent 逐步整理成可维护、可扩展、可观察的工程化项目。

当前已经具备：

- 真实模型调用
- LangGraph agent loop
- 条件化 tool routing
- 本地多会话
- run / step 数据模型
- SQLite 主存储
- LangGraph checkpoint 持久化
- 基于 SSE 的流式聊天
- 桌面端会话与执行过程展示

## 当前主链路

当前聊天主路径是：

```text
Electron
  -> React UI
    -> FastAPI Local API
      -> ChatService
        -> runner / streaming_runner
          -> LangGraph
            -> LLM + Tools + SQLite + Checkpoints
```

其中：

- transcript 面向用户可见消息
- run 面向一次任务执行
- run_steps 面向执行过程展示
- checkpoints 面向 LangGraph durable execution

## 当前能力

### Runtime

- 基于 `langchain-openai` 的 OpenAI-compatible 模型接入
- LangGraph `chatbot -> tools -> chatbot` 主循环
- SQLite transcript / runs / run_steps / artifacts 表
- LangGraph SQLite checkpointer
- 同步执行与流式执行两套入口

### API

- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `PATCH /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs/stream`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/steps`

兼容别名仍然存在：

- `POST /api/conversations/{conversation_id}/messages`
- `POST /api/conversations/{conversation_id}/messages/stream`

但当前主路径已经是 run-oriented。

### 前端

- 多会话侧边栏
- transcript + active run + historical runs 分离渲染
- 执行过程折叠时间线
- 最终回答 Markdown 渲染
- 本地桌面窗口集成

### 内置 Tools

- `get_current_time`
- `multiply`
- `list_directory`
- `glob_files`
- `search_in_files`
- `read_file`
- `read_file_range`
- `write_file`
- `replace_in_file`
- `append_file`
- `run_command`
- `read_pdf`
- `read_docx`
- `read_xlsx`
- `read_pptx`
- `batch_read_documents`
- `web_search`
- `fetch_url`

## 项目结构

```text
desktop/         Electron 桌面壳
ui/              React 前端
agentbot/        Python 后端与 Agent Runtime
docs/            产品、架构、runbook、执行记录
.agents/skills/  仓库级 Codex skills
workspace/       本地运行数据
main.py          CLI 入口
config.json      本地运行配置
```

## 本地存储

当前主存储已经是 SQLite：

- `workspace/agent_runtime.db`
- `workspace/langgraph_checkpoints.db`

其中：

- `agent_runtime.db` 保存 conversations / messages / runs / run_steps / artifacts
- `langgraph_checkpoints.db` 保存 LangGraph thread checkpoints

仓库里仍保留了早期 JSONL 模块用于迁移兼容和历史参考，但它们不再是当前聊天主链路的 source of truth。

## 配置

运行配置来自仓库根目录的 `config.json`：

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "gpt-4.1-mini",
    "temperature": 0.1,
    "max_tokens": 4096,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "request_timeout_seconds": 120,
    "max_retries": 2,
    "reasoning_effort": null,
    "reasoning": null,
    "extra_body": {},
    "default_headers": {}
  },
  "search": {
    "provider": "tavily",
    "api_key": "your_search_api_key",
    "max_results": 5,
    "timeout_seconds": 12
  },
  "command": {
    "enabled": true,
    "default_timeout_seconds": 20,
    "max_timeout_seconds": 60,
    "max_output_chars": 12000,
    "allowed_programs": [
      ".venv\\Scripts\\python.exe",
      "python",
      "uv",
      "npm"
    ],
    "blocked_patterns": [
      "del ",
      "remove-item",
      "rmdir",
      ">",
      "|",
      "&&"
    ]
  },
  "browser": {
    "headless": true,
    "close_on_finish": true,
    "max_actions": 12
  },
  "debug": false
}
```

说明：

- `llm.api_key` 必填
- `llm.base_url` 可选，默认走 OpenAI 官方地址
- `llm.model` 默认 `gpt-4.1-mini`
- `llm.temperature` 必须是数字
- `llm.max_tokens` 可选，控制最大输出长度
- `llm.top_p` / `llm.frequency_penalty` / `llm.presence_penalty` 为常见采样参数
- `llm.request_timeout_seconds` / `llm.max_retries` 控制请求超时与重试
- `llm.reasoning_effort` / `llm.reasoning` 用于支持 reasoning 能力的兼容模型
- `llm.extra_body` / `llm.default_headers` 用于 provider-specific 参数透传，例如部分 OpenAI-compatible 服务的 thinking 开关
- `search.*` 用于应用级联网搜索配置
- `command.*` 用于受限本地命令执行配置
- `browser.headless` 控制浏览器子图使用后台浏览器还是可见浏览器窗口
- `browser.close_on_finish` 控制浏览器任务结束后是否自动关闭浏览器窗口
- `browser.max_actions` 控制浏览器子图单次运行允许的最大动作步数，默认 `12`
- `debug` 控制控制台调试输出

实现见：

- [settings.py](/F:/AgentBot/agentbot/config/settings.py)

## 安装

### Python

推荐：

```powershell
uv sync
```

### 前端

```powershell
cd ui
npm install
```

### Electron

```powershell
cd desktop
npm install
```

## 运行

### CLI

```powershell
.\.venv\Scripts\python.exe main.py
```

### 单条 CLI 输入

```powershell
.\.venv\Scripts\python.exe main.py "你好"
```

### FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentbot.api.app:app --host 127.0.0.1 --port 8000
```

### 前端开发

```powershell
cd ui
npm run dev
```

### Electron 开发

```powershell
cd desktop
npm run dev
```

## 当前文档入口

从这些文档开始最合适：

- [docs/index.md](/F:/AgentBot/docs/index.md)：文档总入口
- [docs/architecture/index.md](/F:/AgentBot/docs/architecture/index.md)：技术架构总览
- [docs/product/scope.md](/F:/AgentBot/docs/product/scope.md)：当前产品范围
- [docs/product/roadmap.md](/F:/AgentBot/docs/product/roadmap.md)：后续方向
- [docs/runbooks/local-dev.md](/F:/AgentBot/docs/runbooks/local-dev.md)：本地开发和运行

## 当前边界

当前项目还没有完整实现：

- 长期记忆
- stop / resume / approval UI
- subgraph / multi-agent orchestration
- 完整自动化测试体系
- 独立 tracing 平台接入

但当前工程结构已经支持继续往这些方向演进，而不需要重写主链路。
