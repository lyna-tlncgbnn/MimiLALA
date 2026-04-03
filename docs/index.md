# 文档索引

`docs/` 是项目文档总入口。

## 从这里开始

- [README.md](/F:/AgentBot/README.md)
  项目概览、快速启动、当前主链路
- [architecture/index.md](/F:/AgentBot/docs/architecture/index.md)
  当前系统的技术说明总览
- [architecture/browser-use-migration-todo.md](/F:/AgentBot/docs/architecture/browser-use-migration-todo.md)
  浏览器子图继续借鉴 `browser-use` 的迁移清单与下一步顺序
- [architecture/browser-observation-pipeline.md](/F:/AgentBot/docs/architecture/browser-observation-pipeline.md)
  浏览器 observation 的 raw capture -> serialization 分层说明
- [architecture/browser-planner-state.md](/F:/AgentBot/docs/architecture/browser-planner-state.md)
  浏览器子图 planner state 的字段与当前边界
- [product/scope.md](/F:/AgentBot/docs/product/scope.md)
  当前产品范围与非目标
- [product/roadmap.md](/F:/AgentBot/docs/product/roadmap.md)
  后续产品和工程方向
- [runbooks/local-dev.md](/F:/AgentBot/docs/runbooks/local-dev.md)
  本地开发、启动与验证

## 文档分层

### `architecture/`

当前系统的技术真相：

- 总体架构
- runtime 主链路
- 数据库与持久化
- graph 执行流
- streaming 协议
- 前端读取模型
- tools 层设计
- 目录结构

### `product/`

项目做什么、不做什么，以及下一步方向：

- `scope.md`
- `roadmap.md`

### `runbooks/`

面向本地开发和排障：

- 配置说明
- 本地启动
- 调试与排障

### `exec-detail/`

每次实际实施后的执行说明。  
这些文档描述“做了什么”和“为什么这样改”，不是当前系统真相文档。

### `exec-plans/completed/`

历史阶段计划归档。  
这些文档保留阶段性背景，不应替代当前技术文档。

### `decisions/`

关键技术决策记录。  
早期 ADR 可能保留历史阶段结论，不一定等同于当前实现。

## 当前阅读顺序建议

如果你第一次进入这个项目，建议按这个顺序看：

1. [README.md](/F:/AgentBot/README.md)
2. [architecture/index.md](/F:/AgentBot/docs/architecture/index.md)
3. [runbooks/local-dev.md](/F:/AgentBot/docs/runbooks/local-dev.md)
4. [product/scope.md](/F:/AgentBot/docs/product/scope.md)

## 维护规则

- 代码行为、主链路、存储模型或接口变化后，优先更新 `architecture/`
- 启动方式、配置、排障方式变化后，更新 `runbooks/`
- 功能边界和阶段目标变化后，更新 `product/`
- 每次实作完成后，把实施过程写到 `exec-detail/`
