# Conversation Run List Reorg Phase 3

Date: 2026-04-04

## Goal

Break down the oversized `conversation-run-list.tsx` container into smaller feature-local components and utility modules without changing behavior.

## Why This Step Was Needed

Before this step, `conversation-run-list.tsx` contained:

- empty state prompt content
- timestamp formatting
- payload stringification
- historical run step mapping
- active run step mapping
- user prompt UI
- agent answer wrapper UI
- execution hint UI
- historical run section UI
- active run section UI
- final list composition

This made the file both a renderer and a local feature framework at the same time.

## Changes

Added utility module:

- `ui/src/features/chat/lib/conversation-run-list-utils.ts`

Added components:

- `ui/src/features/chat/components/user-prompt.tsx`
- `ui/src/features/chat/components/agent-section.tsx`
- `ui/src/features/chat/components/execution-hint.tsx`
- `ui/src/features/chat/components/historical-run-section.tsx`
- `ui/src/features/chat/components/active-run-section.tsx`
- `ui/src/features/chat/components/conversation-empty-state.tsx`

Updated:

- `ui/src/features/chat/components/conversation-run-list.tsx`

## Result

`conversation-run-list.tsx` is now primarily a composition container:

- derive sorted runs
- map transcript messages by id
- decide whether to show empty state, historical runs, active run, and error
- delegate rendering to smaller subcomponents

The step mapping and format helpers are now feature-local utilities instead of inline functions.

## Validation

Build verification executed:

- `npm run build`

Build passed.
