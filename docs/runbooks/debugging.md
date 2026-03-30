# 调试说明

## 控制台 Debug 模式

把 `config.json` 里的 `debug` 设为 `true` 后，程序会在控制台打印简洁的 execution 摘要。

当前会输出的类别包括：

- conversation loaded
- tools registered
- graph started
- tool call emitted
- tool completed
- final answer
- run failed

## 持久化的运行结果

如果需要更深入地检查运行过程，可以直接看：

- `workspace/conversations/default.jsonl`
- `workspace/executions/default.jsonl`

## 当前限制

- 没有结构化 tracing backend
- 没有可视化 graph inspector
- 没有自动 replay 工具
