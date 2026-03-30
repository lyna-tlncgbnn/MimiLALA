# ADR 0001：使用 LangGraph 作为核心 Agent Loop

## 状态

Accepted

## 背景

这个项目的目标是在保持执行流程清晰可见的前提下，渐进式地学习和实现 Agent 行为。

## 决策

使用 LangGraph 作为主 Agent loop 的编排层。

## 原因

- graph flow 清晰、可检查
- tool routing 是一等概念
- 后续更容易继续演进到 checkpointer、subgraph 和更复杂的 orchestration
- 它非常适合这种 learning-first 的仓库

## 影响

- graph structure 会成为整个架构的核心部分
- 后续扩展应优先建立在现有 graph flow 上，而不是绕过 graph 直接在 runner 里堆逻辑
