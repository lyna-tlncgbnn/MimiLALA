# Agent Runtime Redesign Phase 5 UI Hierarchy Refinement

Date: `2026-04-02`

## Summary

This step refined the run-centric chat UI to better match the intended agent interaction model.

The updated hierarchy is now:

1. user input
2. `Agent` section header
3. execution section
4. final answer content

This keeps `Agent` as the primary container while preserving the runtime logic that execution happens before the final answer is produced.

## Problems Addressed

The previous revision still had four UI problems:

1. execution and answer hierarchy was not aligned with the runtime order
2. the execution area could still feel too detached from the `Agent` section
3. the assistant and user blocks still carried too much card styling
4. the final answer did not feel clearly incremental while streaming

## What Changed

### 1. `Agent` became the parent section

Updated file:

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)

New structure:

- user prompt
- `Agent` header
- execution subsection
- final answer subsection

This creates one coherent `Agent` region instead of making the answer and execution feel like separate top-level blocks.

### 2. execution now appears before the final answer

Updated file:

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)

New order inside `Agent`:

1. execution
2. final answer

This matches the intended runtime mental model:

- first the agent executes tools and intermediate steps
- then the final answer is produced

### 3. final answer area remains streamable

Updated file:

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)

Behavior:

- the `Agent` section appears even while the answer is still being generated
- the final answer text area stays mounted
- `assistant_final_delta` can continue filling the final answer region incrementally

This preserves the intended streaming behavior for the final answer while keeping execution non-streaming and step-based.

### 4. user and assistant visuals were softened further

Updated file:

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)

Changes:

- removed the black user bubble
- user prompt is now a lighter right-aligned text block
- assistant area is now a lightweight content section rather than a bordered white card

Result:

- less “chat demo” feeling
- less toy-like card styling
- more document-flow / workspace feel

### 5. execution remains subordinate but no longer detached

Updated files:

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)
- [run-steps-panel.tsx](F:/AgentBot/ui/src/features/chat/components/run-steps-panel.tsx)

Behavior:

- execution is still visually secondary
- it is indented under the `Agent` section
- it appears before the final answer
- it is hidden entirely when there are no visible steps

This gives the runtime order without bringing back the old “large timeline block competing with the answer” problem.

## Resulting UI Rules

After this refinement, the frontend follows these rules:

1. `Agent` is the primary section title for a run.
2. Execution is shown inside the `Agent` section.
3. Execution appears before the final answer.
4. The final answer is the bottom output region and can stream incrementally.
5. No execution panel is shown when there are no visible steps.
6. User and assistant surfaces avoid heavy card styling.

## Verification

Command run:

```powershell
cd ui
npm run build
```

Result:

- TypeScript build passed
- Vite production build passed

## Files Changed

- [conversation-run-list.tsx](F:/AgentBot/ui/src/features/chat/components/conversation-run-list.tsx)
- [run-steps-panel.tsx](F:/AgentBot/ui/src/features/chat/components/run-steps-panel.tsx)
- [agent-runtime-redesign.md](F:/AgentBot/docs/architecture/agent-runtime-redesign.md)

## Next Step

The next useful refinement would be:

- replace the generic collapsed `查看执行` affordance with a backend-provided run summary so historical runs are informative even before expansion
