# Runtime Flow

## 目标

本文描述当前代码里从桌面前端到 LangGraph 再到持久化的主链路。
它不是产品说明，而是运行链路说明。

## 同步主链路

同步链路主要用于：

- CLI
- 同步 API

路径如下：

```text
CLI / POST /runs
  -> ChatService.send_run_to_conversation()
    -> run_once(...)
      -> build_graph(...)
      -> graph.stream(...)
      -> tools / LLM / checkpoints
      -> persist transcript / run / steps
    -> read back conversation + latest run
```

关键文件：

- `agentbot/app/runner.py`
- `agentbot/services/chat.py`
- `agentbot/api/routes/conversations.py`

## 流式主链路

当前桌面端主聊天体验主要走流式链路：

```text
React UI
  -> POST /api/conversations/{conversation_id}/runs/stream
    -> FastAPI StreamingResponse
      -> ChatService.stream_message_to_conversation()
        -> stream_once(...)
          -> LangGraph graph.stream(...)
            -> LLM + ToolNode + checkpoints
          -> translate runtime events to SSE
      -> browser fetch + stream reader
        -> activeRun state
        -> query refetch
        -> persisted transcript/runs take over
```

关键文件：

- `ui/src/shared/api/api.ts`
- `ui/src/app/app-shell.tsx`
- `agentbot/api/routes/conversations.py`
- `agentbot/services/chat.py`
- `agentbot/app/streaming_runner.py`

## 前端阶段

一次流式发送的大致前端阶段是：

1. 用户提交 draft
2. 前端决定目标 conversation
3. 如果没有 active conversation，则先创建 conversation
4. 前端创建临时 `activeRun`
5. 前端开始读取 SSE
6. `run_started` 到达后，补齐真实 `run_id`
7. `step_started / step_completed` 更新执行步骤
8. `assistant_final_delta` 逐步拼接正式回答
9. `assistant_finalized / run_completed` 到达后完成本轮
10. invalidate / refetch conversation 与 runs
11. persisted transcript 与 historical runs 接管显示

## SSE 语义

当前主事件是：

- `run_started`
- `step_started`
- `step_completed`
- `assistant_final_delta`
- `assistant_finalized`
- `run_completed`
- `run_failed`
- `done`

这意味着当前 UI 已经不再依赖早期的 message-centric 事件协议。

## LangGraph 执行阶段

当前 graph 仍以 chatbot/tool loop 为主，但已经接入 specialist subgraph：

1. runner 构建输入
2. graph 先经过 intent 判断节点
3. 如果识别为浏览器任务，则进入 `browser_subgraph`
4. `browser_subgraph` 完成后回到主图的 `browser_summary`
5. 否则进入 `chatbot` 节点调用已绑定 tools 的 LLM
6. route 判断是否转入 `tools`
7. `ToolNode` 执行
8. 工具结果送回 `chatbot`
9. 当模型不再发出 tool call 时结束

## 浏览器子图在运行链路中的位置

当前 `browser_subgraph` 已经完成最小真实浏览器交互闭环，主要支持：

- Playwright 驱动 Chromium 会话
- 真实页面导航与读取
- 页面标题、主文本、链接、表单控件摘要
- iframe-aware observation
- AX / aria 辅助信息
- 页面截图输出到 `workspace/browser_artifacts/`
- 子图内部 `observe -> decide -> act -> evaluate -> observe/finish` 循环
- 浏览器动作：`navigate / new_tab_navigate / click / type / press_enter / scroll / wait / go_back / switch_tab`
- browser 执行步骤实时写入 `run_steps`
- browser screenshot / page summary artifacts 落入统一 `artifacts`
- 轻量 loop detection 提示重复动作与页面停滞
- 浏览器动作当前默认直接执行，不再在子图内做 approval gating
- runtime 级副作用回收：navigation / dialog / download / tab
- 借鉴 `browser-use` 的 planner 规则适配

它当前仍然不是完整 browser automation framework，现阶段主要用于打通：

- 子图接入主图
- browser 执行步骤落库
- execution timeline 可见性
- 真实页面读取与基础交互能力

## 当前持久化落点

当前一次 run 结束后，最终会稳定落到两套存储：

### 产品层数据库

落到 `agent_runtime.db`：

- conversation metadata
- user message
- assistant final message
- run
- run steps
- artifacts

### LangGraph checkpoint 库

落到 `langgraph_checkpoints.db`：

- thread state
- checkpoint snapshots

## 当前前端显示模型

前端不是直接把所有消息平铺出来，而是：

### transcript

来自 persisted `messages`

### active run

来自当前 SSE 事件和本地状态

### historical runs

来自 persisted `runs`

### historical run steps

来自 persisted `run_steps`

这个模型的好处是：

- 运行中的过程可见
- 历史对话保持干净
- 工具过程不会污染 transcript 主消息区

## 下一步

浏览器子图后续继续向 `browser-use` 靠拢时，当前建议顺序是：

1. planner state 增强，而不是先做大基础设施重构
2. 补第二轮关键动作，让 prompt 规则和 runtime 能力更匹配
3. 继续增强 observation 的阻塞态识别和可操作表达
4. 再评估是否需要把 runtime 拆成更明显的 watcher / handler 结构

具体迁移项见 [browser-use-migration-todo.md](/F:/AgentBot/docs/architecture/browser-use-migration-todo.md)。
