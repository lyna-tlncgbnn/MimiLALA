## AgentBot

AgentBot is a LangGraph learning project that is being built toward a complete agent framework.

### Current phase

The repository is now in `Phase 5 - Mature Project Expansion`.

The first Phase 5 slice focuses on two local data foundations:

1. conversation files with file-level `meta`
2. execution logs stored alongside each conversation

### Config

Create a root `config.json` and fill in your model settings:

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "gpt-4.1-mini",
    "temperature": 0.1
  },
  "debug": false
}
```

If you use an OpenAI-compatible provider such as Alibaba, set its compatible `base_url`
and the actual model name it expects.

`debug` now only controls whether execution events are also echoed to the console.
Execution events themselves are persisted locally by default.

### Current capabilities

The project currently supports:

- real model calls through LangGraph
- tool calling with `get_current_time` and `multiply`
- a default persistent conversation
- local execution event logging

### Workspace

The project stores local runtime data under:

```text
workspace/
  conversations/
    default.jsonl
  executions/
    default.jsonl
```

`conversations/default.jsonl` stores one conversation as:

- one `meta` record on the first line
- followed by `message` records

`executions/default.jsonl` stores:

- the same `meta` record shape on the first line
- followed by `event` records

Both files belong to the same conversation because their first-line `conversation_id` is identical.

### Execution Logging

Execution events are now written locally by default.

Typical event types include:

- `conversation_loaded`
- `tools_registered`
- `graph_started`
- `tool_call_emitted`
- `tool_completed`
- `final_answer`
- `run_failed`

### Run

Pass a prompt directly:

```powershell
.\.venv\Scripts\python.exe main.py "你好"
```

Or run interactively:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Example prompts

```powershell
.\.venv\Scripts\python.exe main.py "现在几点了"
.\.venv\Scripts\python.exe main.py "13乘以7是多少"
```

### Conversation example

Run these two commands one after another:

```powershell
.\.venv\Scripts\python.exe main.py "我叫张三"
.\.venv\Scripts\python.exe main.py "我刚刚叫什么名字？"
```

Then inspect:

- `workspace/conversations/default.jsonl`
- `workspace/executions/default.jsonl`

### Current boundaries

The project still does not include:

- API server
- tracing platform integration
- long-term memory
- subgraphs
- multi-agent orchestration

### Next step

The next recommended Phase 5 slice is richer tools on top of the new local data model.
