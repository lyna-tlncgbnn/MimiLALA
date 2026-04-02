# Agent Runtime Redesign Phase 4 Run-Oriented API Surface

Date: `2026-04-02`

## Summary

This step finished the main run-oriented API surface defined in the redesign document.

After this change:

- conversations expose a run listing endpoint
- conversations expose a formal sync run execution endpoint
- the old sync `/messages` endpoint still exists for compatibility
- the frontend API client knows about run summaries and conversation run listings

This phase does not change the active UI yet. It completes the backend contract needed for historical run inspection and future execution-panel work.

## Scope

This step extends the earlier API cutover work by adding the missing run-oriented conversation endpoints:

- `GET /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs`

This aligns the conversation API with the redesign target:

- conversation transcript endpoints
- sync run execution endpoint
- streaming run execution endpoint
- run detail and run steps endpoints

## What Changed

### 1. Added run-oriented response schemas

Updated file:

- [schemas.py](F:/AgentBot/agentbot/api/schemas.py)

New schemas:

- `ConversationRunsDetail`
- `SendRunResponse`

Purpose:

- `ConversationRunsDetail` returns one conversation summary plus its run list
- `SendRunResponse` returns the conversation, the persisted run summary, refreshed transcript messages, and the final assistant reply

### 2. Extended chat service with a sync run-oriented execution method

Updated file:

- [chat.py](F:/AgentBot/agentbot/services/chat.py)

New method:

- `send_run_to_conversation(conversation_id, user_text)`

Behavior:

- executes a sync run through `run_once`
- reloads the conversation transcript from SQLite
- loads the latest persisted run for the conversation
- returns `meta + run + messages + reply`

Why this method exists:

- the old sync path returned only transcript-oriented response data
- the run-oriented API needs to expose the run object explicitly

### 3. Added `GET /api/conversations/{conversation_id}/runs`

Updated file:

- [conversations.py](F:/AgentBot/agentbot/api/routes/conversations.py)

Behavior:

- validates that the conversation exists
- reads runs from SQLite using `RunRepository.list_for_conversation`
- returns:
  - serialized conversation summary
  - ordered run list

This endpoint is the conversation-level entry point for historical run inspection.

### 4. Added `POST /api/conversations/{conversation_id}/runs`

Updated file:

- [conversations.py](F:/AgentBot/agentbot/api/routes/conversations.py)

Behavior:

- executes one sync run
- returns:
  - conversation summary
  - run summary
  - updated transcript messages
  - final assistant reply payload

Compatibility behavior:

- old `POST /api/conversations/{conversation_id}/messages` is still present
- the old route remains useful during migration
- the new route is the preferred run-oriented sync API

### 5. Frontend API client now understands run listings and sync run responses

Updated file:

- [api.ts](F:/AgentBot/ui/src/shared/api/api.ts)

New client types:

- `RunSummary`
- `ConversationRunsDetail`

New client functions:

- `sendRun(conversationId, content)`
- `listConversationRuns(conversationId)`

This does not change the UI yet, but it gives the frontend a stable typed contract for the next execution-history work.

## Resulting API Surface

The main conversation/run API surface is now:

Conversation endpoints:

- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/messages`
- `PATCH /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`

Run-oriented conversation endpoints:

- `GET /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs`
- `POST /api/conversations/{conversation_id}/runs/stream`

Compatibility endpoints still present:

- `POST /api/conversations/{conversation_id}/messages`
- `POST /api/conversations/{conversation_id}/messages/stream`

Run detail endpoints:

- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/steps`

## Verification Performed

### 1. Python import verification

Verified:

- `agentbot.api.routes.conversations`
- `agentbot.services.chat`
- `agentbot.api.schemas`

### 2. Frontend build verification

Command:

```powershell
cd ui
npm run build
```

Result:

- build passed

### 3. SQLite response-shape verification

A temporary SQLite database was created and seeded with:

- one conversation
- one run

Then the same serializer path used by the route was exercised to verify the returned shape:

- conversation summary serialized correctly
- run summary list serialized correctly

The temporary validation database was deleted after the check.

## Files Changed

- [schemas.py](F:/AgentBot/agentbot/api/schemas.py)
- [chat.py](F:/AgentBot/agentbot/services/chat.py)
- [conversations.py](F:/AgentBot/agentbot/api/routes/conversations.py)
- [api.ts](F:/AgentBot/ui/src/shared/api/api.ts)

## What This Step Did Not Do

This step does not yet include:

- frontend rendering of historical runs
- execution timeline replay UI
- artifact endpoints
- removal of compatibility `/messages` endpoints

## Recommended Next Step

The next highest-value step is:

- start consuming `GET /api/conversations/{conversation_id}/runs` and `GET /api/runs/{run_id}/steps` in the frontend so historical execution detail can be shown without reading raw transcript noise
