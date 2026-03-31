# UI Frontend

这是桌面应用中的 React 渲染层，运行在 Electron 窗口中，通过本地 FastAPI 服务访问后端能力。

如果你是第一次进入这个目录，建议先看：

- `package.json`：前端脚本与依赖
- `src/app/`：应用入口与应用壳
- `src/features/`：按业务域拆分的功能模块
- `src/shared/`：跨业务复用的通用层
- `../docs/architecture/frontend.md`：更完整的前端架构说明

## 运行方式

开发：

```powershell
npm run dev
```

构建：

```powershell
npm run build
```

预览：

```powershell
npm run preview
```

默认开发地址：

- UI：`http://127.0.0.1:5173`
- Backend API：`http://127.0.0.1:8000`

## 当前目录结构

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
  package.json
  vite.config.ts
```

## 分层约定

### `src/app`

放应用级入口与总装配：

- React 挂载
- Router
- QueryClient
- 应用壳布局
- 全局样式

### `src/features`

按业务功能组织，而不是按“页面位置”随意堆组件。

当前包括：

- `features/chat`
- `features/conversations`
- `features/settings`

后续新增功能时，优先判断它属于哪个业务域，再决定是否新建 feature。

### `src/shared`

放跨业务复用的内容：

- `shared/ui`：通用 UI 基础组件
- `shared/lib`：通用工具函数
- `shared/api`：API 请求与数据结构

只有明确会被多个 feature 复用的内容，才应该放到这里。

### `src/state`

放全局前端状态。

当前使用 `zustand`，主要承载：

- 侧边栏展开/收起
- 侧边栏宽度
- 设置弹窗开关
- 当前重命名目标

## 现在前端负责什么

- 会话列表展示
- 聊天消息展示
- 聊天输入与发送
- 会话创建 / 切换 / 重命名 / 删除
- SSE 流式消息展示
- 少量本地 UI 状态管理

## 现在前端不负责什么

- 直接调用 Python 对象
- 直接读写本地 conversation 文件
- 桌面窗口生命周期
- execution 可视化面板
- 多窗口管理

## 常改位置

如果你想改：

- 应用整体布局：`src/app/app-shell.tsx`
- 聊天顶部与输入区：`src/features/chat/layout/`、`src/features/chat/components/`
- 侧边栏与会话列表：`src/features/conversations/components/`
- 设置弹窗：`src/features/settings/components/`
- API 请求：`src/shared/api/api.ts`
- 全局样式变量：`src/app/styles.css`
- UI 状态：`src/state/ui-store.ts`

## 当前实现特点

- 使用 `HashRouter`
- 使用 `@tanstack/react-query` 管理远程数据
- 使用 `zustand` 管理本地 UI 状态
- 使用 `zod` 校验 API 返回结构
- 使用 SSE 做流式聊天
- 侧边栏支持展开/收起与宽度拖拽

## 修改约定

- 优先做小步、可运行的改动
- 新代码优先放到对应的 feature 目录
- 不要把业务组件继续堆回 `shared/`
- 如果结构变化影响了目录或职责，请同步更新：
  - `ui/README.md`
  - `docs/architecture/frontend.md`

## 备注

当前品牌资源已经切换到 `MiniLALA`，logo 位于：

- `src/assets/logos/minilala-wordmark-wide-transparent.png`
