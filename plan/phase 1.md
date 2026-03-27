# Phase 1 - Project Skeleton

## Status

**DONE**

## Summary

Phase 1 已完成，当前仓库已经从单文件 demo 过渡到正式项目骨架。

这一阶段实际完成的目标：

- 目录结构已切换到长期可扩展的项目形态
- `CLI` 已成为唯一用户入口
- `main.py` 只保留薄启动职责
- 真实模型调用已通过 LangGraph 最小图跑通
- 配置入口已固定为根目录 `config.json`

这一阶段明确没有实现：

- tool calling
- 条件路由
- session persistence
- memory
- API server
- multi-agent

---

## 实际落地结果

### 已建立的目录骨架

```text
agentbot/
  app/
    cli.py
    runner.py
  config/
    settings.py
  graph/
    state.py
    nodes.py
    routes.py
    builder.py
  models/
    llm.py
  tools/
    basic.py
    registry.py
  memory/
    session.py
  prompts/
    system.py
main.py
config.json
```

### 当前职责边界

- `main.py`
  只负责调用 CLI 入口，不承载业务逻辑

- `agentbot/app/cli.py`
  负责读取命令行参数或交互输入，调用 runner，并打印结果

- `agentbot/app/runner.py`
  负责单轮执行总调度：
  1. 读取配置
  2. 初始化真实模型
  3. 构造 system message 和 user message
  4. 构建 LangGraph
  5. 执行 graph
  6. 提取最终 assistant 输出

- `agentbot/config/settings.py`
  负责读取并校验根目录 `config.json`

- `agentbot/models/llm.py`
  负责基于配置创建 `ChatOpenAI`

- `agentbot/graph/builder.py`
  负责构建最小图：
  `START -> chatbot -> END`

- `agentbot/graph/nodes.py`
  负责最小模型节点，即用真实模型处理当前消息列表

- `agentbot/prompts/system.py`
  负责提供最小 system prompt

- `agentbot/tools/*` 与 `agentbot/memory/*`
  当前仅保留边界和占位，不承担实际能力

---

## 配置方式

Phase 1 实际采用的是 `config.json`，不是环境变量直读。

当前配置结构：

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "your-model-name",
    "temperature": 0.1
  }
}
```

说明：

- `api_key` 必填
- `base_url` 支持 OpenAI 兼容接口，因此适用于阿里等兼容服务
- `model` 使用具体供应商实际支持的模型名
- `temperature` 必须是数字

---

## 当前运行方式

### 命令行直接传参

```powershell
.\.venv\Scripts\python.exe main.py "你好"
```

### 交互式输入

```powershell
.\.venv\Scripts\python.exe main.py
```

然后在提示符中输入一句话。

---

## 验收结果

以下 Phase 1 验收项已经满足：

- `main.py` 不再包含 graph 业务逻辑
- `CLI` 是唯一用户入口
- graph 已拆入 `agentbot/graph`
- 模型初始化已拆入 `agentbot/models`
- 配置读取已拆入 `agentbot/config`
- 可以通过 `config.json` 驱动真实模型调用
- 缺少关键配置时会输出用户可读错误
- 最小图结构已固定为 `START -> chatbot -> END`

---

## 下一阶段入口

下一步进入 **Phase 2 - Minimal Agent Loop**。

目标是：

- 在现有骨架上接入 `ToolNode`
- 增加 1 到 2 个简单工具
- 把当前单次模型调用升级成最小 agent 回环
