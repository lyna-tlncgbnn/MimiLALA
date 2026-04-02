# 2026-04-02 Execution Panel Collapsible Timeline Rebuild

## Background

The earlier execution-panel rewrite fixed the high-level content order, but the visual structure was still off:

- it still looked like a stack of rounded cards instead of a timeline
- the left-side dots and connectors were decorative rather than structural
- expand/collapse behavior was partially hand-rolled
- some UI copy in the chat components was still garbled

That meant the gap from the reference design was still mainly structural, not cosmetic.

## Goal

Rebuild the execution panel as a proper collapsible timeline:

1. the execution header acts as the panel trigger
2. each step is rendered as a timeline disclosure row
3. detail content expands inline under the matching step
4. the existing `Agent -> execution -> final answer` information order remains unchanged
5. adjacent chat UI copy is normalized to clean UTF-8 text

## Dependency Change

Added:

- `@radix-ui/react-collapsible`

Reason:

- the project already uses Radix primitives
- disclosure behavior is more reliable with a headless primitive than with custom state wiring

## Code Changes

### 1. Rebuilt `RunStepsPanel`

File:

- `ui/src/features/chat/components/run-steps-panel.tsx`

New structure:

- top-level execution section uses `Collapsible.Root`
- each step uses its own `Collapsible.Root`
- the timeline is rendered with explicit dot/connector elements
- detail panels expand inline under the selected row

### 2. Rebuilt `ConversationRunList`

File:

- `ui/src/features/chat/components/conversation-run-list.tsx`

Adjusted:

- removed extra execution-panel indentation
- kept `Agent` as the parent container
- made historical runs and active runs use the same execution-panel component
- normalized visible UI labels to readable Chinese

## Follow-up Refinement

After the first rebuild, two additional issues were fixed:

1. historical runs now collapse back to the original `查看执行` hint instead of keeping a collapsed timeline header
2. the execution header no longer renders its own timeline dot and connector, so the opened state does not show a duplicated left-side axis

This makes the collapsed and expanded states behave as two intentionally different views:

- collapsed: lightweight execution hint
- expanded: actual timeline

## Result

The execution panel now follows these rules:

- collapsed historical runs show `查看执行`
- expanded state renders only one timeline axis for actual steps
- step rows behave like disclosure rows, not message cards
- final answer still appears below execution in the `Agent` section

## Docs Updated

- `docs/architecture/agent-runtime-redesign.md`

## Verification

- `npm install @radix-ui/react-collapsible`
- `npm run build`

## Additional Visual Refinement

The timeline styling was tightened again after the initial rebuild:

- step timestamps were removed to avoid wasting a full extra line on each tool step
- left-side timeline dots were changed from hollow markers to filled markers
- disclosure arrows now sit directly after the header text instead of floating at the far right edge
- step rows no longer use rounded card-like containers
- expanded detail content now reads as an indented inline detail block instead of a separate card

This keeps the execution area closer to a process list than a stack of UI panels.

The layout was then tightened further:

- timeline dot, step icon, and label now share a stricter alignment baseline
- vertical spacing between step rows was reduced to make the execution list denser
- execution header and step labels were shifted toward a softer gray hierarchy so they read as secondary process information rather than primary content
