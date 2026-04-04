# Rich Markdown Renderer Upgrade

Date: 2026-04-04

## Goal

Upgrade agent answer rendering from a lightly styled markdown parser hookup into a reusable rich content renderer for the desktop chat UI.

## Why This Change Was Needed

Before this change, the frontend already parsed assistant answers with `react-markdown` and `remark-gfm`, but the experience still felt close to plain text because:

- only a small subset of markdown tags had custom rendering
- tables had no dedicated visual treatment
- code blocks had no language header or copy affordance
- math was unsupported
- there was no isolated validation surface for renderer behavior

As a result, users could not easily tell whether a weak rendering result came from:

- the model not emitting valid markdown
- or the frontend not presenting markdown in a strong enough way

## Scope

Included in this phase:

- renderer subsystem extraction
- GFM support carried into a complete renderer path
- math rendering with KaTeX
- syntax-highlighted code blocks
- copy interaction for code blocks
- markdown-specific visual theme
- streaming-safe fallback behavior
- render lab validation route
- architecture documentation for the renderer

Not included:

- raw HTML rendering
- Mermaid support
- artifact-specific renderers
- JSON / diff specialized viewers

## Implementation Summary

New renderer files:

- `ui/src/features/chat/renderers/rich-content-renderer.tsx`
- `ui/src/features/chat/renderers/markdown-renderer.tsx`
- `ui/src/features/chat/renderers/code-block.tsx`
- `ui/src/features/chat/renderers/render-utils.tsx`
- `ui/src/features/chat/renderers/markdown-theme.css`

Updated integration points:

- `ui/src/features/chat/components/message-content.tsx`
- `ui/src/app/main.tsx`
- `ui/src/app/App.tsx`

New validation page:

- `ui/src/app/render-lab-page.tsx`

## Dependency Changes

Added:

- `remark-math`
- `rehype-katex`
- `katex`
- `rehype-highlight`
- `highlight.js`

## Renderer Behavior

Current content policy:

- assistant body -> markdown renderer
- user body -> plain renderer
- tool output -> plain renderer
- run-step detail -> plain renderer

This keeps the assistant answer expressive while preserving the readability of execution logs.

## Streaming Resilience

Because assistant content is assembled from streamed SSE deltas, markdown can be incomplete mid-render.

To avoid renderer failures breaking the conversation view:

- markdown rendering is wrapped in an error boundary
- a broken intermediate render falls back to plain text
- later deltas can recover the rich renderer automatically

## Validation

Validation route added:

- `#/dev/render-lab`

Build verification performed:

- `npm run build`

The build completed successfully.

## Visual Tuning Follow-up

After the first renderer pass, the code block and table presentation still felt visually heavier than the rest of the chat surface.

A follow-up tuning pass adjusted:

- code block background from dark to light
- code block toolbar density
- copy button size
- code font size
- table font size
- table cell padding
- heading spacing
- inline code size

The purpose of this pass was not to change rendering behavior, but to bring markdown visuals back into the same lightweight surface language as the surrounding chat UI.

## Follow-up Risks

### Bundle Size

KaTeX increases client bundle size noticeably.
This is acceptable for the current phase, but future optimization may include:

- route-level code splitting
- more selective renderer resource loading

### Tool Output Rendering

Tool output and run-step detail still use plain rendering.
If the product later needs rich previews for:

- markdown tool output
- JSON
- diffs
- generated documents

then those should be added as dedicated renderer modes rather than folded into the assistant markdown renderer.
