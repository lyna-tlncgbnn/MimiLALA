# 2026-04-04 Backend Reorganization Phase 2 Execution Core

## 目标

执行 `2026-04-04-backend-reorganization-blueprint.md` 中的 Phase 2：

- 收敛 `agentbot/app/runner.py` 与 `agentbot/app/streaming_runner.py` 的重复逻辑
- 抽取共享执行骨架
- 保持同步 / 流式两个入口的输出语义不变

## 本次改动

### 新增共享执行内核

新增：

- `agentbot/app/execution_core.py`

该模块统一承载了同步与流式执行都依赖的公共步骤：

- settings 加载
- llm 初始化
- conversation 读取
- user message 构造
- run 启动
- input messages 构造
- graph 执行
- chunk 归一化
- final assistant 提取
- run 完成持久化
- 公共文本与 metadata 处理

### `runner.py` 收缩为同步 adapter

调整后：

- 仍负责同步执行的 user-facing error 语义
- 仍负责 debug 输出
- 仍负责同步结果的最后提取

但不再重复承担：

- 初始化 settings / llm / conversation / run
- graph 执行骨架
- final assistant 提取与结果持久化辅助逻辑

### `streaming_runner.py` 收缩为流式 adapter

调整后：

- 仍负责 SSE/UI event 语义
- 仍负责 `assistant_final_delta` / `assistant_finalized` / `run_completed` 这些流式输出

但共享了执行准备、graph 调用、metadata、文本提取等逻辑。

## 设计取舍

本阶段刻意没有把同步与流式“完全合并”为一个函数。

原因：

- 蓝图明确要求只抽共享骨架
- 同步与流式在输出形态上天然不同
- 过度抽象 event 处理会降低可读性

因此本次做法是：

- 公共初始化与 graph 执行收进 `execution_core.py`
- 不同输出适配仍保留在各自入口

这符合蓝图中“只抽共享步骤，不强行统一所有输出形式”的要求。

## 当前收益

本阶段完成后，以下变更将只需改一处或显著减少重复修改：

- settings / llm 初始化方式
- conversation seed 构造
- graph stream 调用方式
- chunk normalization
- final assistant 查找规则
- 文本内容 stringify 规则

## 未在本阶段处理的内容

以下内容有意未改：

- `services/` 到 `application/` 的命名与目录调整
- API 层协议
- browser runtime 结构拆分
- legacy `memory/` 收口

这些仍属于后续阶段。

## 验证要点

本阶段完成后应继续验证：

- CLI 同步单轮执行仍能导入和运行
- FastAPI app 仍能成功导入
- 流式 run 的 SSE 事件形状未变化
- transcript / runs / run_steps / checkpoints 语义未变化

## 风险提醒

本次改动中，同步与流式入口现在共享同一套准备逻辑。

这会让后续维护更轻，但也要求：

- 不要再把仅一侧需要的逻辑偷偷塞回 adapter
- 若出现同步 / 流式特有差异，应先判断是否真的是输出差异，而不是初始化差异

## 后续建议

下一步按蓝图进入 Phase 3：

- 让 `services/` 更明确地按用例组织
- 弱化“两个大 service 类”的中心地位
