# Conversation Message Schema Refactor: Slice 2

## Background

After Slice 1, the project already had a richer conversation message schema at the storage and API layer:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

However, streaming and live frontend rendering still behaved too much like the old text-first model.

Two concrete issues remained:

- internal supervisor outputs could still leak into visible assistant text
- browser progress updates were still being pushed into `content` instead of staying in structured fields

This slice focused on making streaming and the live UI actually respect the new message schema.

## Goal

Move the runtime chat experience from:

- "everything eventually becomes content"

to:

- "content is only the visible final answer, while delegation and browser progress stay structured"

## What Was Implemented

### 1. Streaming now forwards supervisor decisions as structured events

Updated [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py).

Custom events from the `supervisor` source are now forwarded as:

- `supervisor_decision_made`

This makes the orchestration decision available to the frontend without turning it into visible assistant text.

### 2. Browser completion no longer pretends to be the final assistant reply

Updated [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py).

Previously, browser subgraph completion events could emit `assistant_completed` directly.

That behavior was wrong under the new supervisor-first architecture because:

- browser is a delegated worker
- the final user-facing reply should come from the `respond` node

This slice removed that coupling.

### 3. Visible assistant token streaming remains restricted to the final response node

Updated [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py).

Visible assistant deltas continue to be filtered by graph node, so only text from the user-visible response path is streamed into the assistant bubble.

This prevents internal orchestrator output from being treated as normal answer text.

### 4. Frontend stream event typing now includes supervisor decisions

Updated [api.ts](/F:/AgentBot/ui/src/shared/api/api.ts).

The frontend streaming schema now supports:

- `supervisor_decision_made`

This keeps the stream contract aligned with the backend.

### 5. Live assistant messages now carry structured delegation state

Updated [app-shell.tsx](/F:/AgentBot/ui/src/app/app-shell.tsx).

During live streaming:

- supervisor decisions now populate `delegation`
- browser lifecycle events now update `browser_task`
- browser progress no longer overwrites `content`
- final assistant text is written into:
  - `content`
  - `response`

This is the main runtime behavior shift in the slice.

### 6. Browser progress is now represented structurally instead of as fake answer text

Updated [app-shell.tsx](/F:/AgentBot/ui/src/app/app-shell.tsx).

Previously, browser events repeatedly replaced assistant `content` with generated status text.

Now:

- browser progress lives in `browser_task`
- delegation intent lives in `delegation`
- `content` remains reserved for the eventual visible answer

This keeps the message model semantically clean.

### 7. Added delegation display support in the chat UI

Updated:

- [message-list.tsx](/F:/AgentBot/ui/src/features/chat/components/message-list.tsx)
- [message-card.tsx](/F:/AgentBot/ui/src/features/chat/components/message-card.tsx)

Assistant cards can now show a lightweight delegation block using:

- `delegation.target`
- `delegation.status`
- `delegation.reason`
- `delegation.task`

This gives the user visibility into what the main agent decided without leaking raw orchestration JSON.

## Validation

This slice was validated with:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. Frontend build
   - `npm run build`

These checks passed.

## Current Limitations

This slice fixes the major schema/display mismatch, but there are still follow-up opportunities:

- refine the visual presentation of delegation vs browser task blocks
- reduce duplicated status wording if both delegation and browser task are present
- add richer frontend semantics for tool-planning assistant messages

## Outcome

At the end of this slice:

- supervisor decisions are no longer treated as normal assistant text
- browser progress is no longer forced into `content`
- the live chat UI now follows the richer conversation schema more closely

This is the point where the conversation model becomes meaningfully schema-driven instead of text-driven.
