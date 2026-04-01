# Browser Subgraph Phase 3: Action Migration Expansion

## Background

After the first Phase 3 step, the project already had:

- model-guided routing into browser mode
- file-based browser prompts
- browser planner input organized more like `browser-use`

The next planned step in Phase 3 was to expand the browser action surface further so the browser subgraph could handle more realistic browsing flows without changing the overall LangGraph structure.

This work started from three high-value actions taken directly from `browser-use` semantics:

- `read_content`
- `send_keys`
- `switch_tab`

Then it expanded further to cover the remaining high-value browser interaction actions that fit the current architecture cleanly:

- `close_tab`
- `get_dropdown_options`
- `select_dropdown_option`
- `scroll_to_text`
- `go_back`
- `screenshot`
- `save_as_pdf`
- `upload_file`

It also fixed an existing planner/executor mismatch for:

- `navigate(new_tab=...)`

## Goal

Extend the current browser subgraph with a much richer browser-use-aligned action surface while preserving the existing architecture:

- LangGraph remains the orchestration layer
- `browser-use` remains the browser execution/runtime layer
- planner output stays browser-use-style and converts into the project's own execution plan model

## What Was Implemented

### 1. Expanded browser planner and execution schema

Updated [browser.py](/F:/AgentBot/agentbot/models/browser.py).

The browser action system now includes:

- `switch_tab`
- `close_tab`
- `send_keys`
- `read_content`
- `get_dropdown_options`
- `select_dropdown_option`
- `scroll_to_text`
- `go_back`
- `screenshot`
- `save_as_pdf`
- `upload_file`

This change was applied consistently at both layers:

- `BrowserActionPlan`
- `BrowserPlannerAction`

The internal execution model now supports the required fields for this richer action set, including:

- `tab_id`
- `keys`
- `goal`
- `source`
- `context`
- `path`
- `file_name`
- `print_background`
- `landscape`
- `scale`
- `paper_format`
- `new_tab`

Validation rules were extended so invalid action payloads fail before execution.

### 2. Kept planner output aligned with browser-use-style JSON

Updated [browser.py](/F:/AgentBot/agentbot/models/browser.py).

The planner still emits the browser-use-style output envelope:

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `action`

Inside `action`, the project now supports browser-use-compatible single-action payloads for:

- `switch_tab`
- `close_tab`
- `send_keys`
- `read_content`
- `get_dropdown_options`
- `select_dropdown_option`
- `scroll_to_text`
- `go_back`
- `screenshot`
- `save_as_pdf`
- `upload_file`

This keeps the planner contract stable while letting the LangGraph side continue to convert that structured output into the local execution plan model.

### 3. Extended the runtime bridge payload

Updated [browser_runtime.py](/F:/AgentBot/agentbot/services/browser_runtime.py).

The subprocess bridge now forwards the fields required by the expanded action set, including:

- `tab_id`
- `keys`
- `goal`
- `source`
- `context`
- `path`
- `file_name`
- `print_background`
- `landscape`
- `scale`
- `paper_format`
- `new_tab`

This keeps the main graph process decoupled from `browser-use` internals while still allowing new actions to pass through cleanly.

### 4. Added browser-use worker support for the expanded action set

Updated [browser_worker.py](/F:/AgentBot/agentbot/browser_worker.py).

The worker now imports and executes these `browser-use` action models:

- `SwitchTabAction`
- `CloseTabAction`
- `SendKeysAction`
- `ReadContentAction`
- `GetDropdownOptionsAction`
- `SelectDropdownOptionAction`
- `ScreenshotAction`
- `SaveAsPdfAction`
- `UploadFileAction`

And maps them to the corresponding `browser-use` tool entrypoints:

- `tools.switch(...)`
- `tools.close(...)`
- `tools.send_keys(...)`
- `tools.read_long_content(...)`
- `tools.dropdown_options(...)`
- `tools.select_dropdown(...)`
- `tools.find_text(...)`
- `tools.go_back(...)`
- `tools.screenshot(...)`
- `tools.save_as_pdf(...)`
- `tools.upload_file(...)`

This is an important boundary detail:

- the project does **not** reuse `browser_use.agent.service.Agent`
- it only reuses the `browser-use` runtime/tooling layer

### 5. Extended planner prompt capability declarations

Updated [system_prompt_no_thinking.md](/F:/AgentBot/agentbot/prompts/browser/system_prompt_no_thinking.md).

The browser planner prompt now explicitly teaches the model when to use:

- `switch_tab`
- `close_tab`
- `send_keys`
- `read_content`
- `get_dropdown_options`
- `select_dropdown_option`
- `scroll_to_text`
- `go_back`
- `screenshot`
- `save_as_pdf`
- `upload_file`

It also includes the corresponding action payload examples, so the prompt and the actual execution surface stay aligned.

This keeps following the same principle as earlier browser iterations:

- do not declare actions the project cannot execute
- do declare the actions that are truly wired end-to-end

### 6. Preserved file-producing action results

Updated [browser.py](/F:/AgentBot/agentbot/models/browser.py) and [browser_worker.py](/F:/AgentBot/agentbot/browser_worker.py).

The browser action result model now preserves file-producing outputs more faithfully by retaining:

- `attachments`
- `images`

This matters for actions like:

- `screenshot`
- `save_as_pdf`

Without this, the action text might survive but the produced artifact path could be lost.

### 7. Fixed an existing planner/executor mismatch for navigation

Updated [browser.py](/F:/AgentBot/agentbot/models/browser.py), [browser_runtime.py](/F:/AgentBot/agentbot/services/browser_runtime.py), and [browser_worker.py](/F:/AgentBot/agentbot/browser_worker.py).

Before this slice, the planner schema already exposed:

- `navigate: {"url": "...", "new_tab": true|false}`

but the execution side always forced:

- `new_tab=False`

That mismatch has now been removed, and `navigate(new_tab=...)` is forwarded end-to-end.

## browser-use References Used

This slice referenced the `browser-use` implementation directly, especially:

- `F:\browser-use\browser_use\tools\views.py`
- `F:\browser-use\browser_use\tools\service.py`

The following semantics were intentionally mirrored:

- `SwitchTabAction(tab_id=...)`
- `CloseTabAction(tab_id=...)`
- `SendKeysAction(keys=...)`
- `ReadContentAction(goal=..., source=..., context=...)`
- `GetDropdownOptionsAction(index=...)`
- `SelectDropdownOptionAction(index=..., text=...)`
- `ScreenshotAction(file_name=...)`
- `SaveAsPdfAction(file_name=..., print_background=..., landscape=..., scale=..., paper_format=...)`
- `UploadFileAction(index=..., path=...)`

The worker-side tool calls also match the actual `browser-use` registered tool surface:

- switch action is executed through `tools.switch(...)`
- close tab is executed through `tools.close(...)`
- keyboard input is executed through `tools.send_keys(...)`
- long-form page reading is executed through `tools.read_long_content(...)`
- dropdown inspection is executed through `tools.dropdown_options(...)`
- dropdown selection is executed through `tools.select_dropdown(...)`
- history navigation is executed through `tools.go_back(...)`
- scroll-to-text is executed through `tools.find_text(...)`
- screenshot capture is executed through `tools.screenshot(...)`
- PDF export is executed through `tools.save_as_pdf(...)`
- file upload is executed through `tools.upload_file(...)`

## Validation

This slice was validated locally with:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. Planner output parsing checks
   - validate `read_content`, `switch_tab`, and `send_keys` payloads through `BrowserPlannerOutput`
   - validate `close_tab`, `get_dropdown_options`, `select_dropdown_option`, `scroll_to_text`, `screenshot`, `save_as_pdf`, `go_back`, `upload_file`, and `navigate(new_tab=true)` payloads through `BrowserPlannerOutput`
   - convert each parsed payload into `BrowserActionPlan`

These checks passed.

## Current Limitations

This slice does not port every single `browser-use` action.

Still intentionally out of scope for now are actions that are more tightly coupled to the code-use/file-authoring layer or need separate UX decisions:

- richer file-system authoring actions
- browser-use's full code-use workflow
- screenshot-in-next-observation UX beyond the current metadata passthrough

Also:

- `read_content` still depends on the extraction LLM being configured for the worker process
- `upload_file` assumes the local file path is explicitly known and available to the worker

## Outcome

At the end of this slice, the browser subgraph can now handle a much broader browser-use-style interaction surface without changing its high-level architecture:

- move between tabs
- close tabs
- use keyboard-driven interaction
- read long-form page content through `browser-use`
- inspect and operate dropdowns
- navigate back in history
- jump to visible text
- save screenshots
- export PDFs
- upload local files
- honor `navigate(new_tab=...)`

This is a strong next step in making the browser agent more browser-use-like while still keeping LangGraph in charge of orchestration.
