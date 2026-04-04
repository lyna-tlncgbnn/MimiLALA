# Frontend App Shell Reorg Phase 2

Date: 2026-04-04

## Goal

Reduce the controller density of `ui/src/app/app-shell.tsx` without changing visible behavior.

## Why This Step Was Needed

Before this step, `app-shell.tsx` combined:

- route handling
- query wiring
- mutations
- cache invalidation
- sidebar UI coordination
- draft state
- streaming run state
- error handling
- page assembly

That made it the heaviest orchestration file in the frontend and the next major barrier to further cleanup.

## Changes

Added:

- `ui/src/features/chat/hooks/use-conversation-screen.ts`
- `ui/src/features/chat/lib/active-run-state.ts`

Updated:

- `ui/src/app/app-shell.tsx`

## New Responsibilities

### `use-conversation-screen.ts`

This hook now owns the page-level orchestration for the conversation screen:

- route-derived conversation selection
- React Query reads
- create / rename / delete conversation mutations
- sidebar and dialog coordination through UI store
- draft state
- send flow
- stream lifecycle state
- final error composition

### `active-run-state.ts`

This module now owns the run-state transition helpers:

- active step upsert logic
- initial pending run creation
- stream event to active-run transition mapping

This keeps the event-driven state evolution out of the page component itself.

### `app-shell.tsx`

`app-shell.tsx` is now reduced to a thin assembly layer:

- call `useConversationScreen`
- wire returned props into `SidebarPanel`, `ChatPanel`, `SettingsDialog`, and `RenameDialog`

## Outcome

This step does not yet fully complete the front-end reorganization, but it creates a much better base for the next cleanup stages:

- extracting feature hooks
- consolidating constants
- simplifying large feature components

## Validation

Build verification executed:

- `npm run build`

Build passed.
