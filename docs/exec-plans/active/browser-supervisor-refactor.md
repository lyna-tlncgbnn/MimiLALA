# Browser Supervisor Refactor Plan

## Status

ACTIVE

## Why This Refactor Exists

The current browser integration is functionally usable, but the orchestration shape is wrong for a real agent experience.

Today the graph does this:

- `START -> entry -> (browser or route) -> chatbot/tools`

That means browser delegation is decided **before** the main chat agent runs. In practice, this creates a brittle behavior pattern:

- weak or indirect browser intent is easy to miss
- the router only sees a single-turn classification problem
- the main chat agent cannot reason over full conversational context before delegation
- when routing misses, the chat agent may answer as if browser capability is unavailable

This is exactly the failure mode we observed in chat.

## Architecture Decision

We will replace the current **pre-chat router-first architecture** with a **main-agent-first supervisor architecture**.

Target principle:

- every turn enters the main agent first
- the main agent decides whether to answer directly, call normal tools, or delegate to the browser subgraph
- browser execution remains implemented as a LangGraph subgraph
- browser execution does **not** become a normal chat tool
- we intentionally avoid fallback-heavy hard-coded intent routing

This is aligned with the official LangChain / LangGraph multi-agent guidance:

- subagents: centralized control should live in the main agent, not a separate classifier  
  Source: [Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents)
- router pattern is a different pattern from supervisor/subagents  
  Source: [Multi-agent Overview](https://docs.langchain.com/oss/python/langchain/multi-agent)
- if nested graph visibility matters, calling subgraphs from graph nodes is preferable to hiding them inside tool wrappers  
  Source: [Use subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)

Inference from those sources:

- our current "route first, then maybe browser" design is closer to a router pattern
- the product behavior we now want is a supervisor pattern
- because we care about browser step streaming and graph visibility, we should keep browser execution as a node/subgraph, not collapse it into a plain tool wrapper

## Refactor Goal

Build a new main graph where:

1. all user turns enter the main agent first
2. the main agent produces a structured orchestration decision
3. that decision routes the turn to one of:
   - direct response
   - normal tool execution
   - browser subgraph delegation
4. the browser subgraph returns results to the main agent
5. the main agent produces the final user-facing answer

This changes browser delegation from:

- "classifier dispatch before the main agent"

to:

- "main agent decides whether to delegate"

## Target Graph Shape

Current shape:

```text
START
  -> entry
  -> route/browser
  -> chatbot
  -> tools
  -> END
```

Target shape:

```text
START
  -> supervisor
  -> (chatbot_response | tools | browser_subgraph)
  -> supervisor
  -> END
```

More concretely:

```text
START
  -> supervisor

supervisor
  -> respond
  -> tools
  -> browser

tools
  -> supervisor

browser
  -> supervisor

respond
  -> END
```

This makes the main agent the orchestrator for the whole turn.

## What Will Be Removed

The following concepts should be removed rather than patched around:

- entry-time browser routing as the main decision point
- the dedicated pre-chat `route` classifier node
- hard-coded browser intent rules as a primary orchestration mechanism
- wording in prompts that implies browser delegation happens somewhere outside the main agent

We may still keep explicit `/browser` semantics only if they are modeled as **instructional context for the supervisor**, not as a separate pre-router.

But the default design target is:

- no separate router gate in front of the main agent

## New Core Concept: Supervisor Decision

Introduce a structured decision model for the supervisor node, for example:

```json
{
  "decision": "respond",
  "reason": "I can answer directly.",
  "response": "..."
}
```

```json
{
  "decision": "tools",
  "reason": "A standard tool is needed first."
}
```

```json
{
  "decision": "browser",
  "reason": "This requires live browser interaction.",
  "browser_task": "Open the target site and extract the requested information."
}
```

Key principle:

- the supervisor is not just classifying
- it is choosing the next orchestration action

This is broader and more capable than the current `chat/browser` router schema.

## Proposed State Model Changes

The main graph state should move from "messages plus optional router metadata" toward "messages plus orchestration state".

Recommended main state additions:

- `supervisor_decision`
- `delegation_reason`
- `active_subagent`
- `browser_task_request`
- `browser_task_result`
- `last_tool_result_summary`

We should keep message history as the main conversational backbone, but orchestration metadata should become explicit first-class state.

This avoids hiding critical delegation information in ad hoc message content.

## Node-Level Refactor Plan

### 1. Replace `route` with `supervisor`

Current problem:

- `route` is a classifier node
- it runs before the main agent
- it makes delegation too early

Target:

- replace it with a `supervisor` node that sees the full turn state and decides the next action

Responsibilities of `supervisor`:

- inspect conversation context
- understand whether browser capability is relevant
- decide among direct answer / normal tools / browser delegation
- produce structured orchestration output

### 2. Split "chatbot" into two roles

Right now `chatbot(...)` mixes:

- normal answer generation
- tool planning via tool calls

After the refactor, these responsibilities should be separated conceptually:

- `supervisor`: decides what path to take
- `respond`: generates the final direct answer

Normal tool usage can remain on the existing tool-call path, but the decision to enter that path should belong to the supervisor.

### 3. Reposition browser subgraph under supervisor control

Current browser node behavior:

- browser subgraph runs and returns an AI message directly

Target behavior:

- browser node runs as a delegated worker
- browser result is written into structured state
- control returns to `supervisor`
- supervisor decides how to present or combine the result

This matters because the main agent should remain the entity that responds to the user.

### 4. Tools should return to supervisor, not directly to chatbot

Current tool loop:

- chatbot -> tools -> chatbot

Target:

- supervisor -> tools -> supervisor

The supervisor becomes the single re-entry point after any delegated action.

That gives one consistent place for:

- deciding whether the task is complete
- deciding whether another delegated step is needed
- deciding how to word the final response

## Browser Delegation Contract

The browser subgraph should no longer infer the full task solely from the raw user message.

Instead, the supervisor should pass a structured browser task contract, for example:

- `goal`
- `task`
- `start_url`
- `success_criteria`
- `response_expectation`

Example:

```json
{
  "goal": "Find today's weather in Xi'an",
  "task": "Open a reliable weather website, look up Xi'an weather for today, and capture the current temperature and condition.",
  "start_url": null,
  "success_criteria": "Return today's weather summary for Xi'an with source page context.",
  "response_expectation": "A concise Chinese answer for the user."
}
```

This improves:

- delegation clarity
- browser planner performance
- final answer quality

## Prompt Strategy Changes

### Main system prompt

The main system prompt should explicitly state:

- browser capability exists
- the main agent can delegate browser work
- the main agent should decide delegation when browser interaction materially helps
- the main agent must not claim browser capability is unavailable unless browser execution actually failed

### Supervisor prompt

Introduce a dedicated supervisor prompt file.

Suggested new prompt directory additions:

- `agentbot/prompts/supervisor/`
- `agentbot/prompts/supervisor/system_prompt.md`
- `agentbot/prompts/supervisor/decision_schema.md`

This prompt should teach the main agent:

- when to answer directly
- when to use normal tools
- when to delegate to browser
- how to produce a structured orchestration decision

### Browser prompt

The browser prompt remains specialized and browser-use-aligned.

But after this refactor, the browser prompt should no longer carry responsibility for deciding whether browser usage is necessary. That decision belongs to the supervisor.

## Streaming and UI Impact

This refactor changes streaming semantics.

Today the browser branch can produce its own visible events directly after routing.

After refactor:

- supervisor decision event should stream first
- then delegated branch events stream
- then supervisor finalization event streams

Recommended new event sequence:

- `supervisor_decision_made`
- `tool_execution_started` or `browser_subgraph_started`
- delegated progress events
- `supervisor_response_started`
- `assistant_completed`

This will make the UI behavior much easier to understand:

- user sees that the main agent chose to delegate
- then sees delegated work happen
- then sees the main agent conclude

## Migration Plan

### Step 1. Introduce supervisor decision model

Add a structured supervisor decision schema and prompt.

Acceptance:

- the model can emit one of:
  - `respond`
  - `tools`
  - `browser`

### Step 2. Replace pre-chat router graph shape

Remove the standalone route-first path from the graph.

Acceptance:

- every turn enters supervisor first
- no browser delegation happens before supervisor

### Step 3. Rewire tools loop through supervisor

Change:

- `chatbot -> tools -> chatbot`

to:

- `supervisor -> tools -> supervisor`

Acceptance:

- after tool execution, control returns to supervisor

### Step 4. Rewire browser loop through supervisor

Change browser node behavior so it returns structured result state, not only a final AI message.

Acceptance:

- browser node writes result to state
- supervisor consumes browser result and generates final user-facing reply

### Step 5. Update prompts

Refactor prompts so:

- main prompt reflects true delegation ability
- supervisor prompt owns delegation decisions
- browser prompt owns browser execution only

Acceptance:

- main agent no longer claims browser is unavailable when browser subgraph is actually present

### Step 6. Update streaming/UI metadata

Make supervisor decisions visible in SSE and browser task summaries.

Acceptance:

- UI clearly shows that the main agent delegated to browser

## Files Expected To Change

Core graph:

- `agentbot/graph/builder.py`
- `agentbot/graph/nodes.py`
- `agentbot/graph/routes.py`
- `agentbot/graph/state.py`

Models:

- `agentbot/models/routing.py`
- `agentbot/models/browser.py`
- new supervisor decision model file

Prompts:

- `agentbot/prompts/system.py`
- new `agentbot/prompts/supervisor/` files
- `agentbot/prompts/browser/` files where delegation assumptions are currently mixed in

Streaming / UI:

- `agentbot/app/streaming_runner.py`
- `ui/src/shared/api/api.ts`
- `ui/src/app/app-shell.tsx`
- browser task display components if needed

Docs:

- `docs/architecture/graph-flow.md`
- current Phase 3 plan should later be superseded or archived
- implementation detail doc after each migration slice

## Risks

### 1. More orchestration complexity

This is a bigger change than prompt tuning or rule tuning.

Why still worth it:

- it fixes the architecture at the right layer
- it aligns the product with how users naturally expect an agent to behave

### 2. Supervisor prompt quality becomes critical

The supervisor prompt now becomes the main routing brain.

Mitigation:

- keep the decision schema narrow
- validate with concrete conversation examples

### 3. Tool calling and delegation can conflict

If the supervisor prompt is vague, the model may overuse tools or underuse browser delegation.

Mitigation:

- define clear delegation criteria
- separate direct response generation from orchestration decision-making

## What This Refactor Explicitly Chooses

This refactor intentionally chooses:

- centralized control in the main agent
- browser subgraph as a delegated worker
- less hard-coded routing
- more semantic orchestration

This refactor explicitly rejects:

- a classifier in front of the main agent as the primary browser routing mechanism
- patching browser intent detection forever with more regexes and rules
- letting the main agent pretend browser capability does not exist

## Recommended Execution Order

Implement this refactor in three slices:

1. Supervisor decision model + graph rewiring
2. Browser result contract + supervisor finalization
3. Streaming/UI alignment + prompt tightening

This keeps the app runnable while still making a real architectural change.

## Success Criteria

This refactor is successful when all of the following are true:

- all user turns enter the main agent first
- the main agent can decide to delegate browser work without explicit prefixes
- the main agent no longer says browser capability is unavailable when it exists
- browser work returns to the main agent for final response synthesis
- the UI shows delegation as a main-agent decision rather than a hidden pre-router behavior

## Final Recommendation

Do this as a real architectural refactor, not as another routing patch.

The current router-first design was useful as a transitional learning step.
The next correct step is to graduate to:

- **main-agent-first supervision**
- **browser subgraph as delegated worker**
- **single orchestration brain at the top of the graph**
