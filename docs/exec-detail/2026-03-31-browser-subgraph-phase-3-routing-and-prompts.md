# Browser Subgraph Phase 3: Routing + Prompt Foundation

## Background

At the end of Phase 2, browser mode in chat was already usable, but it still relied on:

- explicit browser prefixes such as `/browser`
- browser planner prompts embedded primarily in Python code

That meant two important Phase 3 goals were still open:

- move from explicit-only browser routing toward model-guided routing
- make browser prompt management file-based and easier to evolve

## Goal

This iteration focused on the first two foundational parts of Phase 3:

1. add a model-guided routing decision layer to the main graph
2. move browser prompt source-of-truth into a dedicated prompt directory

This was intentionally done before further browser action expansion, because routing and prompt structure affect all later browser-agent work.

## What Was Implemented

### 1. Added a main graph routing decision model

Added [routing.py](/F:/AgentBot/agentbot/models/routing.py).

The project now has a small structured routing schema:

- `route`
- `reason`

Allowed route values are:

- `chat`
- `browser`

This keeps routing explainable and constrained.

### 2. Extended main graph state for routing metadata

Updated [state.py](/F:/AgentBot/agentbot/graph/state.py).

The main chat graph no longer depends purely on raw `MessagesState`. It now uses:

- `AgentGraphState`

which keeps the existing message list while also allowing:

- `routing_decision`

This makes later routing logging and inspection cleaner.

### 3. Inserted a router node into the main graph

Updated [builder.py](/F:/AgentBot/agentbot/graph/builder.py).

The main graph now follows this shape:

- `START -> entry`
- explicit browser prefix -> `browser`
- otherwise -> `route`
- `route` -> `chatbot` or `browser`

This preserves explicit browser override while enabling model-guided routing for ordinary messages.

### 4. Added model-guided routing logic

Updated [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py) and [routes.py](/F:/AgentBot/agentbot/graph/routes.py).

There is now a dedicated router node that:

- reads the latest user message
- invokes the model with structured output
- emits a constrained routing decision

At the same time, explicit browser prefixes are still supported as hard override:

- `/browser`
- `browser:`
- `浏览器:`
- `使用浏览器:`

This preserves debuggability and manual control.

### 5. Added a dedicated browser prompt directory

Added:

- [__init__.py](/F:/AgentBot/agentbot/prompts/browser/__init__.py)
- [loader.py](/F:/AgentBot/agentbot/prompts/browser/loader.py)
- [router_prompt.md](/F:/AgentBot/agentbot/prompts/browser/router_prompt.md)
- [system_prompt_no_thinking.md](/F:/AgentBot/agentbot/prompts/browser/system_prompt_no_thinking.md)
- [system_prompt_browser_use_no_thinking.md](/F:/AgentBot/agentbot/prompts/browser/system_prompt_browser_use_no_thinking.md)

This is the first real prompt-file structure for the browser agent in this repo.

### 6. Switched browser prompt loading to file-based templates

Updated [browser_subgraph.py](/F:/AgentBot/agentbot/prompts/browser_subgraph.py).

Instead of embedding the planner prompt directly in a Python function, it now loads:

- browser planner prompt from the browser prompt directory
- router prompt from the same directory

This means prompt changes now live primarily in prompt files, not in Python string blocks.

### 7. Moved browser planner input shape one step closer to browser-use

Updated [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py).

The planner input is still local to this project, but it is now organized more like browser-use:

- `<user_request>`
- `<agent_history>`
- `<agent_state>`
- `<browser_state>`

This is not yet a full browser-use message-manager port, but it is a meaningful alignment step in the planner interface.

### 8. Updated the top-level system hint

Updated [system.py](/F:/AgentBot/agentbot/prompts/system.py).

The global system prompt now reflects the new routing behavior:

- browser interaction may be routed automatically
- `/browser` still forces browser mode

## Validation

This iteration was validated with:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. graph construction check
   - build the main graph with real project settings

3. route behavior sanity check
   - explicit browser message routes directly to `browser`
   - non-explicit browser-like message routes to `route`
   - router output can branch to either `browser` or `chatbot`

These checks passed.

## Current Limitations

This iteration does not yet complete all of Phase 3.

Still pending:

- richer browser action migration from browser-use
- broader browser-use-style planner/history alignment
- routing decision visibility in more user-facing surfaces
- execution log enrichment for routing decisions

## Outcome

At the end of this iteration:

- browser routing is no longer explicit-prefix-only
- the architecture now has room for explainable model-guided routing
- browser prompt management has been moved onto a proper file-based foundation

This creates a much better base for the next Phase 3 steps, especially action expansion and deeper planner/history alignment.
