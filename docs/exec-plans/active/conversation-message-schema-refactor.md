# Conversation Message Schema Refactor Plan

## Status

ACTIVE

## Why This Refactor Exists

The current conversation message schema is too thin for the agent architecture the project now has.

Right now a stored conversation message mainly contains:

- `role`
- `content`
- `tool_call_id`
- `tool_calls`
- partial browser metadata in some assistant messages

This worked when the system was mostly:

- user message
- assistant text
- optional tool call

But the architecture now includes:

- supervisor decisions
- delegated browser tasks
- browser task summaries
- tool call planning without user-facing text
- final user-facing responses that should be separated from orchestration metadata

The result is a schema mismatch:

- user-visible answer content and internal orchestration data are not clearly separated
- some internal data can leak into `content`
- tool / delegation semantics are not first-class in the conversation layer
- the frontend has to infer too much from too little structure

This refactor treats the **conversation record** as the primary source of truth for message semantics.

## Product Decision

We will **not** treat `execution` as the primary home for these details right now.

Instead:

- conversation records will carry the full structured message semantics needed by the app
- `content` will only mean user-visible response text
- internal orchestration and delegation information will live in structured message fields

This keeps the app simpler and more directly useful in the current stage of the project.

## Refactor Goal

Upgrade the conversation message schema from a text-first shape to a structured assistant-message model that can represent:

- direct answers
- tool planning
- tool execution results
- browser delegation
- browser task summaries

without forcing all of that into `content`.

## Core Design Principle

`content` should mean exactly one thing:

- the user-visible natural language text for that message

Everything else should be moved into explicit structured fields.

That means these should **not** be represented as raw `content`:

- supervisor orchestration JSON
- browser delegation decisions
- tool planning payloads
- internal "reason" fields intended for control flow

## Proposed Target Message Schema

### Shared base fields

Every message record keeps:

- `type`
- `message_id`
- `timestamp`
- `role`
- `content`
- `name`
- `metadata`

Where:

- `content` is always a string
- `metadata` is a general extension field for future light metadata

### Assistant message fields

Assistant messages should additionally support:

- `response`
- `tool_calls`
- `delegation`
- `browser_task`
- `state`

Recommended normalized shape:

```json
{
  "type": "message",
  "message_id": "msg_xxx",
  "timestamp": "2026-04-01T10:00:00+08:00",
  "role": "assistant",
  "content": "今天重庆多云，当前气温 22°C。",
  "response": {
    "text": "今天重庆多云，当前气温 22°C。"
  },
  "tool_calls": [],
  "delegation": {
    "target": "browser",
    "status": "completed",
    "reason": "需要实时网页信息",
    "task": "Search for today's weather in Chongqing..."
  },
  "browser_task": {
    "task": "Search for today's weather in Chongqing...",
    "status": "completed",
    "final_response": "今天重庆多云，当前气温 22°C。",
    "error_message": null,
    "current_url": "...",
    "page_title": "...",
    "step_count": 4,
    "steps": []
  },
  "state": {
    "kind": "final"
  },
  "metadata": {}
}
```

This shape is intentionally redundant in one place:

- `content`
- `response.text`

That redundancy is acceptable because:

- `content` remains easy for generic chat rendering
- `response` makes the semantics explicit

## Recommended Field Semantics

### `content`

Meaning:

- only the user-visible answer text for that message

Rules:

- if the assistant has not yet produced a user-visible answer, `content` should be `""`
- raw supervisor JSON must never be placed here
- raw tool call payloads must never be placed here

### `response`

Meaning:

- normalized user-facing response payload

Suggested shape:

```json
{
  "text": "..."
}
```

Why keep it if `content` exists:

- explicit semantics
- easier future extension
- avoids overloading `content` as the only contract

### `tool_calls`

Meaning:

- explicit tool call requests emitted by the assistant

Rules:

- should be present on assistant messages when the assistant plans tool use
- `content` may be empty for these messages
- the frontend should render tool activity from this field, not infer it from empty text

### `delegation`

Meaning:

- explicit subagent delegation metadata

Suggested shape:

```json
{
  "target": "browser",
  "status": "planned" | "running" | "completed" | "failed",
  "reason": "...",
  "task": "..."
}
```

This is the key field that solves the current leakage problem.

Supervisor decisions like:

- `decision`
- `reason`
- `browser_task`

should be normalized into `delegation`, not dumped into `content`.

### `browser_task`

Meaning:

- browser subgraph task summary and result payload

This field already exists in lightweight form. It should become the canonical browser-specific summary field for assistant messages.

It should include:

- task
- status
- final response
- error message
- current URL
- page title
- step count
- steps

### `state`

Meaning:

- what stage this assistant message represents

Suggested values:

- `planning`
- `tooling`
- `delegating`
- `final`

This can help the frontend reason about partial vs final messages without string hacks.

## Message-Type Behavior by Role

### User messages

Keep simple:

- `content` is the user text
- no `tool_calls`
- no `delegation`

### Tool messages

Keep current basics, but allow `metadata`:

- `tool_call_id`
- `name`
- `content`
- optional structured output field later if needed

### Assistant messages

This refactor mainly targets assistant messages.

Assistant messages may represent three broad cases:

1. final answer
2. tool planning
3. browser delegation summary

The schema should support all three directly.

## Current Code Impact

This refactor will affect four layers together.

### 1. Conversation storage

Files:

- [conversation.py](/F:/AgentBot/agentbot/memory/conversation.py)

Needed changes:

- extend `_message_to_record(...)`
- extend `_record_to_message(...)`
- preserve assistant structured fields in JSONL
- maintain backward compatibility for older conversation files

### 2. Conversation API serialization

Files:

- [conversations.py](/F:/AgentBot/agentbot/services/conversations.py)
- [schemas.py](/F:/AgentBot/agentbot/api/schemas.py)

Needed changes:

- expose the new structured fields in API payloads
- stop treating assistant content as the only meaningful field

### 3. Streaming layer

Files:

- [streaming_runner.py](/F:/AgentBot/agentbot/app/streaming_runner.py)

Needed changes:

- ensure supervisor internal outputs are converted into structured delegation fields
- do not surface supervisor raw JSON as `content`
- emit final assistant content only from the user-visible response path

### 4. Frontend message model

Files:

- [api.ts](/F:/AgentBot/ui/src/shared/api/api.ts)
- message rendering components in `ui/src/features/chat/`

Needed changes:

- update TypeScript schemas
- render text from `content`
- render tools from `tool_calls`
- render browser/task state from `delegation` and `browser_task`
- stop assuming all assistant semantics are encoded in `content`

## Migration Strategy

### Step 1. Define the target API/message schema

Introduce the new fields in:

- Python API schema
- TypeScript schema

Acceptance:

- frontend and backend agree on the new message shape

### Step 2. Update storage serialization

Teach conversation storage to read/write:

- `response`
- `delegation`
- `browser_task`
- `state`
- `metadata`

Acceptance:

- new conversations persist the richer schema
- old conversations still load

### Step 3. Normalize assistant message creation

Update graph/runner code so assistant messages are built consistently:

- `content` only contains user-visible text
- supervisor decisions become `delegation`
- tool planning becomes `tool_calls`
- browser summary becomes `browser_task`

Acceptance:

- no supervisor JSON appears in `content`

### Step 4. Update frontend rendering

Render messages according to semantic fields rather than only `content`.

Acceptance:

- browser delegation is visible without polluting the message text
- tool use is visible without relying on empty-content heuristics

### Step 5. Backfill compatibility behavior

Add compatibility handling for older messages missing new fields.

Acceptance:

- old conversations still display
- new conversations display with richer semantics

## Explicit Non-Goals

This refactor does not aim to:

- redesign execution storage
- build a full event-sourcing system
- remove `content`
- redesign all frontend visual styles at the same time

It is specifically about making the **conversation message schema** match the current agent architecture.

## Risks

### 1. Backward compatibility

Old stored conversations only have the thin schema.

Mitigation:

- make all new fields optional at load time
- default missing fields to `null` / empty lists

### 2. Mixed partial/final message handling

Streaming currently creates partial assistant messages.

Mitigation:

- clearly distinguish partial orchestration state from final user-visible response
- use `state.kind` or equivalent to avoid ambiguity

### 3. Frontend complexity

The frontend will now need to understand more than `content`.

Mitigation:

- keep the field model simple
- avoid deeply nested or overly generic schemas

## Recommended Outcome

After this refactor, conversation messages should behave like this:

- `content` is only what the user should read
- `tool_calls` explicitly describe tool planning
- `delegation` explicitly describes subagent delegation
- `browser_task` carries browser execution summary
- internal orchestration data no longer leaks into user-visible text

## Final Recommendation

Treat this as a schema refactor, not a display patch.

The real problem is not only that the UI showed JSON once.  
The deeper problem is that the conversation model currently lacks the fields needed to represent the agent's real behavior cleanly.

This plan fixes that at the right layer.
