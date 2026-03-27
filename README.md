## AgentBot

AgentBot is a LangGraph learning project that is being built toward a complete agent framework.

### Current phase

The repository is currently in `Phase 2 - Minimal Agent Loop`.

Phase 2 goals:

1. keep the Phase 1 project skeleton stable
2. add the first real tools
3. upgrade the graph from a single model call to a minimal agent loop
4. let the model decide when to call tools and then answer from tool results

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

### Phase 2 boundaries

Phase 2 intentionally does not include:

- session persistence
- memory
- API server
- multi-agent orchestration
