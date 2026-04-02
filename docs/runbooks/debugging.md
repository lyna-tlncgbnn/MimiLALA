# 调试说明

## 第一层：确认服务是否启动

先确认：

- FastAPI 已启动
- 前端已启动
- Electron 或浏览器页面已连接到本地 API

建议检查：

- `http://127.0.0.1:8000/api/health`

## 第二层：确认配置

检查根目录 `config.json` 是否存在且有效：

- `llm.api_key`
- `llm.base_url` 可选
- `llm.model`
- `debug`

如果模型配置无效，聊天主链路通常会在 runner / streaming runner 阶段失败。

## 第三层：看数据库

当前主数据已经不再在 JSONL 里。

优先检查：

- `workspace/agent_runtime.db`
- `workspace/langgraph_checkpoints.db`

你需要重点关注：

- `runs.status`
- `runs.final_message_id`
- `messages`
- `run_steps`

## 第四层：看运行链路位置

如果是同步链路问题，优先看：

- `agentbot/app/runner.py`

如果是流式链路问题，优先看：

- `agentbot/app/streaming_runner.py`
- `ui/src/shared/api/api.ts`
- `ui/src/app/app-shell.tsx`

## 第五层：看前端 read model

如果“正文有了但界面不对”，通常不是模型问题，而是前端 read model 切换问题。

优先看：

- `ui/src/features/chat/components/conversation-run-list.tsx`
- `ui/src/features/chat/components/run-steps-panel.tsx`

## debug 开关

将 `config.json` 中的 `debug` 设置为 `true`，可增强控制台调试输出。

## 当前已知排障原则

- 不要再默认把 JSONL 当主存储
- transcript 问题先看 `messages`
- 历史执行区问题先看 `runs` 和 `run_steps`
- checkpoint 问题先看 `langgraph_checkpoints.db`
