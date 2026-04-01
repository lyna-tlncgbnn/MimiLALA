# Browser Subgraph Phase 2: Chat Integration

## Background

Before this iteration, the browser subgraph already existed as an explicit capability behind:

- `POST /api/browser/tasks`

That proved the architecture and the browser-use runtime bridge, but it still lived outside the main chat flow.

This iteration focused on the next smallest useful step:

- connect the browser subgraph into the main chat graph
- keep the existing chat/tool loop intact
- expose minimal browser progress through chat streaming

## Goal

Allow the main chat pipeline to enter browser mode without introducing a full supervisor or multi-agent orchestration layer.

The target was:

- explicit browser routing
- minimal wrapper-node integration
- browser progress visible in SSE

## What Was Implemented

### 1. Added explicit browser routing at graph entry

Updated [routes.py](/F:/AgentBot/agentbot/graph/routes.py) to add an entry router.

The main graph now checks the latest user message before entering the normal chat loop.

Current explicit browser triggers are:

- `/browser ...`
- `browser: ...`
- `浏览器: ...`
- `使用浏览器: ...`

If one of these prefixes is present, the graph routes into the browser wrapper node instead of the normal `chatbot -> tools -> chatbot` path.

### 2. Added a browser wrapper node in the main graph

Updated [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py) to add `call_browser_subgraph(...)`.

This wrapper node:

- extracts the browser task text from the latest user message
- extracts the first URL as a best-effort `start_url`
- builds and runs the browser subgraph
- converts the browser result back into a normal assistant message

This preserves the original architecture boundary:

- LangGraph main graph remains the top-level orchestrator
- browser-use remains an execution/runtime layer behind the browser subgraph

### 3. Inserted browser routing into the main graph builder

Updated [builder.py](/F:/AgentBot/agentbot/graph/builder.py).

The main graph now has:

- `entry`
- `browser`
- `chatbot`
- `tools`

Flow:

- `START -> entry`
- `entry -> browser` for explicit browser turns
- `entry -> chatbot` for regular chat turns
- `browser -> END`
- regular chat path remains unchanged

This is intentionally narrow:

- no supervisor
- no shared browser state in the main graph
- no broad refactor of the existing tool loop

### 4. Added minimal browser SSE visibility

Updated [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py).

The outer chat stream now enables LangGraph `custom` stream mode and forwards browser wrapper events to the frontend SSE layer.

Current browser streaming events include:

- `browser_subgraph_started`
- `browser_observed`
- `browser_action_planned`
- `browser_action_started`
- `browser_action_finished`
- `browser_subgraph_completed`
- `browser_subgraph_failed`

These are intentionally summary-level events, not fine-grained browser internal traces.

### 5. Passed browser LLM config through the main graph

Updated:

- [runner.py](/F:/AgentBot/agentbot/app/runner.py)
- [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py)
- [builder.py](/F:/AgentBot/agentbot/graph/builder.py)

The main graph now passes OpenAI-compatible config down so the browser subgraph can continue using extraction and browser-use worker capabilities consistently.

### 6. Added a user-facing browser trigger hint

Updated [system.py](/F:/AgentBot/agentbot/prompts/system.py).

The base system prompt now includes a short hint that users can explicitly start browser mode with:

- `/browser`
- `browser:`
- `浏览器:`

This does not change orchestration by itself, but it makes the feature discoverable.

## Validation

This iteration was validated with:

- Python compile check:
  - `.\.venv\Scripts\python.exe -m compileall agentbot`
- main graph build check with real project settings:
  - build the main graph with chat model and browser config
- routing check:
  - explicit browser prefix routes to `browser`
  - normal message routes to `chatbot`

These checks passed.

## Current Behavior

After this iteration, browser mode is available from chat through explicit prefixes.

Example:

```text
/browser 打开 https://example.com 然后告诉我页面标题
```

Regular chat behavior remains on the existing path.

## Current Limitations

This iteration does not yet provide:

- automatic browser intent detection without explicit prefixes
- browser events in non-streaming execution logs at the same detail level as SSE
- fully granular live subgraph visualization
- more advanced browser routing policies

## Outcome

The project has now crossed an important threshold:

- the browser subgraph is no longer only a standalone API capability
- it is part of the main chat graph

The implementation is still deliberately narrow and explicit, which matches the current learning-first architecture and keeps the graph readable.
