# 产品 Roadmap

## 当前状态

当前代码已经完成了几个关键阶段：

- project skeleton
- minimal agent loop
- default conversation persistence
- framework hardening
- conversation meta 和 local execution logs
- richer tools
- multi-conversation persistence
- desktop app foundation
- streaming chat phase 1

其中最近完成的几个阶段是：

### multi-conversation persistence

已经完成：

- conversation 按 `conversation_id` 独立存储
- execution 按 `conversation_id` 独立存储
- 默认会话通过指针文件绑定到标准 conversation 对象
- 多会话 CRUD 语义已经在 persistence 内核中具备

### desktop app foundation

已经完成：

- FastAPI 本地服务入口
- conversation CRUD API
- send message API
- React 前端工程骨架
- Electron 桌面壳
- 本地桌面端到后端的基础联通链路

### streaming chat phase 1

已经完成：

- 基于 `SSE` 的流式聊天接口
- optimistic user message
- assistant waiting / assistant streaming 状态
- tool started / tool finished 聊天流反馈
- 流结束后的 conversation 最终对齐

## 当前建议方向

当前最自然的下一步，不再是“把桌面端跑起来”，也不再是“把 streaming 做出来”，因为这两部分主链路都已经具备。

下一步更适合聚焦在桌面应用体验增强与可观察性增强，例如：

- execution log visualization
- 更完整的 streaming 体验
- 更完整的桌面设置与调试能力

## 近期里程碑

1. execution log visualization
2. 更完整的 streaming 体验
3. 更完整的桌面设置与调试能力
4. long-term memory
5. subgraph 或 multi-agent 实验

## 规划规则

Roadmap 只表达产品方向与阶段顺序。  
具体实现工作应落到 `docs/exec-plans/active/` 中。
