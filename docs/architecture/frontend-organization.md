# 前端代码组织说明

## 文档目的

这份文档描述的是 `ui/` 前端当前的组织方向、已经完成的重构结果，以及后续继续整理时应遵守的边界。

它不是“理想化模板”，而是面向当前 AgentBot 前端现状的约束说明。目标不是把所有代码一次性改成某种教科书结构，而是在保证主链路稳定可运行的前提下，让前端继续往更清晰、可维护、可扩展的方向演进。

当前前端已经不再是早期单页 demo，而是承担以下职责：

- 展示 conversation transcript
- 展示 active run
- 展示 historical runs 与 run steps
- 发起聊天请求与流式更新
- 管理侧边栏、设置弹窗、重命名弹窗等本地 UI 状态

因此，前端结构的核心问题已经不再是“组件多不多”，而是：

- 页面装配逻辑是否过重
- 业务边界是否清晰
- API、query key、状态转换是否收口
- 大组件是否被拆成可理解的层级

## 当前组织目标

前端整体正在向下面这种分层方式收敛：

```text
app/
  负责应用入口、页面装配、全局配置、路由级结构

features/
  负责具体业务域的 UI、hook、feature-local 工具函数与 API

shared/
  负责无业务语义的通用能力，例如 HTTP、SSE、基础 UI、通用工具

state/
  负责全局客户端状态（当前仍使用该目录名，后续如有必要可再统一迁为 stores/）
```

这个方向的重点不是“目录一定要长成某个样子”，而是下面几条边界：

- `app/` 负责装配，不负责堆业务细节
- `features/` 按业务归属代码，而不是按技术类型平铺所有文件
- `shared/` 只放可跨 feature 复用、且不带业务语义的能力
- 全局客户端状态与服务端查询状态分开处理

## 当前主要目录归属

基于现在已经完成的重构，前端关键目录可按下列方式理解。

### `ui/src/app/`

这里放应用级别的装配代码，而不是具体业务实现。

当前重点包括：

- `app-shell.tsx`
  页面级装配入口，负责把侧边栏、聊天区、弹窗拼起来
- `config/env.ts`
  应用级配置入口
- `main.tsx`
  前端启动入口

这里的原则是：

- 可以知道“有哪些页面结构块”
- 可以做顶层 provider、路由、应用配置
- 不应该直接堆太多会话管理、流式状态机、run 事件处理细节

### `ui/src/features/chat/`

这里承载聊天主链路相关的前端代码。

当前已经形成几层：

- `api/`
  聊天相关接口、schema、query keys
- `components/`
  聊天相关展示组件
- `hooks/`
  聊天页面 orchestration hook
- `lib/`
  聊天 feature 内部的状态转换、数据整理、小工具函数
- `renderers/`
  富文本渲染能力层
- `types/`
  聊天 feature 内部类型

这里的核心原则是：

- 聊天 feature 内部尽量自洽
- 聊天特有的 API、query key、run 状态转换不要散到 `shared/`
- 页面控制逻辑尽量放进 hook，而不是直接堆在页面组件里

### `ui/src/features/conversations/`

这里承载会话列表及其管理能力。

典型职责包括：

- 会话列表读取
- 会话创建、重命名、删除
- 侧边栏展示
- 会话列表项组件

它和 `chat/` 的关系是：

- `conversations/` 更偏会话管理
- `chat/` 更偏当前会话内容与运行态展示

这两个 feature 之间可以协作，但应尽量避免代码职责混杂。

### `ui/src/features/settings/`

当前设置功能还比较轻，主要是一个入口和展示壳。

这里暂时不需要过度抽象，但仍然建议保持：

- 组件归属于 settings feature
- 不要把设置相关文案和展示逻辑散落到 `app/` 或 `chat/`

### `ui/src/shared/`

这里放的是通用能力，而不是“没人知道该放哪儿的代码回收站”。

当前主要包括：

- `shared/api/http-client.ts`
  通用 JSON 请求
- `shared/api/sse.ts`
  通用 SSE 读取能力
- `shared/ui/*`
  基础 UI 原子组件
- 通用工具函数

判断标准是：

- 如果一个模块脱离当前业务语境仍然成立，才适合放 `shared/`
- 如果它天然带有“chat / conversation / run”的领域语义，就应该留在 feature 内

### `ui/src/state/`

这里目前承载全局客户端 UI 状态，例如：

- 侧边栏是否收起
- 侧边栏宽度
- 设置弹窗开关
- 重命名目标 ID

当前虽然目录名还是 `state/`，但语义上它更接近 global client store。

后续如果全局状态继续增长，可以再评估是否统一迁到 `stores/`。但在当前阶段，这不是优先级最高的问题，优先级更高的是先把状态职责边界保持清楚。

## 已完成的关键重构

这部分记录当前已经完成、并且应继续保留的组织方向。

### 1. API 层拆分

原来的 `ui/src/shared/api/api.ts` 同时承担了太多职责：

- schema
- 类型导出
- fetch 请求
- streaming
- feature-specific API
- SSE 解析

这会导致任何接口变更都牵动整文件，也让 API 层无法清楚区分“通用传输层”和“业务接口层”。

当前已经拆成：

- `ui/src/app/config/env.ts`
- `ui/src/shared/api/http-client.ts`
- `ui/src/shared/api/sse.ts`
- `ui/src/features/conversations/api/*`
- `ui/src/features/chat/api/*`

这意味着：

- `shared/api/` 只保留通用传输能力
- 具体接口按 feature 归属
- query keys、schema 和 feature API 更容易一起维护

### 2. Query Key 收口

查询 key 不再应该散落在页面和组件里直接写字符串数组。

当前已经按 feature 收口到：

- `ui/src/features/conversations/api/conversations-query-keys.ts`
- `ui/src/features/chat/api/chat-query-keys.ts`

这样做的价值是：

- query invalidation 更稳定
- cache 地址更清晰
- 后续修改接口或 query 结构时，不需要全局搜裸字符串

### 3. 页面 orchestration 从 `app-shell` 抽离

`app-shell.tsx` 不应该演变成一个“把所有行为都写进去的大控制器”。

当前已经完成的拆分是：

- `ui/src/app/app-shell.tsx`
  保留为页面装配层
- `ui/src/features/chat/hooks/use-conversation-screen.ts`
  承担页面 orchestration
- `ui/src/features/chat/lib/active-run-state.ts`
  承担流式 run 状态转换

现在 `app-shell` 的主要职责是：

- 读取页面级 hook 返回的数据和事件
- 装配 `SidebarPanel`
- 装配 `ChatPanel`
- 装配对话框

而 `use-conversation-screen.ts` 负责：

- 当前 conversation route 派生
- React Query 查询
- create / rename / delete conversation mutation
- draft 状态
- send 流程
- active run 状态
- stream error 与 stream phase
- 与全局 UI store 协调

这个拆分是当前前端组织里最重要的一个边界，应继续保持。

### 4. 大型 feature container 拆分

`conversation-run-list.tsx` 原先承担了过多职责，包括：

- empty state
- active run
- historical runs
- step mapping
- 小组件定义
- 文案与格式化逻辑

现在已经拆成：

- `conversation-run-list.tsx`
  薄组合容器
- `active-run-section.tsx`
- `historical-run-section.tsx`
- `user-prompt.tsx`
- `agent-section.tsx`
- `execution-hint.tsx`
- `conversation-empty-state.tsx`
- `conversation-run-list-utils.ts`

这个方向说明一个明确原则：

- 大组件优先拆成“组合容器 + 子组件 + utils”
- 不要让一个文件同时承担页面逻辑、展示、映射和文案全部职责

### 5. 富文本渲染层独立

assistant 回答展示已经不再只是一层简单字符串渲染。

当前已经形成独立的 renderer 层：

- `renderers/markdown-renderer.tsx`
- `renderers/code-block.tsx`
- `renderers/rich-content-renderer.tsx`
- `renderers/markdown-theme.css`

这里的意义是：

- 富文本渲染不再散落在普通消息组件里
- markdown / code / math / table 样式可以独立演进
- 后续如果接更多内容类型，扩展点更明确

## 当前推荐的数据流

对当前聊天页面，推荐按下面这条流理解：

```text
AppShell
  -> useConversationScreen
    -> feature APIs + React Query
    -> ui-store
    -> active-run-state helpers
  -> SidebarPanel / ChatPanel / dialogs
    -> subcomponents
    -> rich content renderers
```

再展开一点，可以理解成三层状态：

### 1. 服务端查询状态

由 React Query 管理，例如：

- conversation list
- current conversation transcript
- conversation runs

这类状态应优先留在 query 层，不要重复拷贝一份到全局 store。

### 2. 页面运行态状态

由页面 hook 管理，例如：

- draft
- activeRun
- streamPhase
- streamError

这类状态有明显页面上下文，不应该提前抽成全局 store。

### 3. 全局客户端 UI 状态

由 zustand store 管理，例如：

- sidebarCollapsed
- sidebarWidth
- settingsOpen
- renameTargetId

这类状态跨组件共享，但不属于后端数据。

## 目录与职责的判断规则

后续新增文件时，可以按下面的判断规则来决定放哪儿。

### 什么时候放到 `app/`

放到 `app/` 的前提是它属于应用装配层，例如：

- 应用入口
- 顶层 provider
- 页面壳层
- 应用级配置

如果一段逻辑明显知道“conversation、run、chat message”这些业务语义，那么通常就不该留在 `app/`。

### 什么时候放到 `feature/api`

满足下面任一条件时，优先放到 feature 的 `api/`：

- 接口只服务某个 feature
- schema 与该 feature 强绑定
- query keys 与该 feature 强绑定

只有纯通用传输逻辑才留在 `shared/api/`。

### 什么时候放到 `feature/hooks`

适合放到 `feature/hooks/` 的通常是：

- 页面 orchestration
- 多个组件共享的业务逻辑
- 与具体 feature 数据流强相关的 hook

不建议把“只是为了抽而抽”的非常薄的一层包成 hook。

### 什么时候放到 `feature/lib`

适合放到 `feature/lib/` 的通常是：

- 状态转换函数
- 映射函数
- 格式化逻辑
- 只服务当前 feature、但不直接依赖 React 的工具函数

这里应尽量保持“可测试的纯逻辑”属性。

### 什么时候放到 `shared/`

只有满足下面条件时才放到 `shared/`：

- 可以跨 feature 复用
- 不带 feature-specific 业务语义
- 抽出去后不会让代码更难理解

如果一个工具函数名字里已经带有明显的 chat / run / conversation 语义，就应该优先留在 feature 内。

## 当前不推荐的做法

为了避免后续整理再次走偏，这里明确写出当前不推荐的方向。

### 1. 不推荐把所有字面量都抽成 constants

不是所有“magic number”都应该被抽出去。

当前不推荐抽离这些内容：

- 单个组件里只出现一次的布局值
- 局部 Tailwind class
- 很直观的一次性字号或圆角
- 只在一个组件里使用的文案

原因是这类抽离经常会导致：

- 阅读时来回跳文件
- JSX 失去直观性
- 本地样式意图被过度抽象
- 常量文件变成杂物堆

### 2. 不推荐让页面组件重新变重

新的功能不应再直接堆回 `app-shell.tsx` 这类页面壳层。

优先顺序应该是：

- 先想是否属于页面 hook
- 再想是否属于 feature-local lib
- 最后才考虑是否必须留在页面组件本身

### 3. 不推荐把业务逻辑提前塞进 `shared/`

`shared/` 不是为了“看起来通用”而存在。

过早把业务逻辑搬进 `shared/`，往往会：

- 削弱 feature 边界
- 增加命名模糊性
- 让后续维护者搞不清归属

## 当前推荐的整理策略

在已经完成前几轮重构之后，后续前端继续整理时，推荐采用下面的顺序。

### 第一优先级：保证用户可见层稳定

优先处理：

- 乱码文案
- 明显错误的展示
- 死代码
- 过重的大组件

### 第二优先级：继续压缩过重文件

当前继续值得整理的文件通常包括：

- `message-card.tsx`
- `sidebar-panel.tsx`
- `run-steps-panel.tsx`

整理方式优先是：

- 提高清晰度
- 减少重复逻辑
- 明确局部职责

而不是先抽大量共享常量。

### 第三优先级：在有明确收益时再做更深的结构调整

例如：

- `state/` 是否迁到 `stores/`
- 某些 feature 是否还要再细分目录
- 是否增加更完整的页面目录结构

这些都属于可以做，但不是当前最高优先级的事项。

## 当前的过渡状态说明

当前前端仍有一些过渡性结构，这是正常的。

例如：

- `ui/src/shared/api/api.ts` 仍保留为兼容导出层
- `state/` 目录名尚未统一成 `stores/`
- 某些组件仍然偏大，但职责已经比以前清晰很多

这些过渡层的存在是为了：

- 避免一次性大搬迁带来过高风险
- 允许逐步迁移调用点
- 保持主链路稳定

因此，当前判断一个调整是否合理，不是看“结构有没有一步到位”，而是看：

- 是否让职责边界更清楚
- 是否降低后续继续整理的难度
- 是否避免为了形式统一而破坏当前可读性

## 目标状态

前端后续理想但务实的目标状态应是：

- 页面层保持薄
- feature 边界清楚
- API 与 query keys 按 feature 收口
- 状态流分成 query state、page state、global UI state 三层
- 富文本渲染作为独立能力层演进
- 大组件继续拆成组合容器与子模块
- 文档始终同步代码现状，而不是停留在旧结构描述

如果后续继续做前端整理，应以这份文档作为判断依据，而不是重新回到“所有东西都抽成共享模块”或“所有行为都塞回页面组件”这两种极端做法。
