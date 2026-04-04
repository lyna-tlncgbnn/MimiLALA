# Rich Content Rendering

## Overview

The frontend now treats agent answer rendering as a dedicated rich content system instead of a thin markdown parser hookup.

Primary renderer entry points:

- `ui/src/features/chat/components/message-content.tsx`
- `ui/src/features/chat/renderers/rich-content-renderer.tsx`
- `ui/src/features/chat/renderers/markdown-renderer.tsx`
- `ui/src/features/chat/renderers/code-block.tsx`
- `ui/src/features/chat/renderers/markdown-theme.css`

## Rendering Modes

The renderer currently keeps two explicit content modes:

- `plain`
- `markdown`

Usage policy:

- assistant final answers use `markdown`
- user messages use `plain`
- tool outputs and run-step detail remain `plain` for now

This avoids over-parsing execution logs while allowing the main assistant answer to be rendered richly.

## Markdown Pipeline

The markdown pipeline is built with:

- `react-markdown`
- `remark-gfm`
- `remark-math`
- `rehype-katex`
- `rehype-highlight`

This enables:

- headings
- paragraphs
- lists
- blockquotes
- tables
- task lists
- footnotes
- inline code
- fenced code blocks
- inline math
- block math
- links
- images

## Code Block Rendering

Code blocks are no longer displayed with only browser-default `<pre><code>` styling.

A dedicated `CodeBlock` component is responsible for:

- language label
- copy button
- dark code surface
- horizontal scrolling
- syntax-highlight token styling

## Streaming Tolerance

The chat pipeline renders assistant content while SSE deltas are still arriving.
That means markdown may be incomplete at intermediate states.

To keep the UI resilient:

- markdown rendering is wrapped in an error boundary
- renderer failures temporarily fall back to plain text
- later content updates can recover rich rendering automatically

This is especially relevant for unfinished math, code fences, or other partially streamed constructs.

## Security Boundary

The renderer intentionally keeps a conservative safety boundary:

- raw HTML is not enabled
- `rehype-raw` is not used
- links still pass through `react-markdown`'s default safe `urlTransform`
- external links open in a new tab with `noopener noreferrer`

## Validation Surface

A dedicated local validation page is available at:

- `#/dev/render-lab`

This page is used to verify:

- typography
- tables
- code blocks
- math
- footnotes
- images

## Current Limitations

Not included in this phase:

- raw HTML rendering
- Mermaid diagrams
- artifact-specific rich preview
- dedicated JSON / diff renderer for tool output

Those should be added as separate capabilities instead of overloading the assistant answer renderer.
