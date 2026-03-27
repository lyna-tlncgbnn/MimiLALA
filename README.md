## AgentBot

AgentBot is a LangGraph learning project that is being built toward a complete agent framework.

### Current phase

The repository is currently in `Phase 1 - Project Skeleton`.

Phase 1 goals:

1. establish the long-term project structure
2. keep `CLI` as the only user entrypoint
3. keep `main.py` as a thin bootstrap only
4. run one real-model LangGraph turn without tools or memory

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

### Run

Pass a prompt directly:

```powershell
.\.venv\Scripts\python.exe main.py "你好"
```

Or run interactively:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Phase 1 boundaries

Phase 1 intentionally does not include:

- tool calling
- session persistence
- memory
- API server
- multi-agent orchestration
