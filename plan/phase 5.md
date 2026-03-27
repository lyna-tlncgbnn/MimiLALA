# Phase 5 - Conversation Meta And Local Execution Logs

## Status

**DONE**

## Summary

Phase 5 的第一步先没有扩展更多平台能力，而是先把本地数据模型定稳：

- `conversation` 文件保存对话历史
- `execution` 文件保存执行事件
- 两者通过文件第一行的 `meta.conversation_id` 对齐

当前目录固定为：

```text
workspace/
  conversations/
    default.jsonl
  executions/
    default.jsonl
```

---

## 实际实施内容

本阶段已经完成：

- 将旧的 `session` 语义升级为 `conversation`
- 对话文件改为 `meta + message records`
- 执行文件改为 `meta + event records`
- 引入文件级 `conversation_id`
- 引入单次运行级 `execution_id`
- 让 execution events 默认本地落地
- 保留 `debug` 作为控制台展示层，而不是核心数据能力

---

## 数据结构约定

### conversations/default.jsonl

第一行：

```json
{"type":"meta","conversation_id":"conv_xxx","name":"default","created_at":"2026-03-27T13:00:00+08:00"}
```

后续每行：

```json
{"type":"message","message_id":"msg_xxx","timestamp":"2026-03-27T13:00:01+08:00","role":"user","content":"我叫张三"}
```

### executions/default.jsonl

第一行：

```json
{"type":"meta","conversation_id":"conv_xxx","name":"default","created_at":"2026-03-27T13:00:00+08:00"}
```

后续每行：

```json
{"type":"event","event_id":"evt_xxx","execution_id":"exec_xxx","timestamp":"2026-03-27T13:00:00+08:00","event":"graph_started"}
```

---

## 验收结果

Phase 5 这一小步已经满足：

- `conversations/default.jsonl` 和 `executions/default.jsonl` 会自动创建
- 两个文件第一行的 `conversation_id` 一致
- 每条消息都有 `message_id`
- 每条事件都有 `event_id`
- 同一次运行产生的事件共享同一个 `execution_id`
- graph 失败时也会写入失败事件
- 旧 `workspace/sessions/default.jsonl` 可迁移到新路径

---

## 下一步建议

基于当前数据模型，下一步最适合继续做：

**richer tools**

也就是在保留现有 conversation / execution 落地能力的前提下，增加更真实的工具能力。
