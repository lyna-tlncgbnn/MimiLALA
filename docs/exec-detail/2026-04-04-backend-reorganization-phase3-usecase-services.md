# 2026-04-04 Backend Reorganization Phase 3 Use-Case Services

## 目标

执行 `2026-04-04-backend-reorganization-blueprint.md` 中的 Phase 3：

- 让 `services/` 从少数几个大 service，逐步变成按用例组织
- 让 API 通过更明确的用例入口调用能力
- 保持现有 API 协议与主链路行为不变

## 本次改动

### 新增按用例组织的 services 模块

新增：

- `agentbot/services/conversation_queries.py`
- `agentbot/services/conversation_commands.py`
- `agentbot/services/run_queries.py`
- `agentbot/services/run_execution.py`
- `agentbot/services/run_streaming.py`

其中职责分工为：

- `conversation_queries.py`
  - 列表查询
  - 单会话读取
  - 默认会话读取
- `conversation_commands.py`
  - 创建会话
  - 重命名会话
  - 删除会话
- `run_queries.py`
  - run 列表 / 单 run / run steps / artifacts 查询
  - 最新 run 查询
- `run_execution.py`
  - 同步发送消息
  - 同步发起 run
- `run_streaming.py`
  - 流式 run 执行入口

### API 改为使用明确用例入口

更新：

- `agentbot/api/routes/conversations.py`
- `agentbot/api/routes/runs.py`

现在 API 层直接依赖的是更明确的用例模块，而不是继续围绕：

- `ChatService`
- `ConversationService`
- `RunService`

这种范围较宽的入口。

### 保留兼容 facade，避免一次性打断旧调用路径

为降低重构风险，旧文件仍然保留，但改成兼容包装：

- `agentbot/services/chat.py`
- `agentbot/services/conversations.py`
- `agentbot/services/runs.py`

这些文件不再承担主组织职责，而是转发到新的用例模块。

## 当前达成的结构结果

Phase 3 完成后，`services/` 已经开始呈现出更清晰的用例形态：

```text
agentbot/services/
  conversation_queries.py
  conversation_commands.py
  run_queries.py
  run_execution.py
  run_streaming.py
```

同时保留兼容层，避免大范围 import 破坏：

```text
agentbot/services/
  conversations.py
  chat.py
  runs.py
```

## 为什么这样做

蓝图里 Phase 3 的重点不是立刻重命名成 `application/`，而是先在当前目录结构里建立更明确的用例边界。

本次做法符合这个原则：

- 没有大规模搬目录
- 没有改动 API 协议
- 但已经把主入口从“大 service”转向“明确用例”

这让后续进入真正的 `application/` 目录迁移时，风险会小很多。

## 未在本阶段处理的内容

以下内容仍未触碰：

- `application/` 目录正式迁移
- `domain/` 层引入
- browser 子系统拆分
- infrastructure 归类

这些属于蓝图后续阶段。

## 验证重点

本阶段至少应确认：

- FastAPI app 仍可正常导入
- routes 不再依赖旧的大 service 作为主入口
- 兼容 facade 仍可导入，避免其他调用点立即失效

## 后续建议

下一步若继续推进，可开始评估：

- 是否把 `sqlite_conversations.py` 也收口成更明确的基础设施模块
- 是否在合适时机将 `services/` 正式迁为 `application/`
