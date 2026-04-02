# Agent Runtime Redesign Phase 5 Frontend Run-Centric UI

Date: `2026-04-02`

## Summary

This step rebuilt the chat frontend from a flat message-list UI into a run-centric conversation view.

After this change:

- the main chat area is no longer driven by a single `messages + liveMessages` model
- transcript history and execution process are rendered as separate UI concerns
- active execution is shown as an explicit run panel
- historical runs can be expanded to inspect persisted steps
- tool activity is no longer rendered as ordinary chat bubbles

This is the frontend counterpart to the earlier storage and API redesign.

## Why The Old UI Had To Be Replaced

The old frontend assumed:

- the conversation is just a list of messages
- live execution can be simulated by appending temporary message bubbles
- tool activity can be represented as assistant/tool messages in the same stream

That model broke once the backend changed to:

- transcript messages
- runs
- run steps
- run-oriented SSE events

The frontend had to be rebuilt around the same model, otherwise it would continue reconstructing product UI from the wrong primitive.

## Design Direction

This implementation intentionally separates:

1. transcript view
2. active run view
3. historical run-step inspection

That direction is consistent with:

- LangGraph persistence guidance, which separates thread/checkpoint state from transcript presentation
- OpenAI structured response/reasoning guidance, which separates final output from tool and reasoning items
- Anthropic tool-use guidance, which treats tool use and tool results as structured blocks rather than plain chat text

Reference material consulted during this step:

- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use)

The visual direction was also aligned to the reference screenshots:

- muted "thinking finished / thinking" header
- vertical timeline for process steps
- collapsible process detail
- final answer visually separated from the process list

## What Changed

### 1. App state moved from `liveMessages` to `activeRun`

Updated file:

- [app-shell.tsx](F:/AgentBot/ui/src/app/app-shell.tsx)

Old model:

- persisted transcript messages
- temporary assistant/tool bubbles in `liveMessages`

New model:

- persisted transcript from `GET /api/conversations/{id}`
- persisted runs from `GET /api/conversations/{id}/runs`
- ephemeral active run state driven by run-oriented SSE

New frontend state shape:

- `activeRun`
- `streamPhase`
- transcript query
- conversation runs query

This is the key architectural change in the frontend.

### 2. Streaming event handling now updates run state instead of message bubbles

Updated file:

- [app-shell.tsx](F:/AgentBot/ui/src/app/app-shell.tsx)

Handled SSE events:

- `run_started`
- `step_started`
- `step_completed`
- `assistant_final_delta`
- `assistant_finalized`
- `run_completed`
- `run_failed`

Behavior:

- `run_started` creates or updates the active run shell
- `step_started` / `step_completed` mutate the active run timeline
- `assistant_final_delta` builds the final assistant text incrementally
- `assistant_finalized` seals the final answer
- on completion the app refreshes transcript + run list queries
- active run state is cleared after successful persistence refresh

### 3. Chat panel now renders a run-centric conversation view

Updated file:

- [chat-panel.tsx](F:/AgentBot/ui/src/features/chat/layout/chat-panel.tsx)

Old child component:

- `MessageList`

New child component:

- `ConversationRunList`

New ChatPanel inputs:

- `messages`
- `runs`
- `activeRun`
- `loadingHistory`
- `loadingRuns`

This reflects the new dual-read-model approach:

- transcript data
- execution data

### 4. Added a new run-centric conversation renderer

New file:

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)

Responsibilities:

- render empty state
- render historical runs in chronological order
- map transcript messages to each run using `user_message_id` and `final_message_id`
- render the active run separately while it is in progress
- load historical step details on demand

Important behavior:

- historical run steps are not fetched eagerly for every run
- step details are requested only when the user expands a run's process section

This keeps the UI scalable and avoids turning every conversation open into a burst of run-step requests.

### 5. Added a dedicated process timeline component

New file:

- [run-steps-panel.tsx](F:/AgentBot/ui/src/features/chat/components/run-steps-panel.tsx)

Responsibilities:

- render process header such as:
  - `正在思考`
  - `已完成思考，N 个步骤`
  - `运行失败`
- render vertical timeline step list
- show running/completed/failed status visually
- support collapsing and expanding
- show optional step detail cards

The detail card can surface:

- step summary
- input payload preview
- output payload preview

This is the main UI replacement for the old tool-bubble model.

### 6. Added explicit frontend types for runs and run steps

Updated file:

- [api.ts](F:/AgentBot/ui/src/shared/api/api.ts)

Added:

- `RunSummary`
- `RunStep`
- `RunStepsDetail`
- `ConversationRunsDetail`
- `listConversationRuns(conversationId)`
- `getRunSteps(runId)`

Also updated transcript message typing:

- `ChatMessage` now includes optional `run_id`

This gives the frontend a stable typed contract for grouping transcript and execution history.

### 7. Tool bubble rendering is no longer part of the active chat path

The new UI no longer depends on:

- synthetic tool messages in the live stream
- assistant message cards that double as execution traces

The old message-oriented components still exist in the repository, but they are no longer the primary renderer for the chat screen.

## Resulting UI Model

Each conversation is now rendered as a sequence of runs.

Each historical run can contain:

- the user message
- a collapsed execution section
- the final assistant answer

The active run contains:

- the current user input
- an expanded execution section while streaming
- the final assistant answer buffer as it is being produced

This matches the target product behavior much more closely than the old flat message list.

## Verification Performed

### Frontend build verification

Command:

```powershell
cd ui
npm run build
```

Result:

- TypeScript build passed
- Vite production build passed

### Backend compatibility verification

Verified imports still succeed for:

- `agentbot.api.schemas`
- `agentbot.api.serializers`
- `agentbot.api.routes.conversations`
- `agentbot.api.routes.runs`

This matters because the frontend now depends on the new transcript/run API contracts.

## Files Added Or Materially Changed

- [app-shell.tsx](F:/AgentBot/ui/src/app/app-shell.tsx)
- [chat-panel.tsx](F:/AgentBot/ui/src/features/chat/layout/chat-panel.tsx)
- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)
- [run-steps-panel.tsx](F:/AgentBot/ui/src/features/chat/components/run-steps-panel.tsx)
- [types.ts](F:/AgentBot/ui/src/features/chat/types.ts)
- [api.ts](F:/AgentBot/ui/src/shared/api/api.ts)
- [schemas.py](F:/AgentBot/agentbot/api/schemas.py)
- [serializers.py](F:/AgentBot/agentbot/api/serializers.py)

## What This Step Did Not Do

This step does not yet include:

- a separate dedicated run inspector page
- artifact preview cards
- step-count summaries returned directly from the backend run list API
- visual replay of checkpoint history
- cleanup/deletion of legacy message-oriented chat components

## Recommended Next Step

The next practical frontend step is:

- add richer historical run summaries from backend metadata so collapsed runs can show better labels without fetching steps first

The next cleanup step is:

- remove or retire the old message-oriented chat components once the new run-centric UI is accepted as the primary product direction
