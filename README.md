## AgentBot

AgentBot is a LangGraph learning project that is being built toward a complete agent framework.

### Current phase

The repository has completed `Phase 3 - Session And Config`.

Phase 3 goals:

1. keep the Phase 2 agent loop stable
2. add a default short-term session
3. persist local conversation history under `workspace/`
4. let the CLI continue a previous conversation automatically

### Config

Create a root `config.json` and fill in your model settings:

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "gpt-4.1-mini",
    "temperature": 0.1
  }
}
```

If you use an OpenAI-compatible provider such as Alibaba, set its compatible `base_url`
and the actual model name it expects.

### Phase 2 capabilities

The project now includes two tools:

- `get_current_time`
- `multiply`

### Workspace

The project now stores local runtime data under:

```text
workspace/
  sessions/
    default.jsonl
```

The CLI automatically loads and saves the default session history from this file.

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

### Phase 3 boundaries

Phase 3 intentionally does not include:

- memory
- API server
- multi-agent orchestration

### Next step

The next planned stage is `Phase 4 - Framework Hardening`.
