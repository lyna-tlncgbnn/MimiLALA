# 本地开发

## Python 依赖安装

```powershell
uv sync
```

或者：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

## 运行 CLI

```powershell
.\.venv\Scripts\python.exe main.py
```

## 运行单条输入

```powershell
.\.venv\Scripts\python.exe main.py "what time is it?"
```

## 启动本地 FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn agentbot.api.app:app --host 127.0.0.1 --port 8000
```

## 前端开发

前端位于 `ui/`，使用 Vite。

```powershell
cd ui
npm install
npm run dev
```

## Electron 开发

桌面壳位于 `desktop/`。

```powershell
cd desktop
npm install
npm run dev
```

说明：

- Electron 会负责加载前端页面
- 当前 Electron 壳会启动本地 FastAPI 子进程

## 当前开发说明

- 这个仓库目前还没有完整自动化测试套件
- 当前验证方式主要包括：
  - 跑 CLI
  - 跑 FastAPI 路由
  - 构建前端与 Electron
  - 检查 `workspace/` 中的 persistence 落盘结果
