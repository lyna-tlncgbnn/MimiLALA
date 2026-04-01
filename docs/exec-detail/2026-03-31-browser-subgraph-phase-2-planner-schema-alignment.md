# Browser Subgraph Phase 2: Planner Schema Alignment

## Background

After browser chat integration and browser event streaming were connected, the browser task could already:

- enter from the main chat graph
- start a real local browser
- navigate to the requested page

But the planner layer still failed intermittently with validation errors.

The visible symptom was:

- the browser actually opened and navigated
- the chat UI showed partial browser progress
- the graph then failed during planner output parsing

## Root Cause

The root problem was not a missing field patch. It was a **schema mismatch between three layers**:

1. the browser-use style prompt
2. the model provider's structured output behavior
3. this project's internal execution action schema

At that point, the project prompt had already moved toward browser-use style instructions, but the planner still expected the model to emit this custom internal shape:

- `action_type`
- `reason`
- `final_response`

In practice, the model was returning a browser-use style shape instead, for example:

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `action`
- `done.text`

That meant the model output was semantically reasonable, but it was being validated against the wrong schema.

So the actual issue was:

**prompt semantics and planner schema were out of alignment.**

## What Was Changed

### 1. Introduced a browser-use style planner output model

Updated [browser.py](/F:/AgentBot/agentbot/models/browser.py).

Instead of forcing the model to emit the internal execution schema directly, the browser planner now uses:

- `BrowserPlannerOutput`
- `BrowserPlannerAction`

These models are intentionally closer to browser-use output:

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `action: [...]`

And each action item supports one browser-use style action payload such as:

- `navigate`
- `click`
- `input`
- `scroll`
- `wait`
- `extract`
- `search_page`
- `find_elements`
- `done`

### 2. Added an explicit conversion layer

Still in [browser.py](/F:/AgentBot/agentbot/models/browser.py), `BrowserPlannerAction` now exposes:

- `to_execution_plan(reason: str) -> BrowserActionPlan`

This conversion is the key boundary:

- planner output stays browser-use shaped
- runtime execution still uses the project's internal `BrowserActionPlan`

This keeps the execution layer stable without forcing the planner prompt to speak a non-native schema.

### 3. Updated browser planner node to use the new schema

Updated [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py).

The planner node no longer does:

- `with_structured_output(BrowserActionPlan)`

It now does:

- `with_structured_output(BrowserPlannerOutput)`

Then it converts the first planner action into the internal execution action before writing to graph state.

### 4. Rewrote the browser subgraph prompt to match the planner schema

Updated [browser_subgraph.py](/F:/AgentBot/agentbot/prompts/browser_subgraph.py).

The prompt now explicitly defines a browser-use style JSON object with:

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `action`

and clearly constrains:

- exactly one action object
- exactly one action key per action object
- only the local supported action names

This means prompt, model output, and validation schema are now aligned.

## Why This Fix Is Better

This was not just a validation workaround.

It fixes the architectural mismatch at the source:

- browser-use style prompt now produces browser-use style output
- the project no longer asks the model to jump straight into an internal execution schema
- the internal execution schema remains available where it belongs: at the executor boundary

In short:

**planner schema and executor schema are now separated cleanly.**

## Validation

This fix was validated in three ways:

1. Python compile check
   - `.\.venv\Scripts\python.exe -m compileall agentbot`

2. local model-shape validation
   - validate a browser-use style `done` payload through `BrowserPlannerOutput`
   - convert it into `BrowserActionPlan`

3. real end-to-end browser chat test
   - `/browser 打开 https://example.com 然后告诉我页面标题`
   - browser opened successfully
   - planner no longer failed on `action_type` / `reason` validation mismatch

## Outcome

At the end of this iteration:

- browser mode in chat works end-to-end for the validated scenario
- the planner no longer depends on a mismatched custom schema
- the browser subgraph prompt is now structurally consistent with the model output it expects

This closes the most important planner-side integration bug in Phase 2.
