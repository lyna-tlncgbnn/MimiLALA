# Phase 3 - Session And Config

## Status

**DONE**

## Summary

Phase 3 的目标是在已完成的最小 agent 回环基础上，为项目加入默认短期会话能力。

本阶段只做：

- 一个默认 session
- 本地 JSONL 历史落地
- 自动加载和自动写回

本阶段不做：

- 多 session 切换
- 长期记忆
- 数据库
- 历史压缩

---

## 实际实施内容

本阶段已经完成：

- 新增 `workspace/` 数据根目录
- 新增 `workspace/sessions/default.jsonl`
- 在 runner 中接入 session 读取和写回
- 默认 CLI 自动使用这个 session

相关边界保持不变：

- `CLI` 仍然是唯一入口
- `MessagesState` 仍然是唯一 state 主干
- `config.json` 仍只负责 `llm`

---

## 验收结果

Phase 3 已满足：

- 第一次运行后自动创建 `workspace/sessions/default.jsonl`
- 第二次运行时可以读取前一次上下文
- 工具回环在加入 session 后仍然正常
- session 文件格式为 JSONL

---

## 暂不实现

本阶段仍不实现：

- 多 session
- session 配置化
- SQLite
- long-term memory
- API server
- 多 agent
