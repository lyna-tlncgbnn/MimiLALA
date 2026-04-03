# Browser Subgraph Phase 1D

## 日期

- 2026-04-03

## 目标

增强 browser 子图的可观察性，让执行过程不仅能看到步骤，还能看到：

- browser artifacts
- loop detection 信号
- 更适合后续 timeline / recovery 的执行输出

## 本次实现

### 1. 新增轻量 loop detection

参考 `browser-use` 的 `PageFingerprint` / `ActionLoopDetector` 思路，实现了轻量版本：

- 页面指纹
- 动作 hash
- 重复动作计数
- 页面停滞提示

当前策略更偏“提示 + 保护性收口”，不是复杂的阻断系统。

相关文件：

- [loop_detection.py](/F:/AgentBot/agentbot/browser/loop_detection.py)
- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

### 2. browser state 增加 loop 相关字段

新增：

- `browser_page_fingerprint`
- `browser_stagnant_count`
- `browser_loop_signal`

相关文件：

- [state.py](/F:/AgentBot/agentbot/graph/state.py)

### 3. browser artifacts 正式落库

这次没有只停留在文件输出，而是把 browser 产物正式接入现有 `artifacts` 表。

当前已落库的 artifact 类型：

- `browser_screenshot`
- `browser_page_summary`

相关文件：

- [shadow_runtime.py](/F:/AgentBot/agentbot/storage/shadow_runtime.py)
- [graph_runtime_events.py](/F:/AgentBot/agentbot/app/graph_runtime_events.py)

### 4. 新增 run artifacts API

新增：

- `GET /api/runs/{run_id}/artifacts`

用于读取某次 run 关联的 browser artifacts。

相关文件：

- [runs.py](/F:/AgentBot/agentbot/api/routes/runs.py)
- [schemas.py](/F:/AgentBot/agentbot/api/schemas.py)
- [serializers.py](/F:/AgentBot/agentbot/api/serializers.py)
- [api.ts](/F:/AgentBot/ui/src/shared/api/api.ts)

## 当前能力边界

Phase 1D 完成后，browser 子图已经支持：

- 中间步骤写入 `run_steps`
- screenshot / page summary 写入 `artifacts`
- 对重复动作和页面停滞给出 loop signal
- 在必要时根据 loop signal 提前收口，避免继续空转

当前还没有：

- 真正可视化 artifacts 的前端展示
- 更复杂的错误分类和恢复策略
- approval / interrupt gating

这些放到后续阶段。

## 验证

已完成以下验证：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. `ui` 前端构建通过：`npm run build`
3. Phase 1D 持久化烟测：
   browser run 成功写入 `artifacts`
4. 已确认 artifact 类型和数量可从数据库读出

示例验证结果里，已看到：

- `browser_action_screenshot`
- `browser_observe_screenshot`
- `browser_observe_summary`

## 结果

Phase 1D 完成后，browser 子图已经不再只是“步骤型 timeline”，而是开始具备：

- 可追溯的浏览器产物
- 可诊断的循环提示
- 更适合前端后续增强展示的数据基础

这为下一阶段的 approval / interrupt 预留提供了更稳的执行上下文。
