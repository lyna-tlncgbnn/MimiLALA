# Frontend Cleanup Phase 4

## Summary

This phase intentionally did **not** continue the earlier constants-extraction direction.

After reviewing the current frontend structure and common React/Tailwind organization guidance, the cleanup focus was narrowed to:

- user-visible text corruption
- dead or noisy implementation details
- small readability improvements that do not change behavior

The goal was to keep the codebase easier to read without over-abstracting local layout decisions.

## Why This Direction Changed

The previous idea of aggressively extracting scattered literals into shared constants would have hurt readability in several places:

- local Tailwind layout values are often clearest in the component itself
- one-off copy does not benefit from indirection
- moving single-use values into shared files creates unnecessary file-hopping

For this codebase, the better rule is:

- centralize behavior/config values that have cross-file meaning
- keep local visual decisions local unless they form a real reusable token

## Changes Made

### 1. Fixed corrupted Chinese UI text

Repaired garbled user-facing text in:

- `ui/src/features/conversations/components/rename-dialog.tsx`
- `ui/src/features/settings/components/settings-dialog.tsx`
- `ui/src/features/chat/components/chat-composer.tsx`
- `ui/src/features/chat/components/run-steps-panel.tsx`

This restores readable labels, placeholders, status text, and explanatory copy.

### 2. Removed small implementation noise

- Simplified an import in `ui/src/features/chat/components/message-card.tsx`
- Removed an unnecessary `useMemo` in `ui/src/features/chat/components/run-steps-panel.tsx`
- Switched a few local event handlers in `ui/src/features/conversations/components/sidebar-panel.tsx` to named local functions for slightly cleaner effect blocks

None of these changes alter behavior.

## Validation

Validated with:

```powershell
cd ui
npm run build
```

The build completed successfully.

## Follow-up

Recommended next cleanup targets remain:

- `ui/src/features/chat/components/message-card.tsx`
- `ui/src/features/conversations/components/sidebar-panel.tsx`
- `ui/src/features/chat/components/run-steps-panel.tsx`

The preferred follow-up pattern is continued component/hook clarity work, not broad constants extraction.
