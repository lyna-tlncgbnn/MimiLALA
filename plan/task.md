# AgentBot Task Plan

## 项目目标

把当前仓库逐步建设成一个可扩展的、基于 LangGraph 的完整 Agent 项目。

项目建设原则：

1. 先搭稳定骨架
2. 先跑通最小真实模型闭环
3. 再逐步增加工具、会话、记忆、持久化和多入口能力
4. 后续扩展都在既有框架内完成，不反复推倒重来

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

后续扩展应在这条主链路基础上增量演进，而不是重写主流程。

---

## Phase 1 - Project Skeleton

**Status:** DONE

### Goal

建立完整、可扩展的项目骨架，并完成第一版真实模型调用能力。

### 实际完成情况

已经完成：

- 正式项目目录结构已建立
- `CLI` 已成为唯一用户入口
- `main.py` 已变成薄启动入口
- `config.json` 已成为配置入口
- 真实模型调用已通过 LangGraph 最小图跑通
- `tools` / `memory` / `prompts` / `routes` 已建立边界文件

---

## Phase 2 - Minimal Agent Loop

**Status:** DONE

### Goal

在现有骨架上实现最小 agent 闭环，把当前“单次模型调用”升级为“模型 + 工具 + 回到模型”的完整循环。

### 实际完成情况

已经完成：

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

增加会话和配置能力，让项目从“单轮 agent”变成“多轮可配置 agent”。

### 实际完成情况

- 增加默认短期 session
- 将 session 历史保存到 `workspace/sessions/default.jsonl`
- 让 CLI 自动读取并继续默认会话
- 保持 `config.json` 仍只负责 `llm` 配置

### Acceptance Criteria

- 多轮对话能保留上下文
- 默认 session 会自动创建和写回
- 工具回环在加入 session 后仍然正常

---

## Phase 4 - Framework Hardening

**Status:** TODO

### Goal

把最小 agent 提升为“可持续扩展的框架”。

### Deliverables

- 统一 tool 注册和加载方式
- 清晰的 system prompt 组织方式
- 错误处理机制
- 日志输出和调试模式
- graph 构建流程规范化

### Acceptance Criteria

- 新增简单工具时不需要修改 graph 主链路
- 常见错误有明确输出
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
4. 下一步进入 Phase 4
5. 不跳过框架加固直接做 memory 或 multi-agent
6. 每一阶段完成后再更新下一阶段细节

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
- 优先用官方推荐抽象，不自己发明复杂框架
- 优先用 CLI 验证能力，不先做 Web
- 优先做短期会话，不先做长期记忆
- 优先做单 agent，不先做多 agent

---

## 当前下一步

当前应实施：

**Phase 4 - Framework Hardening**

目标是在已完成的最小 agent 与默认会话能力基础上，整理工具注册、提示组织、错误处理和调试边界。
