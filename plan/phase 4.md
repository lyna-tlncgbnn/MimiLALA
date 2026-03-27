# Phase 4 - Framework Hardening

## Status

**DONE**

## Summary

Phase 4 的目标不是增加新功能，而是把现有最小 agent 整理得更稳、更容易理解，也更容易继续扩展。

本阶段完成了四件事：

- 固定显式工具注册边界
- 整理 system prompt 组织方式
- 细化错误处理边界
- 增加控制台调试模式

---

## 实际实施内容

本阶段已经完成：

- 保持 `registry.py` 作为唯一工具注册入口
- 保持 graph 主链路不变：
  `START -> chatbot -> route -> tools -> chatbot -> END`
- 将 prompt 组织为更清晰的几段职责常量
- 在 `config.json` 结构中引入 `debug` 开关
- 增加控制台逐步执行日志
- 将 model / tool / session / graph 的错误边界区分得更清楚

相关边界保持不变：

- `CLI` 仍然是唯一入口
- `runner` 仍然是统一调度层
- `MessagesState` 仍然是唯一 state 主干
- `config.json` 仍然是长期配置入口

---

## 调试模式说明

当 `debug` 为 `true` 时，控制台会输出关键执行步骤摘要，例如：

- 加载了多少条 session 历史
- 当前注册了哪些工具
- graph 是否开始执行
- 模型是否发起 tool call
- 调用了哪个工具
- 工具返回了什么
- 最终答案是什么

调试模式只输出控制台摘要，不写日志文件，也不接 tracing 平台。

---

## 验收结果

Phase 4 已满足：

- 新增工具时不需要修改 graph 主链路
- prompt 仍然只从 `prompts/system.py` 进入
- 常见错误会按阶段给出更明确的提示
- `debug=true` 时可以在控制台看到 agent 执行步骤
- `debug=false` 时 CLI 输出仍保持简洁

---

## 暂不实现

本阶段仍不实现：

- 自动工具发现
- tracing / observability 平台接入
- checkpointing
- API server
- long-term memory
- multi-agent
