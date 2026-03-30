# Active Plan：Richer Tools

## 为什么下一步是它

当前项目已经具备：

- 稳定的 CLI 入口
- 可运行的 LangGraph loop
- 两个基础工具
- conversation 与 execution 的本地持久化

这意味着下一步最自然的方向就是扩展工具能力，因为 tool loop 本身已经被验证通了。

## 目标

在不改变核心 graph shape 的前提下，增加一小组更接近真实使用场景的工具。

## 约束

- 保持 CLI 仍然是唯一入口
- 除非确实有必要，否则继续使用 `MessagesState`
- 保持现有 `runner -> graph -> persistence` 主流程不变
- 在真正需要之前，不引入动态 tool discovery

## 候选方向

1. 增加一个只读的 filesystem tool，作用范围限制在项目 workspace 内
2. 增加一个参数 schema 更明确的结构化 utility tool
3. 改进 tool description，让模型更稳定地选择工具
4. 在继续扩展 tool surface 之前，先补最小测试

## 完成标准

- 至少增加一个更贴近真实使用场景的新工具
- tool registration 仍然保持集中管理
- conversation 与 execution logging 仍然正常工作
- README 与相关 docs 同步更新
