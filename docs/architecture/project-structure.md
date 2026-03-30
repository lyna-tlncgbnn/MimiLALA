# 项目结构

## 运行入口

- `main.py`：薄入口，只负责转到 CLI
- `agentbot/app/cli.py`：CLI 参数处理与交互循环
- `agentbot/app/runner.py`：单轮执行总调度

## 运行支撑层

- `agentbot/config/settings.py`：读取并校验 `config.json`
- `agentbot/models/llm.py`：构造 `ChatOpenAI`
- `agentbot/prompts/system.py`：提供当前 system prompt

## Agent 层

- `agentbot/graph/state.py`：当前 graph state 类型
- `agentbot/graph/nodes.py`：chatbot 与 tool execution 节点
- `agentbot/graph/routes.py`：chatbot 之后的路由判断
- `agentbot/graph/builder.py`：graph 组装

## Persistence 层

- `agentbot/memory/conversation.py`：conversation storage
- `agentbot/memory/execution.py`：execution event storage

## Tools 层

- `agentbot/tools/basic.py`：内置工具
- `agentbot/tools/registry.py`：工具注册边界
