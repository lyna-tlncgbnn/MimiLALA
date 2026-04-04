# 2026-04-04 Backend Reorganization Phase 1 API-Service Boundary

## 目标

执行 `2026-04-04-backend-reorganization-blueprint.md` 中的 Phase 1：

- 收紧 `api -> service` 边界
- 让 FastAPI route 不再直接访问 `AgentDatabase` 和 storage repositories
- 保持 API 协议、主链路和返回结构不变

## 本次改动

### 新增 `RunService`

新增：

- `agentbot/services/runs.py`

职责：

- `get_run(run_id)`
- `list_for_conversation(conversation_id)`
- `get_run_steps(run_id)`
- `get_run_artifacts(run_id)`

这使 run 相关查询有了统一的 service 边界，而不是散落在 API route 中直接连接 SQLite。

### 收紧 `api/routes/runs.py`

调整前：

- route 直接初始化 `AgentDatabase`
- route 直接访问 `RunRepository` / `RunStepRepository` / `ArtifactRepository`

调整后：

- route 只负责：
  - HTTP 路由
  - 404 映射
  - serializer 输出
- 具体查询全部通过 `RunService`

### 收紧 `api/routes/conversations.py`

调整前：

- `list_conversation_runs()` 在 route 中直接访问 `AgentDatabase` 和 `RunRepository`

调整后：

- conversation 元数据仍通过 `ConversationService`
- run 列表改为经由 `RunService`

## 当前达成的边界

Phase 1 完成后：

- `agentbot/api/routes/conversations.py` 不再直接 import storage db/repository
- `agentbot/api/routes/runs.py` 不再直接 import storage db/repository

API 层当前只保留：

- request/response 协议
- HTTP 错误映射
- SSE 输出适配
- serializer 组装

## 未在本阶段处理的内容

以下内容刻意未改，以避免超出 Phase 1 范围：

- `runner.py` / `streaming_runner.py` 重复逻辑
- `services/` 命名与最终 `application/` 结构
- browser runtime 大文件拆分
- legacy `memory/` 收口

这些内容属于后续 Phase 2 及以后。

## 风险控制

本次改动只新增 service 边界，不改：

- API schema
- SSE 事件协议
- database schema
- graph 执行路径
- browser 子图逻辑

因此风险主要集中在：

- route 到 service 的参数传递
- 404 行为是否保持一致

## 后续建议

按蓝图继续推进时，下一步应进入 Phase 2：

- 抽取同步 / 流式执行共享内核
- 收敛 `runner.py` 与 `streaming_runner.py` 的重复逻辑
