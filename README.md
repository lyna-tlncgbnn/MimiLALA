# AgentBot 🤖

> A learning-first LangGraph agent project that is growing into a complete AI application framework.

AgentBot is a staged LangGraph project built to understand agent systems from the ground up: real model calls, tool routing, short-term conversation history, and local execution logs.

It is intentionally not a giant framework from day one. The project grows one clear capability at a time, while always staying runnable.

## ✨ Current Status

The first major stage of the project is now usable end to end:

- ✅ Real LLM calls through `langchain-openai`
- ✅ LangGraph-based agent loop
- ✅ Tool calling with conditional routing
- ✅ Default persistent conversation
- ✅ Local execution event logging
- ✅ Interactive CLI chat loop

### Currently implemented

AgentBot can already:

- chat with a real OpenAI-compatible model
- decide whether to call a tool
- execute tools and continue the model loop
- remember recent conversation history through local files
- store execution events for each conversation

Current built-in tools:

- `get_current_time`
- `multiply`

## 🧠 Project Structure

```text
agentbot/
  app/          # CLI, runner, console debug rendering
  config/       # config loading
  graph/        # LangGraph builder, nodes, routing, state
  memory/       # conversation + execution persistence
  models/       # LLM factory
  prompts/      # system prompt
  tools/        # tool definitions and registry
main.py         # thin entrypoint
config.json     # local runtime config
workspace/      # local runtime data
plan/           # staged project roadmap
```

## 📦 Installation

### Requirements

- Python `3.11+`
- An OpenAI-compatible model endpoint

### Option 1: `uv` (recommended)

```powershell
uv sync
```

### Option 2: `venv + pip`

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

## ⚙️ Configuration

Create a root `config.json`:

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

Notes:

- `base_url` supports OpenAI-compatible providers such as Alibaba DashScope.
- `debug` only controls whether execution events are echoed to the console.
- Execution events themselves are persisted locally by default.

## 🚀 Run

### Single prompt

```powershell
.\.venv\Scripts\python.exe main.py "现在几点了"
```

### Interactive mode

```powershell
.\.venv\Scripts\python.exe main.py
```

Interactive mode keeps waiting for the next input after each turn.

Exit commands:

- `exit`
- `quit`
- `/exit`
- `/quit`

Replies are printed like this:

```text
You: 13乘以7是多少
AgentBot:
13乘以7等于91。
```

## 🗂️ Local Data

AgentBot stores local runtime data under:

```text
workspace/
  conversations/
    default.jsonl
  executions/
    default.jsonl
```

### `conversations/default.jsonl`

Stores one conversation as:

- one `meta` record on the first line
- followed by `message` records

### `executions/default.jsonl`

Stores:

- the same conversation `meta` shape on the first line
- followed by `event` records

These two files belong to the same conversation because their first-line `conversation_id` is the same.

Typical execution events:

- `conversation_loaded`
- `tools_registered`
- `graph_started`
- `tool_call_emitted`
- `tool_completed`
- `final_answer`
- `run_failed`

## 💬 Example Prompts

```powershell
.\.venv\Scripts\python.exe main.py "现在几点了"
.\.venv\Scripts\python.exe main.py "13乘以7是多少"
.\.venv\Scripts\python.exe main.py "我叫张三"
.\.venv\Scripts\python.exe main.py "我刚刚叫什么名字？"
```

## 🛣️ Roadmap

Completed:

- Phase 1: project skeleton
- Phase 2: minimal agent loop
- Phase 3: conversation persistence
- Phase 4: framework hardening
- Phase 5 (first slice): conversation meta + local execution logs

Next recommended direction:

- richer tools
- stronger persistence / checkpointer support
- API server
- execution log visualization
- long-term memory
- subgraphs / multi-agent

## 🔬 Design Principles

AgentBot follows a few simple principles:

- keep the program runnable at every stage
- prefer clear boundaries over premature abstraction
- add one meaningful agent concept at a time
- use local persistence to make behavior inspectable

## 📌 Current Boundaries

This project still does **not** include:

- API server
- tracing platform integration
- long-term memory
- subgraphs
- multi-agent orchestration

## 📘 Notes

This repository is intentionally educational as well as practical.  
If you open the `plan/` directory, you can see how the project evolved phase by phase.
