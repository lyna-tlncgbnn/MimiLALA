# 产品 Roadmap

## 当前状态

当前代码已经完成了项目的前几个关键阶段：

- project skeleton
- minimal agent loop
- default conversation persistence
- framework hardening
- conversation meta 和 local execution logs
- richer tools

其中，`richer tools` 阶段已经完成了两项核心目标：

- 增加基础 `filesystem` 能力
- 把 tools 注册方式改成自动扫描注册

并且额外补充了：

- PDF 读取能力
- DOCX 读取能力

## 当前建议方向

在 `richer tools` 已经完成之后，下一步最自然的方向是继续增强 persistence，尤其是补上更强的 persistence model 和 checkpointer 支持。

## 近期里程碑

1. 更强的 persistence 与 checkpointer 支持
2. API server
3. execution log visualization
4. long-term memory
5. subgraph 或 multi-agent 实验

## 规划规则

Roadmap 只表达产品方向与阶段顺序。

具体实现工作应落到 `docs/exec-plans/active/` 中。
