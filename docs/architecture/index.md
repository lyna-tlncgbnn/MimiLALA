# 架构总览

AgentBot 目前是一个围绕单一 LangGraph loop 组织起来的小型 CLI 应用。

## 核心模块

- `agentbot/app/`：CLI、runner、debug 输出
- `agentbot/config/`：配置读取与校验
- `agentbot/graph/`：graph state、nodes、routing 与 graph assembly
- `agentbot/memory/`：本地 conversation 与 execution persistence
- `agentbot/models/`：模型构造
- `agentbot/prompts/`：system prompt 组织
- `agentbot/tools/`：工具定义与注册

## 关键流程

- 用户输入先从 CLI 进入
- runner 负责加载配置、历史记录、tools 和 graph
- graph 负责执行 model 与 tool 步骤
- 结果会被写回 conversation 与 execution storage

## 相关文档

- `graph-flow.md`
- `project-structure.md`
- `persistence.md`
