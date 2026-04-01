# Browser Supervisor Refactor: Slice 1

## Background

The previous browser integration used a router-first shape:

- browser routing happened before the main chat agent
- a dedicated route node classified the turn into browser or normal chat

That design was useful as an intermediate learning step, but it caused a real product problem:

- weak or indirect browser intent could be missed before the main agent ever reasoned over the turn
- when routing missed, the main chat agent could incorrectly talk as if browser capability did not exist

This slice starts the architectural refactor toward a supervisor-first design.

## Goal

Replace the old router-first graph entry with a supervisor-first orchestration skeleton where:

- every turn enters the main agent first
- the main agent decides whether to:
  - respond directly
  - use normal tools
  - delegate to the browser subgraph

This slice focused on the graph backbone first, not on every downstream UI detail.

## What Was Implemented

### 1. Added a supervisor decision model

Added [supervisor.py](/F:/AgentBot/agentbot/models/supervisor.py).

The main agent now emits a structured decision with:

- `decision`
- `reason`
- `response`
- `browser_task`

Supported decisions are:

- `respond`
- `tools`
- `browser`

This is intentionally broader than the old router model, because the supervisor is not just classifying. It is choosing the next orchestration step.

### 2. Expanded main graph state for orchestration

Updated [state.py](/F:/AgentBot/agentbot/graph/state.py).

The main graph now carries explicit orchestration metadata:

- `supervisor_decision`
- `browser_task_request`
- `browser_task_result`

This replaces the old single `routing_decision` focus with state that matches the new architecture.

### 3. Introduced supervisor prompt files

Added:

- [__init__.py](/F:/AgentBot/agentbot/prompts/supervisor/__init__.py)
- [loader.py](/F:/AgentBot/agentbot/prompts/supervisor/loader.py)
- [system_prompt.md](/F:/AgentBot/agentbot/prompts/supervisor/system_prompt.md)

This creates a dedicated prompt layer for orchestration decisions and keeps that responsibility separate from:

- browser execution prompting
- normal assistant response prompting

### 4. Replaced the old route-first graph shape

Updated [builder.py](/F:/AgentBot/agentbot/graph/builder.py).

The main graph now follows a supervisor-first shape:

- `START -> supervisor`
- `supervisor -> respond | tool_chatbot | browser`
- `tools -> supervisor`
- `browser -> supervisor`
- `respond -> END`

This is the key structural change in the slice.

### 5. Replaced router logic with supervisor routing

Updated [routes.py](/F:/AgentBot/agentbot/graph/routes.py).

The graph no longer uses:

- entry-time browser intent rules
- a separate route classifier in front of the main agent

Instead, routing now happens after the supervisor emits its structured decision.

### 6. Reworked node responsibilities

Updated [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py).

The node layer now has these main roles:

- `supervisor`
- `respond`
- `tool_chatbot`
- `execute_tools`
- `call_browser_subgraph`

Important change:

- the browser node no longer directly becomes the final assistant answer
- it behaves as a delegated worker
- it writes structured browser result back into state
- control returns to the supervisor

### 7. Updated the global system prompt

Updated [system.py](/F:/AgentBot/agentbot/prompts/system.py).

The top-level prompt now reflects the real architecture:

- browser capability exists
- the main agent is responsible for deciding browser delegation
- the assistant should not claim browser capability is unavailable just because browser is not exposed as a normal tool

### 8. Updated graph architecture documentation

Updated [graph-flow.md](/F:/AgentBot/docs/architecture/graph-flow.md).

The architecture doc now describes the supervisor-first graph instead of the older router-first design.

## Validation

This slice was validated with:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. Main graph construction check
   - build the graph with real project settings and model config

3. Supervisor routing sanity check
   - `respond` routes to `respond`
   - `tools` routes to `tool_chatbot`
   - `browser` routes to `browser`

These checks passed.

## Current Limitations

This slice establishes the supervisor-first architecture, but it does not yet complete every consequence of the refactor.

Still pending:

- supervisor prompt tuning against real browser-intent conversations
- streaming/UI refinement for supervisor decision visibility
- more realistic end-to-end chat tests for browser delegation
- possible cleanup of now-obsolete router-specific files and concepts

## Outcome

At the end of this slice:

- all turns now enter the main agent first
- browser delegation is no longer decided by a pre-chat router node
- the browser subgraph now behaves as a delegated worker under main-agent control

This is the correct architectural base for the next iterations of browser delegation quality.
