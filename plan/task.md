# AgentBot Task Plan

## 项目目标

把当前仓库逐步建设成一个可扩展的、基于 LangGraph 的完整 Agent 项目。

建设原则：

1. 先搭稳定骨架
2. 先跑通最小真实模型闭环
3. 再逐步增加工具、会话、执行日志、持久化和更多入口
4. 后续扩展都基于现有框架增量演进，而不是反复推倒重来

---

## 总体技术方向

默认技术选型：

- LangGraph `Graph API`
- LangGraph `MessagesState`
- LangChain `ChatOpenAI`
- `config.json` 作为长期配置入口
- CLI 作为第一入口
- `main.py` 只作为薄启动入口

长期主链路固定为：

`input -> build messages -> model -> conditional route -> tools -> model -> finalize output`

---

## Phase 1 - Project Skeleton

**Status:** DONE

已完成正式项目骨架、真实模型调用和 CLI 入口。

## Phase 2 - Minimal Agent Loop

**Status:** DONE

已完成最小 agent 回环、`ToolNode`、条件路由和基础工具。

## Phase 3 - Session And Config

**Status:** DONE

已完成默认短期会话和 `workspace/sessions/default.jsonl` 持久化。

## Phase 4 - Framework Hardening

**Status:** DONE

已完成显式工具注册、prompt 组织、错误边界和控制台调试输出。

## Phase 5 - Mature Project Expansion

**Status:** DOING

### 当前已完成的第一步

- 引入 `workspace/conversations/default.jsonl`
- 引入 `workspace/executions/default.jsonl`
- 固定文件级 `meta`
- 让 conversation 和 execution 通过同一个 `conversation_id` 对齐
- 引入 `execution_id`，区分同一对话中的单次运行
- 将 execution events 变成本地默认落地能力

### 后续建议顺序

1. richer tools
2. persistent conversation/checkpointer 强化
3. API server
4. execution log 展示层
5. long-term memory
6. subgraph / multi-agent

---

## 每阶段统一检查项

每个阶段完成时都检查：

- 代码结构是否仍然清晰
- 入口是否仍然统一
- graph 主链路是否保持稳定
- 是否引入了当前阶段不该出现的复杂度
- 后续扩展是否还能在现有框架上自然继续

---

## 当前默认约束

- 优先保证结构清晰，而不是功能堆积
- 优先使用官方推荐抽象，不自己发明复杂框架
- 优先用 CLI 验证能力，不先做 Web
- 优先做单 agent，不先做多 agent

---

## 当前下一步

当前建议继续推进：

**Phase 5 - richer tools**

也就是在已完成的 conversation / execution 本地数据模型上，开始增加更真实的工具能力。
