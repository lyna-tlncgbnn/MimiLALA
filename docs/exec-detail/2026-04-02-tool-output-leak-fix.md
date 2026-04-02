# 2026-04-02 Tool Output Leak Fix

## 背景

在新的 run-centric UI 下，用户询问目录内容时，最终 `Agent` 正文直接出现了工具原始输出，例如：

- `dir: ui\\dist`
- `file: ui\\package.json`

这类内容属于内部工具返回格式，不应该直接暴露为最终用户答案。

## 根因

问题主要在后端回答质量，而不是前端渲染：

1. `list_directory` 工具返回的是偏内部协议的原始标记格式，包含 `dir:` / `file:` 前缀。
2. system prompt 对“最终回答必须转成用户可读表达”的约束不够强，导致模型可能直接复述工具原文。

## 本次修复

### 1. 收敛 `list_directory` 的输出格式

文件：

- `agentbot/tools/filesystem.py`

原来返回：

- `dir: ...`
- `file: ...`

现在改为更结构化的摘要：

- `Directory: ...`
- `Subdirectories (N):`
- `Files (N):`
- 使用 `- path` 列表项列出结果

这样即使模型引用工具结果，最终呈现也不会再暴露内部风格的 `dir:` / `file:` 标记。

### 2. 收紧最终回答约束

文件：

- `agentbot/prompts/system.py`

新增要求：

- 不要直接转储 raw tool output
- 不要暴露内部 tool formatting
- 文件系统结果需要转成自然语言或按“目录 / 文件”分组的可读列表

## 影响范围

- 同步运行路径 `runner.py`
- 流式运行路径 `streaming_runner.py`

这两条路径都会读取同一份 system prompt，也都会消费相同的 `list_directory` 工具输出。

## 验证

已完成：

- Python 导入检查通过
- 前端 `npm run build` 通过

## 后续观察点

如果后续仍出现其他工具的“原始协议内容”泄漏到最终回答，需要继续按同样思路处理：

1. 先检查工具返回格式是否过于底层
2. 再检查 system prompt 是否缺少对最终回答格式的明确约束
3. 仅在必要时，再补更强的后处理兜底
