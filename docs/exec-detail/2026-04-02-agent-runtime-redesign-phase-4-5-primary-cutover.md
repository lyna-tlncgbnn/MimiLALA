# Agent Runtime Redesign Phase 4-5 Primary Cutover

Date: `2026-04-02`

## Summary

This phase moved the main chat product path off the legacy JSONL transcript/execution stores and onto the new SQLite-backed runtime model.

After this cutover:

- conversation transcript reads come from SQLite
- sync and streaming chat execution write runs, transcript rows, and run steps to SQLite
- the streaming API uses run-oriented events
- the frontend consumes `/runs/stream`
- tool activity is no longer treated as ordinary chat messages in the main UI flow

The legacy JSONL modules still exist in the repository, but they are no longer the primary source of truth for the main chat path.

## Scope

This phase covered the design-document phases:

- Phase 4: Switch API
- Phase 5: Switch Frontend

It also included a small cleanup pass to remove direct primary-path imports from the old JSONL conversation module.

## What Changed

### 1. Conversation service switched to SQLite as the primary read model

New service:

- [sqlite_conversations.py](F:/AgentBot/agentbot/services/sqlite_conversations.py)

Key responsibilities:

- list conversations from SQLite
- create conversations in SQLite
- load transcript messages from SQLite
- rename conversations in SQLite
- delete conversations from SQLite through the new runtime persistence layer
- provide transcript history as LangChain messages for runtime execution

New transcript model:

- `TranscriptMessage`

This is the product transcript model used by API routes and runtime history loading.

Important behavioral rule:

- transcript history now includes only user-visible rows from `messages`
- raw tool rows are not loaded into conversation transcript history

### 2. Conversation API routes now read transcript data from SQLite

Updated route module:

- [conversations.py](F:/AgentBot/agentbot/api/routes/conversations.py)

Affected endpoints:

- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/messages`
- `PATCH /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`

Behavioral change:

- `GET /api/conversations/{conversation_id}` now returns transcript rows serialized from SQLite transcript messages
- the returned `messages` payload no longer depends on legacy JSONL message loading
- raw tool transcript is no longer returned by these endpoints

### 3. Sync runner switched to SQLite-backed runtime persistence

Updated module:

- [runner.py](F:/AgentBot/agentbot/app/runner.py)

Key changes:

- conversation history is loaded from SQLite transcript rows
- a run is created in SQLite at task start
- the user message is persisted into SQLite transcript storage
- tool calls are persisted as `run_steps`
- tool completions update those `run_steps`
- the final assistant answer is persisted as a visible transcript message
- run completion and run failure are persisted to SQLite

This means one user request now maps to:

- one `runs` row
- one visible `messages` row for the user prompt
- zero or more `run_steps` rows during execution
- one visible `messages` row for the final assistant result on success

### 4. Streaming runner switched to run-oriented SSE events

Updated module:

- [streaming_runner.py](F:/AgentBot/agentbot/app/streaming_runner.py)

The old chat-centric event model was replaced on the primary path with:

- `run_started`
- `step_started`
- `step_completed`
- `assistant_final_delta`
- `assistant_finalized`
- `run_completed`
- `run_failed`
- `done`

Behavioral changes:

- stream initialization now creates a SQLite run before graph execution
- tool activity is emitted as run-step events instead of tool-message bubbles
- final assistant text is streamed separately from process events
- run completion and failure are represented explicitly

Compatibility note:

- the backend still exposes a compatibility alias at `POST /api/conversations/{conversation_id}/messages/stream`
- this alias forwards to the new run-oriented implementation
- the primary client path now uses `POST /api/conversations/{conversation_id}/runs/stream`

### 5. Frontend switched to the new stream contract

Updated modules:

- [api.ts](F:/AgentBot/ui/src/shared/api/api.ts)
- [app-shell.tsx](F:/AgentBot/ui/src/app/app-shell.tsx)

Key frontend changes:

- stream target switched from `/messages/stream` to `/runs/stream`
- event handling switched from legacy assistant/tool events to run-oriented events
- tool activity no longer appends synthetic `tool` chat messages into `liveMessages`
- final assistant output is built from `assistant_final_delta` and `assistant_finalized`
- conversation history continues to come from transcript APIs

Resulting UI behavior:

- the main message list is now transcript-oriented
- tool traffic is no longer rendered as ordinary chat bubbles during the active stream
- the frontend is aligned with the new `conversation + run` mental model

### 6. Primary-path dependency on the legacy conversation module was reduced

Small cleanup changes:

- [common.py](F:/AgentBot/agentbot/storage/common.py)
- [shadow_runtime.py](F:/AgentBot/agentbot/storage/shadow_runtime.py)
- [serializers.py](F:/AgentBot/agentbot/api/serializers.py)

What changed:

- `AGENTBOT_META_KEY` was moved into shared storage helpers
- runner and streaming runner now use that shared constant instead of importing it from the old JSONL conversation module
- `RuntimeShadowWriter` was reframed as the SQLite runtime persistence helper instead of a legacy shadow-only bridge
- unused serializer dependency on legacy `ConversationMeta` was removed

This does not delete the old JSONL code, but it removes it from the new main path.

## Current Main Flow After This Cutover

The primary streaming flow is now:

1. frontend calls `POST /api/conversations/{conversation_id}/runs/stream`
2. backend loads visible transcript history from SQLite
3. backend creates a `runs` row and a visible user transcript row
4. LangGraph executes against transcript history
5. tool calls create or update `run_steps`
6. final assistant output is streamed as `assistant_final_delta`
7. final assistant output is persisted as a visible transcript message
8. run status is marked `completed` or `failed`
9. frontend clears temporary live state and refreshes transcript history from SQLite

The primary sync flow is analogous, except it returns the refreshed transcript snapshot rather than streaming deltas.

## Files Added Or Materially Changed

Backend:

- [sqlite_conversations.py](F:/AgentBot/agentbot/services/sqlite_conversations.py)
- [conversations.py](F:/AgentBot/agentbot/services/conversations.py)
- [chat.py](F:/AgentBot/agentbot/services/chat.py)
- [runner.py](F:/AgentBot/agentbot/app/runner.py)
- [streaming_runner.py](F:/AgentBot/agentbot/app/streaming_runner.py)
- [conversations.py](F:/AgentBot/agentbot/api/routes/conversations.py)
- [serializers.py](F:/AgentBot/agentbot/api/serializers.py)
- [common.py](F:/AgentBot/agentbot/storage/common.py)
- [shadow_runtime.py](F:/AgentBot/agentbot/storage/shadow_runtime.py)

Frontend:

- [api.ts](F:/AgentBot/ui/src/shared/api/api.ts)
- [app-shell.tsx](F:/AgentBot/ui/src/app/app-shell.tsx)

## Verification Performed

### Python import verification

Verified these modules import successfully:

- `agentbot.api.app`
- `agentbot.api.routes.conversations`
- `agentbot.app.runner`
- `agentbot.app.streaming_runner`
- `agentbot.services.chat`
- `agentbot.services.conversations`
- `agentbot.services.sqlite_conversations`
- `agentbot.storage.shadow_runtime`

### Frontend build verification

Command:

```powershell
cd ui
npm run build
```

Result:

- TypeScript build passed
- Vite production build passed

Observed warning:

- bundle size warning for a large chunk after minification

This warning is unrelated to the runtime-model cutover and does not block correctness.

## What This Phase Did Not Do

This cutover does not yet include:

- LangGraph SQLite checkpointer integration
- historical run-step UI panel in the frontend
- artifact endpoints
- a dedicated sync `POST /api/conversations/{conversation_id}/runs` endpoint
- deletion of legacy JSONL modules from the repository

## Migration State After This Phase

The repository is now in a mixed-code but single-primary-path state:

- new chat runtime path: SQLite primary
- new conversation transcript path: SQLite primary
- new streaming path: run-oriented
- old JSONL modules: still present, no longer primary for current chat flow

This is the intended stopping point before:

- adding the remaining run-oriented API surface
- wiring LangGraph checkpointer persistence
- removing legacy JSONL modules entirely

## Recommended Next Step

The next highest-value step is:

- implement LangGraph SQLite checkpointer integration and store durable `thread_id`/checkpoint linkage on each run

After that, the project can safely move into:

- historical run replay / inspection
- interrupt and resume capabilities
- full removal of legacy JSONL persistence code
