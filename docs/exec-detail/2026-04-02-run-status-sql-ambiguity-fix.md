# 2026-04-02 Run Status SQL Ambiguity Fix

## 问题现象

出现了两个看起来像前端问题、但实际根因在后端持久化层的症状：

1. 新建对话后，第一次提问时，正文在流式过程中能看到，但结束后历史里直接消失。
2. 后续提问会出现 `network error`，同时 run UI 显示失败或卡在异常状态。

## 实际根因

问题出在：

- [runs.py](F:/AgentBot/agentbot/storage/repositories/runs.py)

`RunRepository.get()` 在查询 `runs` 和 `run_steps` 的聚合结果时，SQL 使用了：

```sql
WHERE run_id = ?
```

但这条查询本身做了：

```sql
FROM runs
LEFT JOIN run_steps ON run_steps.run_id = runs.run_id
```

因此 `run_id` 变成了歧义列，SQLite 在运行时会抛出：

```text
sqlite3.OperationalError: ambiguous column name: run_id
```

## 为什么这会导致前端看到 `network error`

`RunRepository.update_status()` 内部会先调用 `get(run_id)`。

所以一旦 `get()` 因歧义列报错，下面两个关键路径都会被打断：

1. `RuntimeShadowWriter.complete_run()`
2. `RuntimeShadowWriter.fail_run()`

这会造成：

- run 无法从 `running` 更新到 `completed` 或 `failed`
- assistant transcript message 无法稳定提交
- SSE 流在尾部异常中断
- 前端只能看到连接被打断后的 `network error`

这正好解释了：

- 首轮新对话里回答看得到但最后消失
- 历史消息只剩 user message
- `runs` 表里多条 run 长时间停留在 `running`

## 修复

把歧义条件改成显式表名前缀：

```sql
WHERE runs.run_id = ?
```

修改文件：

- [runs.py](F:/AgentBot/agentbot/storage/repositories/runs.py)

## 验证

执行了两类验证：

1. 直接用本地 SQLite 主库验证 `RunRepository.get()` 和 `RunRepository.update_status()`：
   - `get()` 正常返回
   - `update_status()` 正常执行

2. 前端构建验证：
   - `npm run build` 通过

## 结论

这次故障不是 execution panel 样式或前端列表渲染逻辑导致的主问题。

主问题是：

- run 终态写回被 SQL 歧义列错误打断
- 进而破坏了 transcript 落盘和 SSE 收尾

修复这条 SQL 之后，前端才有机会拿到正确的 persisted run 和 assistant transcript。
