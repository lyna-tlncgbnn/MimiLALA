# 项目结构

## 当前整体分层

当前仓库已经不再只是一个 Python CLI 项目，而是形成了四层主体结构：

```text
desktop/   # Electron 桌面壳
ui/        # React 前端
agentbot/  # Python 后端核心
docs/      # 项目文档
```

## 运行入口

- `main.py`
  当前保留的 CLI 薄入口，只负责转到 `agentbot.app.cli`
- `agentbot/app/cli.py`
  CLI 参数处理与交互循环
- `agentbot/api/app.py`
  FastAPI 本地服务入口
- `desktop/electron/main.js`
  Electron 桌面应用入口

## Python 后端结构

### `agentbot/app/`

负责当前 CLI 与单轮运行调度：

- `cli.py`：CLI 入口与交互循环
- `runner.py`：单轮运行总调度
- `debug.py`：控制台 debug 输出

### `agentbot/api/`

负责 FastAPI 本地 API：

- `app.py`：FastAPI 应用创建
- `schemas.py`：请求/响应 schema
- `serializers.py`：API 序列化逻辑
- `routes/health.py`：健康检查路由
- `routes/conversations.py`：conversation 与消息相关路由

### `agentbot/services/`

负责把 API / CLI 需要的业务语义从底层 persistence 与 runner 中抽出来：

- `conversations.py`：conversation CRUD、消息历史读取、消息序列化
- `chat.py`：在指定 conversation 上发送消息并返回最新状态

### `agentbot/config/`

负责运行时配置：

- `settings.py`：读取并校验 `config.json`

### `agentbot/models/`

负责模型构造：

- `llm.py`：构造 `ChatOpenAI`

### `agentbot/prompts/`

负责 prompt 组织：

- `system.py`：提供当前 system prompt

### `agentbot/graph/`

负责 LangGraph 主循环：

- `state.py`：当前 graph state 类型
- `nodes.py`：chatbot 与 tool execution 节点
- `routes.py`：chatbot 之后的路由逻辑
- `builder.py`：graph 组装

### `agentbot/memory/`

负责本地 persistence：

- `conversation.py`：conversation storage 与多会话管理
- `execution.py`：execution event storage
- `session.py`：历史遗留模块，当前主流程不再依赖

### `agentbot/tools/`

负责工具定义与自动注册：

- `basic.py`：基础演示工具
- `filesystem.py`：文件相关工具
- `registry.py`：自动扫描并汇总 `TOOLS`

## 前端结构

### `ui/`

当前前端是一个独立的 React + Vite 工程。

关键文件与目录：

- `package.json`：前端依赖与脚本
- `vite.config.ts`：Vite 配置
- `src/main.tsx`：前端启动入口
- `src/App.tsx`：路由入口
- `src/styles.css`：全局样式与设计 token
- `src/lib/api.ts`：本地 API 访问层
- `src/lib/utils.ts`：通用前端工具函数
- `src/stores/ui-store.ts`：本地 UI 状态

### `ui/src/components/`

当前前端组件分为三层：

- `chat/`：消息卡片与 Markdown 内容渲染
- `layout/`：应用主框架、侧边栏、聊天区、对话框
- `ui/`：基础 UI 组件

## 桌面层结构

### `desktop/`

当前桌面端是一个独立的 Electron 工程。

关键文件：

- `package.json`：Electron 依赖与脚本
- `electron/main.js`：创建窗口、启动本地后端、加载前端页面
- `electron/preload.js`：preload 桥接层
- `tsconfig.json`：桌面工程 TypeScript 配置

## 数据目录

### `workspace/`

运行时数据继续落在仓库内：

```text
workspace/
  conversations/
    default.json
    <conversation_id>.jsonl
  executions/
    <conversation_id>.jsonl
```

其中：

- `conversations/` 保存会话历史
- `executions/` 保存执行事件
- `default.json` 记录当前 CLI 默认会话指向的 `conversation_id`

## 当前结构的意义

当前项目已经形成清晰分层：

- Electron 负责桌面壳
- React 负责界面
- FastAPI 负责本地 API
- Python 核心继续负责 Agent、persistence 和 tools

这套结构已经足够支撑后续继续扩展：

- execution 可视化
- streaming 交互
- 更完整的设置页
- 更丰富的桌面能力
