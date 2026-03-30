# 2026-03-30 Desktop App Foundation Phase 1

## 本次执行目标

本次执行围绕 `docs/exec-plans/active/desktop-app-foundation.md` 先完成桌面应用基础设施的第一阶段落地，重点是：

- 搭建 Python 服务化入口
- 建立首版 conversation API
- 建立单前端 React 页面骨架
- 建立 Electron 桌面壳骨架

当前阶段按照用户要求：

- 只有一套前端页面
- Electron 负责把这套前端页面装进桌面窗口
- 前端界面视觉参考 `F:\nanobot\ui`
- 去掉参考项目中的右侧定时任务栏

## 本次实际完成内容

### 1. 新增 Python service 层

新增目录与文件：

- `agentbot/services/__init__.py`
- `agentbot/services/conversations.py`
- `agentbot/services/chat.py`

职责：

- `ConversationService` 负责 conversation CRUD 和消息历史读取
- `ChatService` 负责在指定 conversation 上发送消息并回收最新状态

这样 API 层不再直接拼接底层 store 和 runner，后续 CLI 与 API 可以复用同一层业务语义。

### 2. runner 支持指定 conversation_id

修改文件：

- `agentbot/app/runner.py`

本次改动：

- `run_once()` 新增 `conversation_id: str | None = None`
- 不传时继续走默认会话
- 传入时可以在指定 conversation 上继续对话

这一步是后续 API `send_message_to_conversation` 的关键基础。

### 3. 新增 FastAPI 应用与 API 路由

新增目录与文件：

- `agentbot/api/__init__.py`
- `agentbot/api/app.py`
- `agentbot/api/schemas.py`
- `agentbot/api/serializers.py`
- `agentbot/api/routes/__init__.py`
- `agentbot/api/routes/health.py`
- `agentbot/api/routes/conversations.py`

当前提供的接口包括：

- `GET /health`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `PATCH /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `GET /api/conversations/{conversation_id}/messages`
- `POST /api/conversations/{conversation_id}/messages`

这些接口已经覆盖桌面端首屏需要的最小 conversation 语义。

### 4. Python 依赖补充

修改文件：

- `pyproject.toml`
- `uv.lock`

新增依赖：

- `fastapi`
- `uvicorn`

### 5. 新增 React 前端工程

新增目录与文件：

- `ui/package.json`
- `ui/tsconfig.json`
- `ui/tsconfig.node.json`
- `ui/vite.config.ts`
- `ui/index.html`
- `ui/src/main.tsx`
- `ui/src/App.tsx`
- `ui/src/styles.css`
- `ui/src/lib/api.ts`
- `ui/src/lib/utils.ts`
- `ui/src/stores/ui-store.ts`

当前前端技术方案为：

- React 19
- TypeScript
- Vite
- React Router
- Tailwind CSS 4
- React Query
- Zustand
- Zod
- React Markdown
- Remark GFM

### 6. 新增前端页面骨架与样式

新增目录与文件：

- `ui/src/components/ui/button.tsx`
- `ui/src/components/ui/dialog.tsx`
- `ui/src/components/ui/scroll-area.tsx`
- `ui/src/components/chat/message-content.tsx`
- `ui/src/components/chat/message-card.tsx`
- `ui/src/components/layout/sidebar-panel.tsx`
- `ui/src/components/layout/chat-panel.tsx`
- `ui/src/components/layout/settings-dialog.tsx`
- `ui/src/components/layout/rename-dialog.tsx`
- `ui/src/components/layout/app-shell.tsx`

当前界面已经具备：

- 左侧会话列表
- 新建会话
- 切换会话
- 重命名会话
- 删除会话
- 中间聊天区
- 底部输入框
- 最小设置弹窗
- Markdown 渲染消息内容

视觉方向参考了 `F:\nanobot\ui` 的：

- 米白背景
- 浅棕强调色
- 左侧细边栏/展开侧栏结构
- 中间聊天面板视觉风格

同时去掉了参考项目里的右侧任务面板。

### 7. 新增 Electron 桌面壳骨架

新增目录与文件：

- `desktop/package.json`
- `desktop/electron/main.js`
- `desktop/electron/preload.js`

当前 Electron 壳负责：

- 创建桌面窗口
- 加载 React 前端页面
- 启动本地 FastAPI 子进程
- 退出时关闭后端子进程

## 本次验证

### 1. FastAPI 路由验证

使用 `fastapi.testclient.TestClient` 验证了：

- `/health`
- conversation 列表
- conversation 创建
- conversation 详情读取
- conversation 重命名
- conversation 删除

这些接口均可正常工作。

### 2. Python 编译验证

运行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果通过。

### 3. 前端构建验证

运行：

```powershell
npm run build
```

工作目录：

- `F:\AgentBot\ui`

结果通过，Vite 成功产出构建文件。

### 4. Electron TypeScript 构建验证

运行：

```powershell
npm run build
```

工作目录：

- `F:\AgentBot\desktop`

结果通过，说明桌面壳入口代码可以正常通过当前校验步骤。

### 5. Electron 实际启动验证

用户后续在本地完成了 `desktop` 目录下的 Electron 依赖安装，并实际执行：

```powershell
npm run dev
```

验证结果：

- Electron 桌面窗口可以启动
- 桌面窗口可以加载 React 前端页面
- 前端页面中的会话相关操作经过人工测试没有发现明显问题

## 当前限制

当前阶段仍然保持以下边界：

- 没有加入 streaming
- 没有加入 execution 可视化面板
- 没有加入复杂设置系统
- 没有加入自动更新、多窗口或系统托盘
- 没有加入 browser / shell / MCP 等高级桌面集成

## 当前结果

截至本次执行结束，项目已经具备：

- 本地 FastAPI 服务入口
- conversation CRUD API
- send message API 入口
- 单前端 React 页面骨架
- 参考 nanobot UI 风格的首版桌面前端布局
- Electron 桌面壳
- 已可实际启动的桌面窗口与本地前后端联通链路

也就是说，桌面基础设施的主体分层已经形成：

- Electron：桌面壳
- React：唯一前端页面
- FastAPI：本地服务入口
- Python 核心逻辑：继续复用现有 Agent / persistence / tools

## 建议给后续阶段的动作

后续如果继续推进，建议优先处理：

1. `POST /api/conversations/{conversation_id}/messages` 的真实模型调用验证与异常态打磨
2. 前端对发送中、错误态、空状态的进一步打磨
3. README 与 architecture 文档同步更新
4. execution 可视化与更完整的设置入口
