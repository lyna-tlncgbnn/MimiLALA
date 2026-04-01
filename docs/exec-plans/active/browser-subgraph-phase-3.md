# 执行计划：Browser Subgraph Phase 3

## 状态
ACTIVE

## 背景

`Browser Subgraph Phase 2` 已经把浏览器能力从“独立入口”推进到了“聊天主链路中的可用能力”。

当前项目已经具备：

- LangGraph 主图中的显式浏览器入口
- 基于 `browser-use` 执行层的浏览器子图
- 聊天中的浏览器 SSE 事件
- 前端可见的浏览器任务摘要
- 基础动作集与部分 `browser-use` 风格 prompt 对齐

但当前实现仍然存在明显边界：

1. 路由到浏览器子图仍然是显式前缀触发，不是 agent 自主判断
2. 浏览器 planner 的 prompt 仍然是本地裁剪版本，尚未形成文件化 prompt 体系
3. 浏览器 planner 的 history / input shape 还没有系统性向 `browser-use` 对齐
4. 浏览器动作集仍然只覆盖最小可用子集，离 `browser-use` 的执行面还有差距

因此，Phase 3 的重点不再是“让浏览器子图能跑”，而是让浏览器 agent 更接近一个可维护、可扩展、可解释的 `browser-use` 风格子 agent。

## Phase 3 目标

Phase 3 的单一目标是：

**把浏览器子图从“显式触发的浏览器能力”推进成“由主 agent 决策路由、并在 planner 层显著对齐 browser-use 的浏览器子 agent”。**

这一步具体包含四个结果：

- 主 agent 可以判断是否将请求路由到 browser subgraph
- 浏览器 prompt 从 Python 字符串迁移为文件化 prompt 资源
- 浏览器 planner 的输入上下文与输出结构继续向 `browser-use` 风格靠拢
- 浏览器执行动作继续从 `browser-use` 迁移高价值能力

## 本阶段不做什么

本阶段明确不包含以下内容：

- 不做完整 multi-agent orchestration
- 不做多个平级 agent 间 handoff 系统
- 不做 checkpointer
- 不做 long-term memory
- 不做完整 execution 可视化面板
- 不直接复用 `browser_use.agent.service.Agent`
- 不把 `browser-use` 整套 message manager / history manager 原样迁入项目
- 不在本阶段把全部 `browser-use` actions 一次性搬完

## 核心问题

Phase 2 跑通以后，当前最值得解决的是四个问题：

1. 浏览器路由依旧是写死前缀，主 agent 不参与决策
2. 浏览器 prompt 仍然主要靠本地拼接，维护性和演进性不足
3. planner 虽然已经修复了 schema 错位，但其上下文组织仍然偏简化
4. 浏览器动作能力还不足以覆盖更复杂的真实网页流程

这些问题共同指向同一个方向：

**让浏览器 agent 在“路由、prompt、history、actions”四层同时提升，而不是只做单点补丁。**

## 核心决策

### 1. 路由从显式触发升级为 model-guided routing

本阶段将新增一个受约束的 routing decision 层。

推荐策略：

- 若用户显式使用 `/browser`、`browser:`、`浏览器:` 等前缀，则强制进入浏览器子图
- 否则先由主 agent 产出结构化路由判断
- 路由判断只允许两个结果：
  - `chat`
  - `browser`

建议输出结构：

```json
{
  "route": "chat",
  "reason": "..."
}
```

这样做的原因：

- 保留显式覆盖，便于调试
- 引入 agent 判断，但不引入不可解释的自由路由
- 方便记录 routing decision 到 execution log

### 2. 浏览器 prompt 文件化

本阶段将把浏览器 prompt 从 Python 字符串迁移到独立 prompt 目录。

建议新增目录：

- `agentbot/prompts/browser/`

建议文件：

- `agentbot/prompts/browser/router_prompt.md`
- `agentbot/prompts/browser/system_prompt_no_thinking.md`
- `agentbot/prompts/browser/system_prompt_browser_use_no_thinking.md`
- `agentbot/prompts/browser/partials/` 下的局部模板（如后续需要）

其中：

- `system_prompt_no_thinking.md` 作为浏览器 planner 的主 prompt 基底
- 内容参考 `browser-use` 的 `system_prompt_no_thinking`
- 但保留“本地裁剪版”策略，只声明当前项目真实具备的能力

核心原则：

- 结构参考 `browser-use`
- 能力声明只保留当前真实支持项
- prompt 成为可维护资源，而不是嵌在 Python 代码里的大字符串

### 3. 浏览器 planner/history 对齐 browser-use

本阶段不迁移 `browser-use` 的整套 agent runtime，但会系统性对齐 planner 输入结构。

建议逐步组织为以下几类输入：

- `user_request`
- `agent_history`
- `browser_state`
- `step_info`
- `read_state` 的本地可替代版本（若当前有对应能力）

其中 `agent_history` 可先从当前 graph state 派生摘要，而不是直接照搬其 message manager。

浏览器 planner 输出则继续沿用已经修正好的 `browser-use` 风格结构：

- `evaluation_previous_goal`
- `memory`
- `next_goal`
- `action`

### 4. 动作迁移继续基于 browser-use

本阶段继续扩浏览器动作，但遵循“高价值优先、保持可运行”的原则。

建议优先迁移顺序：

1. `read_content`
2. `send_keys`
3. `switch_tab`
4. `select_dropdown_option`
5. `get_dropdown_options`
6. `screenshot`
7. `close_tab`

优先级判断依据：

- 对真实网页任务价值高
- 与当前子图结构耦合较低
- 易于复用 `browser-use` 执行层实现

## 本阶段文件级落地建议

### 1. 路由决策相关

预计修改：

- `agentbot/graph/builder.py`
- `agentbot/graph/routes.py`
- `agentbot/graph/nodes.py`
- `agentbot/models/` 下新增 routing decision model

建议新增：

- `agentbot/models/routing.py`
- `agentbot/prompts/browser/router_prompt.md`

### 2. Prompt 文件化相关

预计新增：

- `agentbot/prompts/browser/__init__.py`
- `agentbot/prompts/browser/loader.py`
- `agentbot/prompts/browser/system_prompt_no_thinking.md`
- `agentbot/prompts/browser/system_prompt_browser_use_no_thinking.md`
- `agentbot/prompts/browser/router_prompt.md`

预计修改：

- `agentbot/graph/browser_nodes.py`
- `agentbot/prompts/browser_subgraph.py` 或将其逐步退役

### 3. Planner/history 对齐相关

预计修改：

- `agentbot/graph/browser_state.py`
- `agentbot/graph/browser_nodes.py`
- `agentbot/models/browser.py`

可考虑新增：

- `agentbot/models/browser_history.py`

### 4. 动作扩展相关

预计修改：

- `agentbot/models/browser.py`
- `agentbot/services/browser_runtime.py`
- `agentbot/browser_worker.py`

### 5. 前端 / 展示 / execution logging

视实际执行进度，可能修改：

- `agentbot/app/streaming_runner.py`
- `agentbot/memory/execution.py`
- `ui/src/shared/api/api.ts`
- `ui/src/app/app-shell.tsx`

## 具体工作拆分

### Step 1：引入 routing decision

目标：

- 普通聊天消息可以由主 agent 判断是否进入 browser subgraph

建议实现：

- 新增 routing decision schema
- 主图入口先做 decision
- `chat` 继续走现有链路
- `browser` 进入浏览器包装节点
- 显式 `/browser` 保留最高优先级

验收：

- 非显式前缀消息也可以在合适场景下进入浏览器子图
- 显式前缀始终强制进入浏览器子图

### Step 2：完成 prompt 文件化

目标：

- 浏览器 planner prompt 不再直接定义在 Python 字符串中

建议实现：

- 新增 `agentbot/prompts/browser/`
- 以 `browser-use/system_prompt_no_thinking` 为基底裁剪出本地版本
- Python 侧改为读取模板并注入变量

验收：

- 浏览器 planner 使用文件化 prompt
- 提示词修改不再需要改 Python 大段字符串

### Step 3：history / input shape 对齐 browser-use

目标：

- 浏览器 planner 的上下文更像 browser-use，而不是当前的简化拼接

建议实现：

- 引入 `agent_history` 摘要结构
- 把过去几步的 action/result 组织成稳定格式
- 明确 `browser_state`、`step_info` 的输入块

验收：

- planner prompt 中存在稳定的 history block
- 模型能利用前几步信息，而不是只依赖上一跳结果

### Step 4：继续迁移高价值动作

目标：

- 浏览器子图支持更复杂的真实网页流程

建议优先顺序：

1. `read_content`
2. `send_keys`
3. `switch_tab`
4. `select_dropdown_option`
5. `get_dropdown_options`

其余动作在本阶段后半程视情况扩展。

验收：

- 新动作能从 planner 输出 -> runtime bridge -> worker 执行完整打通

### Step 5：同步前端与执行日志

目标：

- routing decision 与新增浏览器动作在 SSE 和 execution log 中可见

建议实现：

- 新增 routing decision 事件
- execution log 记录进入浏览器的原因
- 前端必要时更新浏览器任务摘要展示

验收：

- 能在日志中看到“为何进入浏览器子图”
- 能在前端或日志中看到新增动作的关键执行摘要

## Prompt 策略

### 浏览器 planner prompt

原则：

- 以 `browser-use` 的 `system_prompt_no_thinking` 为主参考
- 使用本地裁剪版，不直接照搬全部能力声明

必须保留的结构：

- 用户请求优先级
- browser_state 说明
- indexed interactive elements 约束
- action 输出 JSON 格式
- completion 规则
- action-specific rules

必须裁剪的内容：

- 当前项目尚未实现的 actions
- 当前项目尚未实现的 read_state / screenshot / file-system 行为
- 当前项目没有的多动作批量能力（若仍未支持）

### 路由 prompt

原则：

- 极小、极明确、强约束
- 不让 routing model 自由发挥

输出只允许：

- `chat`
- `browser`

并附简短理由，便于调试和日志记录。

## 验收标准

当以下条件同时满足时，可认为 Phase 3 完成：

- 主 agent 可判断是否进入浏览器子图
- 显式 `/browser` 仍然可以强制覆盖
- 浏览器 prompt 已迁移到文件化 prompt 目录
- 浏览器 planner 输入结构显著向 browser-use 对齐
- 至少 3 到 5 个高价值动作完成迁移并可执行
- routing decision 与浏览器关键步骤可进入 SSE / execution log
- 相关文档同步更新

## 主要风险

### 风险 1：prompt 直接照搬 browser-use 造成能力声明错位

应对：

- 采用“browser-use-compatible local variant”
- 只声明当前项目真实支持的能力

### 风险 2：agent 决策路由误判

应对：

- 保留显式 `/browser` 强制入口
- 路由 decision 使用强约束 schema
- execution log 记录 decision 原因

### 风险 3：动作迁移过快导致 worker 层不稳定

应对：

- 继续按动作逐步迁移
- 每个动作单独验证
- 不一次性引入全部 `browser-use` actions

## 相关参考

- `docs/exec-plans/active/browser-subgraph-phase-2.md`
- `docs/exec-detail/2026-03-31-browser-subgraph-phase-2-tool-prompt-alignment.md`
- `docs/exec-detail/2026-03-31-browser-subgraph-phase-2-chat-integration.md`
- `docs/exec-detail/2026-03-31-browser-subgraph-phase-2-planner-schema-alignment.md`
- `docs/exec-detail/2026-03-31-browser-subgraph-phase-2-browser-task-ui.md`
- `F:/browser-use/browser_use/agent/system_prompts/system_prompt_no_thinking.md`
- `F:/browser-use/browser_use/agent/system_prompts/system_prompt_browser_use_no_thinking.md`
