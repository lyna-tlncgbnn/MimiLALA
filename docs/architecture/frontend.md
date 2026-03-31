# Frontend Architecture

## 当前目标

当前前端不是一个独立部署的 Web 产品，而是桌面应用中的唯一界面层。

整体职责划分如下：

- `ui/`
  React 前端，负责页面渲染、交互和调用本地后端 API
- `desktop/`
  Electron 桌面壳，负责窗口管理和本地进程启动
- `agentbot/api/`
  FastAPI 本地服务，负责把 Python Agent 能力暴露给前端

因此，当前前端架构可以理解为：

```text
Electron Shell
  -> React UI
    -> FastAPI Local API
      -> Agent / Persistence / Tools
```

## 当前目录结构

前端相关代码主要分布在以下两个目录：

```text
ui/
  src/
    components/
      chat/
      layout/
      ui/
    lib/
    stores/
    App.tsx
    main.tsx
    styles.css
  index.html
  vite.config.ts

desktop/
  electron/
    main.js
    preload.js
```

## 分层职责

### `ui/`：React Renderer

`ui/` 是当前唯一的用户界面。

它负责：

- 会话列表展示
- 聊天消息展示
- 用户输入
- 会话创建、切换、重命名、删除
- Markdown 消息渲染
- 非流式与流式 API 调用
- streaming 状态的界面反馈

它不负责：

- 直接调用 Python
- 直接操作本地 conversation 文件
- 窗口管理

### `desktop/`：Electron Shell

`desktop/` 只负责桌面外壳。

它负责：

- 启动桌面窗口
- 加载 React 前端页面
- 启动本地 FastAPI 子进程
- 在应用退出时关闭后端进程

它不负责：

- 业务状态管理
- 会话逻辑
- conversation 持久化

### `agentbot/api/`：本地后端 API

前端并不直接接触 Python 业务对象，而是通过本地 API 访问：

- conversation 列表
- conversation 详情
- conversation CRUD
- send message
- stream message

这样做的好处是：

- 前端与 Agent 核心逻辑解耦
- Electron 与前端之间不需要直接共享复杂业务逻辑
- 后续如果继续增强 API server，这一层可以自然扩展

## 前端运行方式

当前前端由 Vite 驱动。

开发阶段：

- React 页面由 Vite dev server 提供
- Electron 加载本地 Vite 地址
- Electron main 进程同时启动本地 FastAPI

当前默认连接关系为：

- React UI 地址：`http://127.0.0.1:5173`
- FastAPI 地址：`http://127.0.0.1:8000`

## 页面组织

当前 React 页面围绕单个主界面展开。

路由定义在：

- `ui/src/App.tsx`

当前采用 `HashRouter`，主要页面包括：

- `/`
- `/conversations/:conversationId`

本质上仍然是同一个桌面主界面，只是切换不同 conversation。

## 核心页面骨架

当前主界面由 `AppShell` 组织，位于：

- `ui/src/components/layout/app-shell.tsx`

页面结构分为两部分：

### 左侧：SidebarPanel

位于：

- `ui/src/components/layout/sidebar-panel.tsx`

负责：

- 显示会话列表
- 新建会话
- 切换会话
- 触发重命名
- 触发删除
- 打开设置
- 侧栏收起/展开

### 中间：ChatPanel

位于：

- `ui/src/components/layout/chat-panel.tsx`

负责：

- 展示消息历史
- 展示空状态
- 输入框
- 发送按钮
- 错误提示
- streaming 状态显示

当前仍没有 execution 可视化面板或右侧详情面板。

## 状态管理

当前前端状态分为三类：

### 1. 远程数据状态

由 `@tanstack/react-query` 管理，负责：

- 会话列表查询
- 单个会话详情查询
- 创建会话
- 重命名会话
- 删除会话
- 非流式消息发送后的缓存刷新

### 2. 本地 UI 状态

由 `zustand` 管理。

当前 store 位于：

- `ui/src/stores/ui-store.ts`

当前保存的状态包括：

- `sidebarCollapsed`
- `settingsOpen`
- `renameTargetId`

### 3. 临时流式状态

streaming chat 主链路不再只依赖后端最终 `messages`，而是维护临时消息层，用来承载：

- optimistic user message
- waiting assistant 占位
- streaming assistant message
- tool running 状态
- tool 结果消息

在流结束后，这些临时状态会被最终 conversation 数据覆盖。

## API 访问层

前端访问后端 API 的入口位于：

- `ui/src/lib/api.ts`

这层负责：

1. 统一发起 `fetch`
2. 用 `zod` 校验返回结构
3. 解析 `SSE` 事件流

当前已经定义的主要 API 方法包括：

- `listConversations()`
- `createConversation()`
- `getConversation()`
- `renameConversation()`
- `deleteConversation()`
- `sendMessage()`
- `streamMessage()`

## 数据流

### 会话列表

1. `AppShell` 调用 `listConversations()`
2. React Query 缓存结果
3. `SidebarPanel` 消费格式化后的会话列表
4. 用户点击某个会话后，路由切换到对应 `conversationId`

### 非流式会话详情

1. `AppShell` 根据当前路由参数确定 `activeConversationId`
2. 调用 `getConversation(conversationId)`
3. `ChatPanel` 渲染消息列表

### 流式发送消息

1. 用户在 `ChatPanel` 输入内容
2. `AppShell` 调用 `streamMessage(conversationId, content)`
3. 前端先插入 optimistic user message，并清空输入框
4. 接收 `assistant_waiting` 后显示等待状态
5. 接收 `assistant_delta` 后持续追加 assistant 文本
6. 如果收到 `tool_started` / `tool_finished`，则更新 tool 状态与结果
7. 收到 `conversation_committed` / `done` 后重新拉取最终 conversation

## 消息渲染

消息显示拆成了两层：

- `message-card.tsx`
- `message-content.tsx`

### `message-card.tsx`

负责：

- 消息外壳
- 角色样式
- 卡片宽度
- 边框和背景层级
- waiting / tool running 等状态样式

### `message-content.tsx`

负责：

- assistant 消息的 Markdown 渲染
- 基础代码块
- 列表
- 链接
- 引用

当前规则是：

- assistant 消息按 Markdown 渲染
- user/tool 消息按纯文本渲染

## Electron 与前端的关系

Electron main 进程位于：

- `desktop/electron/main.js`

当前流程是：

1. Electron 启动时创建窗口
2. Electron 启动本地 FastAPI 子进程
3. BrowserWindow 加载 React 页面地址
4. React 页面通过 HTTP 请求本地 FastAPI

preload 位于：

- `desktop/electron/preload.js`

当前 preload 只暴露最小桥接能力，没有承担业务逻辑。

这意味着：

- 前端业务仍然是标准 React + HTTP 结构
- Electron 只是运行容器，不是业务层

## 当前验证状态

当前桌面前端链路已经完成以下验证：

- Vite 前端可以构建
- FastAPI 本地服务接口可以工作
- Electron 窗口可以实际启动
- Electron 可以加载当前 React 页面
- 会话 CRUD 主链路可用
- streaming chat 主链路可用

## 当前边界

当前前端架构明确不包含：

- 浏览器版独立产品
- 多窗口 UI
- execution 可视化面板
- 复杂设置系统
- 直接操作 Python 本地文件
- MCP、browser、shell 等高级交互界面

## 当前可扩展方向

在当前架构下，后续最自然的扩展方向包括：

- 增加 execution 日志页面
- 增加更完整的 streaming 体验
- 增加更完整的 settings 面板
- 增加 conversation 搜索与筛选
- 增加更丰富的消息卡片显示
