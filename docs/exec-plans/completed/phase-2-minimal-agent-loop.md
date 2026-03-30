# 已完成计划：Phase 2 - Minimal Agent Loop

## 状态

DONE

## 完成内容

Phase 2 把项目从“单次模型调用”升级成了最小 agent loop。

核心结果包括：

- 引入 `ToolNode`
- 增加 conditional routing
- graph 变成 `model -> tools -> model`
- 注册了两个 starter tools：
  - `get_current_time`
  - `multiply`

## 基于当前代码的复核

这个阶段的结论与当前代码仍然一致。

当前 graph 依然遵循同样的基础循环：

```text
START -> chatbot -> route -> tools -> chatbot -> END
```

tool registry 仍然集中在 `agentbot/tools/registry.py`。

## 后续阶段带来的变化

后面的阶段在这个 loop 外层增加了 persistence 和 execution logging，但 Phase 2 的 graph 设计仍然是整个项目的基础。
