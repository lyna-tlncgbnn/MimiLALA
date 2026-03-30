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

其中最近完成的两个阶段是：

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

## 当前建议方向

当前最自然的下一步，不再是“把桌面端跑起来”，因为基础设施已经具备。

下一步更适合聚焦在桌面应用的体验增强与可观察性增强，例如：

- execution log visualization
- streaming 交互体验
- 更完整的设置与调试能力

## 近期里程碑

1. execution log visualization
2. streaming 交互体验
3. 更完整的桌面设置与调试能力
4. long-term memory
5. subgraph 或 multi-agent 实验

## 规划规则

Roadmap 只表达产品方向与阶段顺序。

具体实现工作应落到 `docs/exec-plans/active/` 中。
