# Frontend Architecture

## 当前目标

当前前端不是通用 Web 聊天页，而是本地桌面 Agent 应用的交互层。

它运行在：

- React
- Vite
- Electron 宿主

并通过本地 FastAPI 与 Python 运行时通信。

## 当前读取模型

前端当前已经不是单一 message list。

主界面读取模型分成三层：

### 1. Transcript

来自：

- `GET /api/conversations/{conversation_id}`

用于展示：

- 用户可见历史消息

### 2. Active Run

来自：

- 当前 SSE 流
- `AppShell` 内部临时状态

用于展示：

- 当前轮用户输入
- 当前轮执行步骤
- 当前轮最终回答的增量输出

### 3. Historical Runs

来自：

- `GET /api/conversations/{conversation_id}/runs`
- `GET /api/runs/{run_id}/steps`

用于展示：

- 历史任务列表
- 历史可展开执行过程

## 当前核心文件

- `ui/src/app/app-shell.tsx`
- `ui/src/features/chat/layout/chat-panel.tsx`
- `ui/src/features/chat/components/conversation-run-list.tsx`
- `ui/src/features/chat/components/run-steps-panel.tsx`
- `ui/src/shared/api/api.ts`

## 当前界面原则

当前前端的核心原则已经变成：

- transcript 和 execution 分开
- tools 不作为普通聊天气泡
- 执行区是时间线式可展开列表
- 回答正文和执行过程分层呈现

## 执行区当前形态

执行区当前通过：

- `RunStepsPanel`
- `@radix-ui/react-collapsible`

构成时间线式 disclosure UI。

当前方向是：

- 不做重卡片
- 箭头贴文案
- 点线作为时间线骨架
- 详情作为 inline detail

## 状态来源

### React Query

管理远程数据：

- conversations
- conversation detail
- conversation runs
- run steps

### Local state

`AppShell` 当前还维护：

- draft
- activeRun
- stream phase
- stream error

### Zustand

管理全局 UI 状态：

- sidebar collapsed
- sidebar width
- settings dialog
- rename target

## 当前 API 层

`ui/src/shared/api/api.ts` 当前已内建：

- zod schema
- fetch 封装
- SSE parser

并且当前主流式接口已经切到：

- `/runs/stream`

## 当前限制

当前前端仍未覆盖：

- 停止生成
- execution artifacts 面板
- 多窗口同步
- 更复杂的 run 对账可视化
- 全自动端到端 UI 测试
