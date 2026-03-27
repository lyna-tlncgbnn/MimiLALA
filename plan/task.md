# AgentBot Task Plan

## 项目目标

把当前仓库逐步建设成一个可扩展的、基于 LangGraph 的完整 Agent 项目。

建设原则：

1. 先搭稳定骨架
2. 先跑通最小真实模型闭环
3. 再逐步增加工具、会话、调试、持久化和更多入口
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

后续扩展都应在这条主链路基础上增量推进，而不是重写主流程。

---

## Phase 1 - Project Skeleton

**Status:** DONE

### Goal

建立完整、可扩展的项目骨架，并完成第一版真实模型调用能力。

### 实际完成情况

- 正式项目目录结构已建立
- `CLI` 已成为唯一用户入口
- `main.py` 已变成薄启动入口
- `config.json` 已成为配置入口
- 真实模型调用已通过 LangGraph 最小图跑通

---

## Phase 2 - Minimal Agent Loop

**Status:** DONE

### Goal

把单次模型调用升级为最小 agent 回环。

### 实际完成情况

- 引入 `ToolNode`
- 增加条件路由
- 增加两个简单工具：
  - `get_current_time`
  - `multiply`
- 完成最小回环：
  `user input -> model -> tools -> model -> final answer`

---

## Phase 3 - Session And Config

**Status:** DONE

### Goal

增加默认短期 session，让项目从单轮 agent 升级为带短期上下文的最小框架。

### 实际完成情况

- 增加默认短期 session
- session 历史保存到 `workspace/sessions/default.jsonl`
- CLI 自动读取并继续默认会话
- `config.json` 仍只负责 `llm` 配置

### Acceptance Criteria

- 多轮对话可以保留上下文
- 默认 session 会自动创建和写回
- 工具回环在加入 session 后仍然正常

---

## Phase 4 - Framework Hardening

**Status:** DONE

### Goal

把当前最小 agent 整理成更稳、更容易扩展和调试的学习型框架。

### 实际完成情况

- 固定显式工具注册边界
- 整理 `system prompt` 组织方式
- 细化 model / tool / graph / session 错误边界
- 增加 `config.json` 驱动的控制台调试模式

### Acceptance Criteria

- 新增简单工具时不需要修改 graph 主链路
- 常见错误有更明确输出
- `debug=true` 时可以看到关键执行步骤
- 模块职责清晰，层次稳定

---

## Phase 5 - Mature Project Expansion

**Status:** TODO

### Goal

在稳定框架之上扩展成熟项目能力。

### Deliverables

- persistent session
- checkpointer
- long-term memory
- richer tools
- API server
- web/frontend integration
- subgraph
- multi-agent
- observability

### Acceptance Criteria

- 新能力通过新增节点、模块或入口接入
- 不破坏前四阶段已经稳定的结构
- 主链路仍保持一致

---

## 实施顺序要求

后续必须按阶段推进：

1. Phase 1 已完成
2. Phase 2 已完成
3. Phase 3 已完成
4. Phase 4 已完成
5. 下一步进入 Phase 5
6. 不跳过稳定骨架直接做复杂能力

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

在早期阶段默认遵守：

- 优先保证结构清晰，而不是功能堆积
- 优先使用官方推荐抽象，不自己发明复杂框架
- 优先用 CLI 验证能力，不先做 Web
- 优先做短期会话，不先做长期记忆
- 优先做单 agent，不先做多 agent

---

## 当前下一步

当前应实施：

**Phase 5 - Mature Project Expansion**

目标是在已完成的最小 agent、工具回环、默认 session 与调试边界基础上，开始增量引入更长期的持久化、更丰富的工具、更多入口和可观测能力。
