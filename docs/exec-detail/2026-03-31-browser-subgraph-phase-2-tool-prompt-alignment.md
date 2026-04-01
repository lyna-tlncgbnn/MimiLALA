# Browser Subgraph Phase 2: Tool + Prompt Alignment

## Background

After `Browser Subgraph Phase 1`, the project already had:

- a runnable LangGraph browser subgraph
- a `browser-use` worker bridge
- a visible local browser session
- an explicit `/api/browser/tasks` entrypoint

The next gap was alignment:

- the planner prompt still only reflected the minimal Phase 1 action set
- the browser runtime only exposed part of the useful `browser-use` action surface
- the prompt and executor were not yet speaking the same action language

This iteration focused on that alignment first, before wiring the browser subgraph into the main chat graph.

## Goal

Make the browser planner and the browser executor use a more consistent `browser-use`-style contract.

Concretely, this meant:

- expand the action set beyond `navigate / click / input / done`
- migrate key low-cost observation tools from `browser-use`
- tighten the browser subgraph prompt so it reflects the actual action surface
- keep LangGraph as the only orchestration layer

## What Was Implemented

### 1. Expanded browser action schema

Updated [browser.py](/F:/AgentBot/agentbot/models/browser.py) so the planner can now emit:

- `navigate`
- `click`
- `input`
- `scroll`
- `wait`
- `extract`
- `search_page`
- `find_elements`
- `done`

The action model now validates the required fields for each action type, so the planner is structurally constrained before execution.

### 2. Added browser-use style prompt layer

Added [browser_subgraph.py](/F:/AgentBot/agentbot/prompts/browser_subgraph.py).

This prompt is not a raw copy of `browser-use`'s full system prompt, because this project does not reuse its full agent loop. Instead, it selectively migrates the parts that are still correct in this architecture:

- same-language response behavior
- indexed-element discipline
- prefer page state as ground truth
- use `wait` for unstable/loading pages
- prefer `search_page` and `find_elements` before expensive extraction
- use `extract` only when cheaper page queries are insufficient
- avoid repeated failed actions
- handle popups and overlays early

This keeps the prompt behavior close to `browser-use`, while still fitting a one-action-per-step LangGraph subgraph.

### 3. Extended runtime bridge payloads

Updated [browser_runtime.py](/F:/AgentBot/agentbot/services/browser_runtime.py) so the LangGraph side can send the additional action parameters required by the expanded action schema.

The runtime bridge now forwards:

- `pages`
- `seconds`
- `query`
- `pattern`
- `selector`
- `attributes`
- `include_text`
- `extract_links`
- `start_from_char`

### 4. Extended browser worker execution surface

Updated [browser_worker.py](/F:/AgentBot/agentbot/browser_worker.py) to execute more `browser-use` tools directly.

The worker now supports:

- `scroll`
- `wait`
- `extract`
- `search_page`
- `find_elements`

The implementation continues to use `browser-use` as the execution/runtime layer, not as the orchestration layer.

### 5. Added extraction LLM bridge

Updated [browser.py](/F:/AgentBot/agentbot/services/browser.py) and [browser_runtime.py](/F:/AgentBot/agentbot/services/browser_runtime.py) so the worker receives the current OpenAI-compatible config from local settings.

This allows the worker to create a `browser-use` extraction model for the `extract` action when:

- `api_key` is available
- `base_url` is available or omitted
- `model` is configured

### 6. Improved worker observation quality

Updated [browser_worker.py](/F:/AgentBot/agentbot/browser_worker.py) to include recent browser events during observation.

This makes the subgraph prompt more useful because the planner can now see:

- recent page transitions
- recent runtime-level browser signals
- more context after actions such as click or input

### 7. Improved temporary resource cleanup

Updated [browser_worker.py](/F:/AgentBot/agentbot/browser_worker.py) to clean more temporary state on close and on failure.

Cleanup now covers:

- temporary browser profile directory
- temporary browser-use filesystem directory
- started browser session on exception

Profile retention still supports:

- `AGENTBOT_KEEP_BROWSER_PROFILE=1`

This keeps debugging possible without making the default path noisy.

## Reference Source

This iteration referenced `browser-use` directly, especially:

- `F:\browser-use\browser_use\agent\system_prompts\system_prompt.md`
- `F:\browser-use\browser_use\agent\system_prompts\system_prompt_browser_use.md`
- `F:\browser-use\browser_use\tools\service.py`
- `F:\browser-use\browser_use\tools\views.py`

The project did **not** import or reuse:

- `browser_use.agent.service.Agent`
- `browser_use`'s own planner loop
- `browser_use`'s message-manager-driven orchestration

That boundary remains intentional:

- LangGraph handles state transitions and subgraph routing
- `browser-use` handles browser execution primitives and DOM tooling

## Validation

This iteration was validated with:

- Python compile check:
  - `.\.venv\Scripts\python.exe -m compileall agentbot`
- graph construction check:
  - compile browser graph with project settings and model

The static validation passed.

## Current Limitations

This iteration did **not** yet complete the full Phase 2 plan.

Still pending:

- route the browser subgraph into the main chat graph
- expose browser step events through the chat SSE path
- add higher-level browser routing in chat orchestration
- perform a broader set of real browser task validation scenarios

## Practical Outcome

At the end of this iteration, the browser subgraph is still an explicit entrypoint, but it is meaningfully closer to `browser-use` semantics:

- the prompt reflects the real action surface more accurately
- the executor now supports richer observation and extraction tools
- the worker has better runtime cleanup behavior

This is the right base for the next step:

- connecting the browser subgraph into the main chat flow without having to redesign the planner/executor contract again.
