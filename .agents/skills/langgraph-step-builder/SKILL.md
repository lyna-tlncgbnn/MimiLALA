---
name: langgraph-step-builder
description: Extend this learning project by one LangGraph concept at a time while keeping the code runnable.
---

# LangGraph Step Builder

Use this skill when working in this repository to add the next learning step without overcomplicating the codebase.

## Goal

Advance the project by exactly one meaningful concept per iteration.

Examples:

- add typed state
- add a model-backed chatbot node
- add a tool node
- add conditional routing
- add checkpointing

## Workflow

1. Read `README.md`, `AGENTS.md`, and the current `main.py`.
2. Identify the single next concept that best fits the current stage.
3. Keep the program runnable from the command in `README.md`.
4. Prefer the smallest code change that demonstrates the concept clearly.
5. If the run instructions or learning sequence change, update `README.md`.

## Constraints

- Do not introduce multiple new abstractions in one step.
- Do not split files unless the current file has become meaningfully harder to learn from.
- Prefer clarity over framework completeness.
- Preserve a clean learning progression.

## Output Expectations

When using this skill:

- explain what single concept was added
- keep the example runnable
- mention the next logical step after the current change
