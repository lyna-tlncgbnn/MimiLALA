# Frontend Architecture

## 当前目标

当前前端不是一个独立部署的 Web 产品，而是桌面应用中的渲染层。
它运行在 Electron 窗口中，通过本地 FastAPI 服务访问后端能力。

整体关系如下：

```text
Electron Shell
  -> React UI
    -> FastAPI Local API
      -> Agent / Persistence / Tools
```

当前前端的核心职责是：

- 展示会话列表与消息内容
- 提供聊天输入和流式返回体验
- 调用本地 API 完成会话 CRUD 与消息发送
- 管理少量本地 UI 状态

当前前端不负责：

- 直接调用 Python 对象
- 直接读写本地 conversation 文件
- 桌面窗口生命周期管理

## 当前目录结构

前端相关代码主要分布在以下目录：

```text
ui/
  src/
    app/
      App.tsx
      app-shell.tsx
      main.tsx
      styles.css
    assets/
      logos/
    features/
      chat/
        components/
        layout/
      conversations/
        components/
      settings/
        components/
    shared/
      api/
      lib/
      ui/
    state/
      ui-store.ts
    vite-env.d.ts
  index.html
  vite.config.ts

desktop/
  electron/
    main.js
    preload.js
```

## 分层说明

### `ui/src/app`

应用入口层。

负责：

- React 应用挂载
- Router 定义
- QueryClient 注入
- 页面全局壳子组织
- 全局样式入口

当前主要文件：

- `ui/src/app/main.tsx`
- `ui/src/app/App.tsx`
- `ui/src/app/app-shell.tsx`
- `ui/src/app/styles.css`

### `ui/src/features`

按业务域组织的前端功能模块。

当前拆分为：

- `features/chat`
  负责聊天消息渲染、输入框、聊天顶部控制条
- `features/conversations`
  负责侧边栏、会话列表、会话项、重命名弹窗
- `features/settings`
  负责设置弹窗

这种分层的目标是把“功能域”聚合，而不是把所有组件都按视觉位置堆在一个 `components/` 目录里。

### `ui/src/shared`

跨业务域复用的公共层。

包括：

- `shared/ui`
  通用 UI 基础组件，如 `button`、`dialog`、`scroll-area`
- `shared/lib`
  通用工具函数
- `shared/api`
  API 请求与响应结构定义

### `ui/src/state`

全局前端状态。

当前使用 `zustand`，主要用于：

- 侧边栏展开/收起
- 侧边栏宽度
- 设置弹窗开关
- 重命名目标会话 id

当前 store 位于：

- `ui/src/state/ui-store.ts`

## 页面与路由

当前前端仍然围绕一个主界面运行，使用 `HashRouter`：

- `/`
- `/conversations/:conversationId`

路由定义位于：

- `ui/src/app/App.tsx`

本质上仍然是同一个桌面主界面，只是随着 `conversationId` 变化切换当前会话。

## 主界面结构

当前主界面由 `AppShell` 组织：

- `ui/src/app/app-shell.tsx`

页面由两部分组成：

### 左侧：Conversation Sidebar

主要文件：

- `ui/src/features/conversations/components/sidebar-panel.tsx`
- `ui/src/features/conversations/components/sidebar-conversation-list.tsx`
- `ui/src/features/conversations/components/sidebar-conversation-row.tsx`

负责：

- 展示会话列表
- 新建会话
- 选择会话
- 重命名会话
- 删除会话
- 打开设置
- 侧边栏宽度调整

当前交互特点：

- 侧边栏可展开/收起
- 收起后左侧栏完全隐藏，不保留窄缝
- 会话项使用 `...` 菜单承载重命名与删除
- 侧边栏宽度可拖拽，并受最小/最大值约束

### 右侧：Chat Surface

主要文件：

- `ui/src/features/chat/layout/chat-panel.tsx`
- `ui/src/features/chat/layout/chat-header.tsx`
- `ui/src/features/chat/components/message-list.tsx`
- `ui/src/features/chat/components/chat-composer.tsx`

负责：

- 聊天顶部控制区
- 消息列表展示
- 空状态展示
- 输入框与发送动作
- 错误提示
- 流式消息过程中的界面反馈

当前结构上，聊天区已经拆成：

- `ChatHeader`
- `MessageList`
- `ChatComposer`

这样后续如果要继续扩展顶部区域，例如标题、更多按钮、模式切换，会更自然。

## 状态管理

当前前端状态可以分为三类：

### 1. 远程数据状态

使用 `@tanstack/react-query` 管理，主要包括：

- 会话列表查询
- 单个会话详情查询
- 创建会话
- 重命名会话
- 删除会话

### 2. 本地 UI 状态

使用 `zustand` 管理，主要包括：

- `sidebarCollapsed`
- `sidebarWidth`
- `settingsOpen`
- `renameTargetId`

### 3. 临时流式状态

流式聊天主链路不只依赖后端最终落库后的 `messages`，前端还维护一层临时消息状态，用于承载：

- optimistic user message
- waiting assistant placeholder
- streaming assistant message
- tool running 状态
- tool output 消息

流结束后，这层临时状态会被最终 conversation 数据覆盖。

## API 访问层

前端访问后端 API 的入口位于：

- `ui/src/shared/api/api.ts`

这一层负责：

1. 统一发起 `fetch`
2. 用 `zod` 校验返回结构
3. 解析 `SSE` 事件流

当前主要方法包括：

- `listConversations()`
- `createConversation()`
- `getConversation()`
- `renameConversation()`
- `deleteConversation()`
- `sendMessage()`
- `streamMessage()`

## 运行方式

当前前端由 Vite 驱动。

开发阶段：

- React 页面由 Vite dev server 提供
- Electron 加载本地 Vite 地址
- Electron main 进程同时启动本地 FastAPI

默认连接关系：

- React UI: `http://127.0.0.1:5173`
- FastAPI: `http://127.0.0.1:8000`

页面入口文件：

- `ui/index.html`
- `ui/src/app/main.tsx`

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

当前 preload 仍然保持最小桥接，不承担业务逻辑。
也就是说：

- 前端业务仍然是标准 React + HTTP 结构
- Electron 主要是运行容器，而不是业务层

## 当前验证状态

当前桌面前端链路已经完成以下验证：

- Vite 前端可构建
- Electron 可加载当前前端页面
- 本地 FastAPI 接口可工作
- 会话 CRUD 主链路可用
- SSE streaming chat 主链路可用
- 侧边栏宽度与展开收起交互可用

## 当前边界

当前前端架构明确不包含：

- 浏览器版独立产品
- 多窗口 UI
- execution 可视化面板
- 复杂设置系统
- 直接操作 Python 本地文件
- MCP / browser / shell 等高级交互界面

## 可扩展方向

在当前结构下，后续更自然的扩展方向包括：

- 增加 execution 日志面板
- 增加更完整的 streaming 事件展示
- 增加更丰富的顶部控制区
- 增加 conversation 搜索与筛选
- 增加更完整的 settings 面板
- 增加品牌资源、空状态与消息展示的统一设计系统
