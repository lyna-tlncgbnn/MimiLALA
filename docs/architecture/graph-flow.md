# Graph Flow

## Current Graph Shape

The main graph is now built in [builder.py](/F:/AgentBot/agentbot/graph/builder.py) as a **supervisor-first** graph:

```text
START
  -> supervisor
  -> respond | tool_chatbot | browser

tool_chatbot
  -> tools
  -> END

tools
  -> supervisor

browser
  -> supervisor

respond
  -> END
```

This is a deliberate change from the older router-first design.

## Why This Shape Exists

The project no longer decides browser delegation before the main agent runs.

Instead:

1. every turn enters the main agent first
2. the main agent emits a structured orchestration decision
3. the graph follows that decision into one of three paths:
   - direct response
   - standard tools
   - browser subgraph

This makes browser delegation a main-agent responsibility rather than a pre-chat classifier responsibility.

## Main Nodes

### `supervisor`

Implemented in [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py).

Responsibilities:

- read the full conversation state
- decide whether the turn should:
  - respond directly
  - use standard tools
  - delegate to the browser subgraph
- emit a structured supervisor decision into graph state

### `respond`

Implemented in [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py).

Responsibilities:

- convert the supervisor's final response into the user-facing `AIMessage`
- attach browser task metadata when the answer is based on browser delegation

### `tool_chatbot`

Implemented in [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py).

Responsibilities:

- run the tool-enabled chat model for standard tool usage
- produce tool calls when needed

### `tools`

Implemented through LangGraph `ToolNode`.

Responsibilities:

- execute normal registered tools
- return results to the supervisor path

### `browser`

Implemented in [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py), delegating into the browser subgraph built by [browser_builder.py](/F:/AgentBot/agentbot/graph/browser_builder.py).

Responsibilities:

- execute browser work as a delegated worker
- stream browser progress events
- write structured browser results back into graph state
- return control to the supervisor

Important:

- the browser node no longer directly becomes the final assistant answer
- the supervisor remains the main orchestration brain for the turn

## State Model

The main graph still extends `MessagesState`, but now adds orchestration metadata in [state.py](/F:/AgentBot/agentbot/graph/state.py):

- `supervisor_decision`
- `browser_task_request`
- `browser_task_result`

This means the graph is no longer only "message list plus tool loop". It now carries explicit delegation state.

## Synchronous Execution Flow

1. runner builds input messages:
   - system prompt
   - persisted conversation history
   - current user message
2. graph enters `supervisor`
3. supervisor decides:
   - `respond`
   - `tools`
   - `browser`
4. if `respond`, graph emits final assistant message and ends
5. if `tools`, graph enters `tool_chatbot`
6. if tool calls are emitted, `tools` executes them and returns to `supervisor`
7. if `browser`, browser subgraph executes and returns structured result to `supervisor`
8. supervisor then decides the next step again, usually a final `respond`
9. runner persists final messages and execution events

## Streaming Execution Flow

In streaming chat:

1. frontend calls the streaming message endpoint
2. FastAPI delegates to [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py)
3. `graph.stream(...)` emits messages, updates, values, and custom events
4. the UI receives:
   - assistant deltas
   - tool lifecycle events
   - browser subgraph events
   - supervisor decision events when emitted
5. after completion, conversation history is persisted as usual

## Current Limits

The graph is now supervisor-first, but the broader architecture still has these limits:

- no checkpointer
- no long-term memory
- no full execution visualization panel
- browser execution is specialized, but not yet a full multi-subagent ecosystem
- streaming is improving, but supervisor-level events are not yet fully surfaced everywhere in the UI
