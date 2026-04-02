# Agent Runtime Redesign Phase 3 Checkpointer Integration

Date: `2026-04-02`

## Summary

This phase wired LangGraph's SQLite checkpointer into the main chat runtime.

After this change:

- graph compilation uses a SQLite checkpointer
- each run executes with a durable `thread_id`
- checkpoint state is stored in `workspace/langgraph_checkpoints.db`
- existing conversations without checkpoints can be seeded once from transcript history
- later runs on the same conversation resume from checkpoints instead of replaying transcript rows every time

This is the first point where the runtime matches the intended `conversation/thread + run + step + checkpoint` model in the redesign document.

## Why This Phase Was Needed

Before this step, the project had already moved transcript, runs, and run steps into SQLite, but LangGraph execution itself was still stateless between invocations.

That meant:

- conversation history had to be reconstructed from transcript rows on every run
- there was no durable graph state per thread
- replay and recovery features still had no substrate

The redesign document explicitly separates:

- transcript
- runs
- steps
- checkpoints

This phase adds the missing checkpoint layer.

## Official Guidance Applied

This implementation follows LangGraph's persistence model:

- compile the graph with a checkpointer
- invoke with `configurable.thread_id`
- persist state snapshots to the thread at each step

Reference used:

- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)

The specific checkpointer library used here is:

- `langgraph-checkpoint-sqlite`

Key LangGraph guidance used in this phase:

- checkpoint persistence is organized around `thread_id`
- state is saved after graph steps as checkpoints
- application UI should not depend directly on raw checkpoint rows

That maps directly to the current project model:

- `conversation_id` is used as the runtime `thread_id`
- transcript remains in `messages`
- process UI remains in `run_steps`
- checkpoint storage is separate and internal

## Dependency Change

Added package:

- `langgraph-checkpoint-sqlite`

Installed by:

```powershell
uv add langgraph-checkpoint-sqlite
```

This also brought in:

- `aiosqlite`
- `sqlite-vec`

## What Changed

### 1. Added checkpoint database path

Updated module:

- [paths.py](F:/AgentBot/agentbot/storage/paths.py)

New path helper:

- `checkpoints_path()`

New file path:

- `workspace/langgraph_checkpoints.db`

This keeps checkpoint storage separate from the application database:

- `workspace/agent_runtime.db`
- `workspace/langgraph_checkpoints.db`

### 2. Added LangGraph checkpoint helper module

New module:

- [checkpoints.py](F:/AgentBot/agentbot/graph/checkpoints.py)

Responsibilities:

- create a SQLite `SqliteSaver`
- call `setup()` on the saver
- provide a consistent `thread_config(thread_id)` helper
- detect whether a thread already has checkpoints

Main helpers:

- `sqlite_checkpointer()`
- `thread_config(thread_id)`
- `thread_has_checkpoints(checkpointer, thread_id)`

### 3. Graph builder now accepts an optional checkpointer

Updated module:

- [builder.py](F:/AgentBot/agentbot/graph/builder.py)

Change:

- `build_graph(llm, *, checkpointer=None)`

The graph is now compiled as:

```python
graph.compile(checkpointer=checkpointer)
```

This keeps the graph builder simple while allowing runtime code to decide whether checkpoint persistence should be active.

### 4. Sync runner now executes against a durable thread

Updated module:

- [runner.py](F:/AgentBot/agentbot/app/runner.py)

Key changes:

- opens a SQLite checkpointer for the run
- uses `conversation_id` as `thread_id`
- invokes the graph with `config={"configurable": {"thread_id": ...}}`
- detects whether the thread already has checkpoints

Runtime strategy:

- if checkpoints already exist for the conversation, send only the current user message into the graph
- if no checkpoints exist yet, seed the graph with:
  - system prompt
  - transcript history
  - current user message

This seeding fallback matters for migrated conversations:

- old conversation transcript may already exist in SQLite
- no checkpoint thread may exist yet
- first post-migration run needs one seed pass to preserve context

After that first checkpointed run, later runs resume from checkpoint state directly.

### 5. Streaming runner now uses the same checkpoint strategy

Updated module:

- [streaming_runner.py](F:/AgentBot/agentbot/app/streaming_runner.py)

Key changes:

- opens the SQLite checkpointer for each stream
- uses `thread_id = conversation_id`
- invokes `graph.stream(..., config=thread_config(thread_id))`
- uses the same transcript-seed fallback when no checkpoints exist yet

This keeps sync and streaming execution behavior aligned.

### 6. Primary-path metadata dependency cleanup

Updated module:

- [common.py](F:/AgentBot/agentbot/storage/common.py)

Change:

- moved `AGENTBOT_META_KEY` into shared storage helpers

This removed a primary-path dependency on the old JSONL conversation module from:

- [runner.py](F:/AgentBot/agentbot/app/runner.py)
- [streaming_runner.py](F:/AgentBot/agentbot/app/streaming_runner.py)
- [shadow_runtime.py](F:/AgentBot/agentbot/storage/shadow_runtime.py)

## Input Strategy After This Phase

The runtime now has two input modes per conversation thread.

### Mode A: Resume from checkpoints

Used when the thread already has checkpoint state.

Input sent to LangGraph:

- only the current user message

Why:

- LangGraph restores prior state from the thread
- avoids duplicating prior transcript into graph state

### Mode B: Seed from transcript

Used when the thread has no checkpoints yet.

Input sent to LangGraph:

- system prompt
- transcript history
- current user message

Why:

- preserves context for conversations created before checkpointing was enabled
- creates the first durable checkpoint chain for that conversation

## Verification Performed

### 1. Import verification

Verified these modules import successfully:

- `agentbot.graph.checkpoints`
- `agentbot.graph.builder`
- `agentbot.app.runner`
- `agentbot.app.streaming_runner`

### 2. Checkpointer initialization verification

Verified:

- `sqlite_checkpointer()` opens successfully
- `thread_config()` returns the expected LangGraph config shape
- `thread_has_checkpoints()` works against the SQLite saver

### 3. Minimal LangGraph checkpoint persistence smoke test

A small inline LangGraph state machine was executed twice against the same `thread_id`.

Observed result:

- first invocation returned `{'count': 1}`
- second invocation returned `{'count': 2}`
- `graph.get_state(config)` returned latest state `{'count': 2}`

This verifies that:

- state is persisted to SQLite
- a second invocation on the same thread resumes prior state

### 4. Frontend build verification

Command:

```powershell
cd ui
npm run build
```

Result:

- build passed

## Files Added Or Materially Changed

- [paths.py](F:/AgentBot/agentbot/storage/paths.py)
- [checkpoints.py](F:/AgentBot/agentbot/graph/checkpoints.py)
- [builder.py](F:/AgentBot/agentbot/graph/builder.py)
- [runner.py](F:/AgentBot/agentbot/app/runner.py)
- [streaming_runner.py](F:/AgentBot/agentbot/app/streaming_runner.py)
- [common.py](F:/AgentBot/agentbot/storage/common.py)

## What This Phase Did Not Do

This phase does not yet include:

- checkpoint inspection APIs
- exposing checkpoint history to the frontend
- interrupt/resume workflows
- human approval checkpoints
- removal of legacy JSONL modules from the repository

## Resulting Architecture State

After this phase, the main chat path now has all four intended layers:

1. conversation transcript in SQLite
2. run records in SQLite
3. run steps in SQLite
4. LangGraph thread checkpoints in SQLite

That closes the core runtime-model gap identified in the redesign.

## Recommended Next Step

The next practical step is:

- finish the run-oriented API surface and add historical run inspection endpoints needed by the execution UI

After that, the remaining large cleanup step is:

- remove legacy JSONL persistence code once migration safety is no longer needed
