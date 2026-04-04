# Frontend API Layer Reorg Phase 1

Date: 2026-04-04

## Goal

Start the frontend organization refactor with the lowest-risk structural step:

- split the oversized shared API module
- introduce feature-local API modules
- centralize query keys
- keep runtime behavior unchanged

## Why This Step Came First

The main structural pressure points in the frontend were:

- `ui/src/app/app-shell.tsx`
- `ui/src/shared/api/api.ts`
- large chat container components importing a mixed API barrel

Among those, `shared/api/api.ts` was the safest piece to split first because it mostly affected module boundaries, not visible behavior.

## Changes

Added:

- `ui/src/app/config/env.ts`
- `ui/src/shared/api/http-client.ts`
- `ui/src/shared/api/sse.ts`
- `ui/src/features/conversations/api/conversations-api.ts`
- `ui/src/features/conversations/api/conversations-query-keys.ts`
- `ui/src/features/conversations/api/conversations-schemas.ts`
- `ui/src/features/chat/api/chat-api.ts`
- `ui/src/features/chat/api/chat-query-keys.ts`
- `ui/src/features/chat/api/chat-schemas.ts`

Updated:

- `ui/src/app/app-shell.tsx`
- `ui/src/features/chat/components/conversation-run-list.tsx`
- `ui/src/features/chat/components/message-body-utils.ts`
- `ui/src/features/chat/components/message-card.tsx`
- `ui/src/features/chat/components/message-list.tsx`
- `ui/src/features/chat/components/standard-message-body.tsx`
- `ui/src/features/chat/layout/chat-panel.tsx`

## Resulting Structure

### Shared transport

- `http-client.ts` now owns regular JSON requests
- `sse.ts` now owns streaming event transport

### Feature API

- conversations feature owns its own summary schema, endpoints, and query keys
- chat feature owns transcript/run schemas, streaming API, and run-related query keys

### Query invalidation

`app-shell.tsx` no longer uses raw string array literals for the core conversation and run caches.
It now references:

- `conversationsQueryKeys`
- `chatQueryKeys`

This makes cache operations more stable and easier to audit.

## Compatibility Note

`ui/src/shared/api/api.ts` remains as a temporary barrel export layer so the migration can continue incrementally without forcing every consumer to move in one pass.

The intended end state is to remove that barrel after all direct callers are migrated.

## Validation

Build verification executed:

- `npm run build`

Build passed.

## Next Step

The next reorganization target should be `ui/src/app/app-shell.tsx`, by extracting:

- page-level orchestration hook
- streaming run state handling
- query/mutation wiring

That step should reduce the current controller density without mixing it with transport-level refactors.
