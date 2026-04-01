# Browser Subgraph Phase 2: Browser Task UI Integration

## Background

After browser mode became available in chat, the browser subgraph could already:

- start from the main chat graph
- stream summary events during execution
- return a final answer back to the assistant message

However, the frontend behavior was still weak:

- browser progress was shown by repeatedly overwriting one plain-text assistant message
- browser task details were not preserved as structured message data
- after the streaming phase ended, history reload did not retain a browser task summary

## Goal

Make browser execution visible in chat as structured message state rather than temporary text patches.

The target was:

- live browser progress remains readable
- browser task result survives conversation reload
- browser task summary is attached to assistant messages as metadata

## What Was Implemented

### 1. Attached browser task metadata to assistant messages

Updated [nodes.py](/F:/AgentBot/agentbot/graph/nodes.py).

The browser wrapper node now stores browser execution result data in:

- `AIMessage.additional_kwargs["browser_task"]`

The stored payload includes:

- `task`
- `status`
- `final_response`
- `error_message`
- `current_url`
- `page_title`
- `step_count`
- `steps`

This means browser-task-specific state is now part of the assistant message payload itself.

### 2. Exposed browser task metadata through the API layer

Updated [conversations.py](/F:/AgentBot/agentbot/services/conversations.py).

When assistant messages are serialized for the frontend, `browser_task` is now included if present.

This allows browser task summaries to survive:

- stream completion
- conversation refetch
- later history reload

### 3. Extended frontend chat message types

Updated [api.ts](/F:/AgentBot/ui/src/shared/api/api.ts).

`ChatMessage` now supports an optional `browser_task` payload.

This keeps browser task state typed and available both for:

- live streaming updates
- persisted history rendering

### 4. Reworked live browser progress handling

Updated [app-shell.tsx](/F:/AgentBot/ui/src/app/app-shell.tsx).

Instead of only overwriting assistant text on every browser event, the streaming handler now:

- maintains a structured `browser_task` object on the active assistant message
- updates page title and URL during observation
- appends planned steps
- fills step results when action execution completes
- sets final browser status on completion or failure

A helper now generates readable assistant text from the current browser task state, so the UI remains understandable while still preserving structure.

### 5. Rendered browser task summaries in message cards

Updated:

- [message-list.tsx](/F:/AgentBot/ui/src/features/chat/components/message-list.tsx)
- [message-card.tsx](/F:/AgentBot/ui/src/features/chat/components/message-card.tsx)

Assistant messages with browser metadata now render a dedicated browser task summary block showing:

- browser task status
- original browser task text
- page title
- current URL
- executed step list

This summary appears not only during streaming, but also after the conversation is reloaded from history.

## Validation

This iteration was validated with:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. frontend production build
   - `npm run build`

3. local serialization sanity check
   - serialize an assistant message carrying `browser_task`
   - confirm the API payload includes browser task metadata

## Outcome

At the end of this iteration:

- browser task progress in chat is no longer just a transient text overwrite
- browser task state is carried as structured assistant-message metadata
- browser execution summaries remain visible after history reload

This makes browser mode feel much more like a first-class chat capability instead of a temporary streaming side effect.
