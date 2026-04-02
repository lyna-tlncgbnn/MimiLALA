# 2026-04-02 Streaming Terminal State Separation

## Background

The chat UI could show a contradictory state:

- final assistant content had already streamed successfully
- the same run was later rendered as `failed`
- a transport-level `network error` banner could remain visible alongside a successful persisted answer

This was not an execution-panel styling bug. It was a frontend streaming lifecycle bug.

## Root Cause

The frontend previously treated any exception from the streaming request as a run failure, even if the run had already reached a semantic terminal state.

That meant the following sequence could happen:

1. `assistant_final_delta` events stream normally
2. `assistant_finalized` arrives
3. the browser stream closes with a transport error
4. the client `catch` handler marks the active run as `failed`

So a transport problem during stream shutdown could incorrectly overwrite a successful run.

## Design Rule

Two concepts must remain separate:

1. **semantic run state**
   - started
   - completed
   - failed

2. **transport state**
   - stream open
   - stream closed
   - stream errored

A transport error is not automatically a run failure.

## Implementation

File:

- `ui/src/app/app-shell.tsx`

### 1. Added terminal semantic tracking inside the send flow

The send lifecycle now tracks:

- whether the run has semantically completed
- whether the server has emitted a semantic failure

This is done inside the `onSend` streaming scope rather than inferred later from UI state.

### 2. Catch logic now respects semantic terminal state

Before:

- any stream exception forced the current active run into `failed`

Now:

- if no semantic terminal event was seen, the transport error still becomes a user-visible failure
- if a semantic terminal event was already seen, the transport error no longer rewrites the run as failed

### 3. Finalization logic now keeps terminal semantics stable

During cleanup:

- completed runs are cleared out of local active state after query invalidation
- failed runs remain visible
- completed runs are no longer downgraded to failed during shutdown noise

### 4. Stream error clearing on successful terminal events

When these events arrive:

- `assistant_finalized`
- `run_completed`

the transient stream error state is cleared to avoid stale failure UI after a successful completion.

## Result

The frontend now follows the correct rule:

- semantic completion wins over late transport noise
- only pre-terminal stream failure is treated as run failure
- persisted successful transcript/runs are no longer shown next to a contradictory local failed state

## Verification

- `npm run build`
