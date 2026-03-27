## AgentBot

AgentBot is a LangGraph learning project that is being built toward a complete agent framework.

### Current phase

The repository has completed `Phase 4 - Framework Hardening`.

Phase 4 goals:

1. keep the Phase 3 agent loop stable
2. keep tool registration boundaries explicit
3. make prompt and error boundaries easier to maintain
4. add a console debug mode for learning and troubleshooting

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

Set `debug` to `true` when you want to see the agent's execution steps in the console.

### Current capabilities

The project now includes two tools:

- `get_current_time`
- `multiply`

### Workspace

The project stores local runtime data under:

```text
workspace/
  sessions/
    default.jsonl
```

The CLI automatically loads and saves the default session history from this file.

### Debug mode

When `debug` is `true`, the console shows a concise execution trace, including:

- how many session messages were loaded
- which tools are registered
- whether the model emitted a tool call
- which tool returned what
- what the final answer was

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

### Session example

Run these two commands one after another:

```powershell
.\.venv\Scripts\python.exe main.py "我叫张三"
.\.venv\Scripts\python.exe main.py "我刚刚叫什么名字？"
```

### Phase 4 boundaries

Phase 4 intentionally does not include:

- memory
- API server
- multi-agent orchestration
- tracing platforms
- checkpointing

### Next step

The next planned stage is `Phase 5 - Mature Project Expansion`.
