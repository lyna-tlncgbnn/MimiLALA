# 本地开发

## 安装

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

## 当前开发说明

- 这个仓库目前还没有自动化测试套件
- 现在的本地验证方式主要是跑 CLI，并检查 `workspace/` 中的落盘结果
