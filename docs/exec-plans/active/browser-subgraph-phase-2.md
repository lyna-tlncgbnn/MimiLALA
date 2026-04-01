# 执行计划：Browser Subgraph Phase 2

## 状态

ACTIVE

## 背景

`Browser Subgraph Phase 1` 已经完成了浏览器能力的最小可运行闭环，当前项目已经具备：

- 独立的 LangGraph 浏览器子图
- 显式浏览器任务服务入口
- `browser-use` 执行层的运行时桥
- 本地真实浏览器启动验证
- 结构化浏览器任务返回结果

当前浏览器能力已经证明架构方向成立，但它仍然主要是一个“可单独调用的浏览器能力入口”，还没有进入聊天主链路，也还不具备足够的最小可用动作集与过程可见性。

## 第二阶段目标

第二阶段的单一目标是：

**让浏览器子图进入聊天主链路，并补齐浏览器任务的最小可用能力。**

这里的“最小可用”具体指：

- 聊天主链路能够进入浏览器子图
- 浏览器子图支持比第一阶段更完整的最小动作集
- 前端或 SSE 能看见浏览器执行中的关键步骤
- 浏览器临时运行资源有更合理的清理策略

## 第二阶段不做什么

本阶段仍然明确不包含以下内容：

- 不做完整 multi-agent orchestration
- 不做多个浏览器子图并发
- 不做多 tab 复杂调度系统
- 不做 checkpointer
- 不做 long-term memory
- 不做 execution 可视化面板
- 不做完整自动化测试体系
- 不在本阶段强行把 `browser-use` 全量依赖收编进 `AgentBot`

## 第二阶段的核心问题

第一阶段之后，当前最明显的缺口有四个：

1. 浏览器子图还没有进入聊天主流程
2. 当前动作集太小，真实网页任务容易卡住
3. 浏览器执行过程对前端几乎不可见
4. 临时 profile 目录当前不会自动清理

因此，第二阶段不应该继续横向扩功能，而应该优先补这些“让功能真正可用”的缺口。

## 第二阶段范围

### 1. 接入聊天主链路

把浏览器子图从显式独立入口推进到聊天主图可调用能力。

目标不是一步做到完全自动路由，而是先打通以下任一条稳定路径：

- 显式 route 到浏览器子图
- 明确的聊天主链路包装节点调用浏览器子图
- 基于特定触发规则进入浏览器子图

推荐优先策略：

- 先由主图增加一个显式浏览器包装节点
- 保持父图和浏览器子图状态隔离
- 不在本阶段做复杂 supervisor 结构

### 2. 补齐最小可用动作集

在第一阶段现有动作基础上，第二阶段优先新增：

- `scroll`
- `wait`
- `extract`

优先级解释：

- `scroll` 是大多数页面继续推进的前提
- `wait` 是页面异步加载、跳转、弹层后的必要动作
- `extract` 是让浏览器任务能真正“带回结果”的关键

仍然不作为本阶段核心动作的包括：

- `switch_tab`
- `close_tab`
- `upload_file`
- `select_dropdown`
- 更复杂的复合动作

### 3. 暴露浏览器步骤事件

让当前 SSE 或前端至少能看到浏览器任务的关键节点状态，而不是只看到最终成功/失败。

建议最小事件集：

- `browser_subgraph_started`
- `browser_observed`
- `browser_action_planned`
- `browser_action_started`
- `browser_action_finished`
- `browser_subgraph_completed`
- `browser_subgraph_failed`

目标不是一次做成极细颗粒度，而是先让过程“可见”。

### 4. 收尾运行时卫生

把第一阶段保留下来的运行时阶段性问题收一轮。

优先包括：

- 临时 profile 默认自动清理
- 提供环境变量允许保留 profile 以便调试
- 浏览器启动失败错误分类更清楚
- 浏览器路径配置继续保留

## 核心决策

### 1. 仍然保留 LangGraph 作为唯一编排层

第二阶段仍然不引入 `browser-use` 的 agent loop。

### 2. 仍然保留双环境方案

本阶段仍然继续使用：

- `AgentBot` 主环境
- `browser-use` worker 环境

原因：

- 当前这套方式已经被本地验证可行
- 第二阶段重点是功能可用性，不是依赖治理
- 若此时切换依赖策略，会扩大改动面

### 3. 聊天主链路接入优先用包装节点

第二阶段推荐优先做：

- 聊天主图包装节点调用浏览器子图

而不是：

- 直接把浏览器状态大范围并入现有主图 state

这样可以继续维持边界清晰。

## 第二阶段文件级落地建议

### 1. 主图接入相关

预计修改：

- `agentbot/graph/builder.py`
- `agentbot/graph/nodes.py`
- `agentbot/graph/routes.py`

新增或补充一个包装节点，把浏览器子图接进主图。

### 2. 浏览器子图能力扩展

预计修改：

- `agentbot/models/browser.py`
- `agentbot/graph/browser_nodes.py`
- `agentbot/graph/browser_routes.py`
- `agentbot/services/browser_runtime.py`
- `agentbot/browser_worker.py`

这里主要承担：

- 新动作模型
- 新动作执行
- 更好的执行结果封装

### 3. streaming / API 事件扩展

预计修改：

- `agentbot/app/streaming_runner.py`
- `agentbot/services/chat.py`
- 视情况修改 API 返回事件结构

目标是让聊天流里能显式看到浏览器步骤。

### 4. 运行时清理策略

预计修改：

- `agentbot/browser_worker.py`
- `agentbot/services/browser_runtime.py`

这里主要承担：

- 默认自动删除临时 profile
- 通过环境变量保留 profile

## 第二阶段具体工作拆分

### Step 1：把浏览器子图接入聊天主图

目标：

- 聊天主链路可以进入浏览器子图

建议做法：

- 新增主图包装节点 `call_browser_subgraph`
- 从主图组装浏览器子图输入
- 执行子图
- 把结果转成主图可消费消息

验收：

- 在聊天入口中，可以通过明确触发方式进入浏览器能力

### Step 2：补齐 `scroll`

目标：

- 页面支持向下或向上推进

建议要求：

- 先支持最简单的页级 scroll
- 不在本阶段做元素级复杂滚动

验收：

- 常见长页面任务能够继续推进，而不是因为看不到元素立刻失败

### Step 3：补齐 `wait`

目标：

- 让页面跳转、异步加载、弹层变化后有等待能力

验收：

- 能处理简单延迟加载页面

### Step 4：补齐 `extract`

目标：

- 能把页面信息带回主链路，而不只是点击和输入

建议做法：

- 先做最基础页面内容提取
- 优先提取当前页面中的目标文本或摘要

验收：

- 浏览器任务可以完成“打开页面并返回页面标题/摘要/目标信息”

### Step 5：暴露浏览器步骤事件

目标：

- 前端或 SSE 至少可以看到关键浏览器执行步骤

建议做法：

- 先用节点级和动作级摘要事件
- 不一开始追求非常细的 token 级浏览器事件流

验收：

- 前端能看到浏览器任务在做什么，而不是只看到最终结果

### Step 6：补 profile 清理策略

目标：

- 避免 `workspace` 下积累过多临时 profile 目录

建议策略：

- 默认自动清理
- 环境变量 `AGENTBOT_KEEP_BROWSER_PROFILE=1` 时保留

验收：

- 默认运行结束后清理 profile
- 调试模式下可保留

## 第二阶段的动作规划策略

在动作集增加到 `scroll/wait/extract` 后，第二阶段仍然坚持以下收敛原则：

- 一次只规划一步动作
- 动作必须结构化
- 不做多动作 batch
- 优先可控性，不优先聪明程度
- 动作失败时优先返回清楚失败原因，而不是盲目重试

## 第二阶段的 streaming 策略

本阶段推荐只做到：

- 浏览器子图关键节点事件可见
- 浏览器动作开始与结束可见

不建议本阶段就做：

- 极细粒度浏览器内部事件全量透出
- 复杂 execution timeline UI

## 第二阶段的验收标准

### 主链路验收

- 聊天主流程能够进入浏览器子图
- 浏览器子图结果能够回到聊天主流程

### 动作能力验收

- `scroll` 可用
- `wait` 可用
- `extract` 可用

### 可见性验收

- 浏览器步骤事件可通过 SSE 或前端感知

### 运行时验收

- 临时 profile 默认自动清理
- 浏览器失败时错误信息明确

## 主要风险

### 风险 1：主图接入浏览器子图后影响现有聊天流程

应对：

- 优先显式触发或明确包装节点
- 避免一开始就做模糊自动路由

### 风险 2：动作集增加后 prompt 不稳定

应对：

- 继续严格约束动作结构
- 优先一步一动

### 风险 3：浏览器步骤事件过早做复杂

应对：

- 先做关键事件摘要
- 不在本阶段做完整可视化

## 本阶段完成定义

当以下条件同时满足时，可以认为 `Browser Subgraph Phase 2` 完成：

- 浏览器子图已进入聊天主链路
- `scroll` / `wait` / `extract` 至少以最小形式可用
- 浏览器关键步骤对前端或 SSE 可见
- 临时 profile 具备合理清理策略
- 文档同步更新

## 相关参考

- `docs/exec-detail/2026-03-31-browser-subgraph-phase-1-implementation.md`
- `docs/exec-plans/active/browser-subgraph-phase-1.md`
- `https://docs.langchain.com/oss/python/langgraph/use-subgraphs`
- `https://docs.langchain.com/oss/python/langgraph/streaming`
- `https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph`
