# ADR 0002：在早期阶段使用本地 JSONL 做持久化

## 状态

Accepted

## 背景

项目需要一种可检查、低复杂度的短期持久化方式，但当前阶段不希望过早引入数据库。

## 决策

在当前阶段使用 `workspace/` 下的本地 JSONL 文件来保存 conversation 和 execution 数据。

## 原因

- 容易手工检查
- 容易在文档中举例说明
- 对 CLI-first 的学习型项目来说复杂度足够低
- 对当前单 conversation 开发阶段来说已经足够

## 影响

- 当前 persistence model 很简单，但能力有限
- 未来如果迁移到数据库或 checkpointer，也应该尽量保留“conversation records + execution events”这套概念模型
