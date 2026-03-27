# Phase 2 - Minimal Agent Loop

## Status

**DONE**

## Summary

Phase 2 已完成，当前项目已经从“单次模型调用”升级为“最小 agent 回环”。

本阶段完成的核心变化：

- 模型可以决定是否调用工具
- 工具执行后，结果会返回给模型
- 模型会基于工具结果生成最终答案

完成后的主链路为：

`input -> build messages -> model -> conditional route -> tools -> model -> finalize output`

---

## 实际实施内容

本阶段已经完成：

- 引入 `ToolNode`
- 增加条件路由
- 增加两个简单工具：
  - `get_current_time`
  - `multiply`

相关边界保持不变：

- `CLI` 仍然是唯一入口
- `runner` 继续只负责总调度
- `MessagesState` 继续作为唯一 state 主干
- `config.json` 结构保持不变

---

## 验收结果

Phase 2 已满足：

- `python main.py "现在几点了"` 可以触发时间工具
- `python main.py "13乘以7是多少"` 可以触发乘法工具
- 工具执行后，模型会继续生成最终答案
- graph 已不再是线性图，而是最小 agent 回环

补充验证结果：

- 已确认模型实际发起了 `multiply` tool call
- 已确认图执行过程中产生了 `ToolMessage`
- 已确认最终回答发生在工具执行之后

---

## 暂不实现

本阶段仍不实现：

- session persistence
- 多轮上下文
- long-term memory
- API server
- 多 agent
- 高风险工具

---

## 下一阶段入口

下一步进入 **Phase 3 - Session And Config**。

目标是：

- 增加短期会话能力
- 让对话从单轮执行升级为多轮上下文执行
- 继续完善 `config.json` 结构和配置管理
