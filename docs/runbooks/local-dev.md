# 本地开发

## Python 依赖

推荐：

```powershell
uv sync
```

## 运行 CLI

```powershell
.\.venv\Scripts\python.exe main.py
```

运行单条输入：

```powershell
.\.venv\Scripts\python.exe main.py "你好"
```

## 启动 FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentbot.api.app:app --host 127.0.0.1 --port 8000
```

## 启动前端

```powershell
cd ui
npm install
npm run dev
```

## 启动 Electron

```powershell
cd desktop
npm install
npm run dev
```

## 当前开发建议

常见本地联调顺序：

1. 配好 `config.json`
2. 启动 FastAPI
3. 启动前端
4. 如需桌面体验，再启动 Electron

## 当前主要验证方式

目前仍以手工联调为主：

- 跑 CLI
- 调 FastAPI
- 检查前端 `npm run build`
- 检查 `workspace/agent_runtime.db`
- 检查 `workspace/langgraph_checkpoints.db`
