# Conversation Message Schema Refactor: Slice 1

## Background

The project had reached a point where the conversation message schema was too thin for the real agent behavior.

The old structure mostly treated messages as:

- `role`
- `content`
- optional `tool_calls`

That was no longer enough once the system started to include:

- supervisor decisions
- browser delegation
- browser task summaries
- tool planning without visible answer text

This slice focused on the first concrete step: making the conversation-layer schema rich enough to represent these semantics directly.

## Goal

Introduce a richer assistant message structure at the conversation layer so that:

- `content` remains the user-visible text
- structured assistant semantics can live in explicit fields
- browser delegation and browser task summaries can be preserved in conversation records
- old conversations still load

## What Was Implemented

### 1. Extended conversation storage for richer assistant fields

Updated [conversation.py](/F:/AgentBot/agentbot/memory/conversation.py).

Conversation JSONL records can now preserve these assistant-specific fields:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

This was added at both directions:

- `_message_to_record(...)`
- `_record_to_message(...)`

That means the richer structure now survives persistence instead of being only transient in memory.

### 2. Added assistant response normalization in storage

Updated [conversation.py](/F:/AgentBot/agentbot/memory/conversation.py).

When an assistant message has visible text, the storage layer now normalizes it into:

- `response: {"text": ...}`

This makes assistant response semantics explicit even when only `content` was initially provided.

### 3. Extended API serialization for richer message payloads

Updated [conversations.py](/F:/AgentBot/agentbot/services/conversations.py).

`message_to_api_dict(...)` now exposes:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

This means the frontend can consume these fields directly from conversation APIs instead of guessing from `content`.

### 4. Extended local API message schema

Updated [schemas.py](/F:/AgentBot/agentbot/api/schemas.py).

`MessagePayload` now officially supports:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

This makes the richer shape part of the backend contract.

### 5. Updated assistant message creation in the graph

Updated [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py).

The main graph now writes richer assistant semantics when creating assistant messages:

- `respond(...)` writes:
  - `response`
  - `state`
  - `delegation` when the answer came from browser delegation
  - `browser_task` when available

- `tool_chatbot(...)` now annotates emitted assistant messages with:
  - `state`
  - `response` when visible text exists

This keeps the graph aligned with the conversation schema instead of leaving the storage layer to infer everything.

### 6. Updated frontend message typing

Updated [api.ts](/F:/AgentBot/ui/src/shared/api/api.ts).

The frontend message schema now recognizes:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

This means the browser/chat UI can evolve from a text-only model toward a structured message model without another backend contract change.

### 7. Updated client-side optimistic assistant message defaults

Updated [app-shell.tsx](/F:/AgentBot/ui/src/app/app-shell.tsx).

Optimistic in-memory assistant messages now initialize the richer fields:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

This keeps the temporary client state shape consistent with the API shape.

## Validation

This slice was validated with:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. Frontend build
   - `npm run build`

3. Conversation record roundtrip test
   - create an `AIMessage` with:
     - `response`
     - `delegation`
     - `browser_task`
     - `state`
     - `metadata`
   - serialize it through `_message_to_record(...)`
   - deserialize it through `_record_to_message(...)`
   - verify the structured fields survive

These checks passed.

## Current Limitations

This slice establishes the richer message schema, but it does not yet fully redesign every UI behavior around it.

Still pending:

- render `delegation` more explicitly in the frontend
- tighten streaming semantics so internal orchestration output never appears as visible assistant text
- further normalize tool-planning messages vs final assistant messages

## Outcome

At the end of this slice:

- conversation messages are no longer limited to `content` plus ad hoc extras
- browser delegation and browser task summary are now first-class conversation fields
- the backend, storage layer, and frontend types now agree on a richer assistant message shape

This creates the right base for the next slice, which is to make streaming and UI presentation fully respect the new schema.
