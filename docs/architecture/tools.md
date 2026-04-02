# Tools Architecture

## 当前职责

`agentbot/tools/` 负责两件事：

- 定义模型可调用的工具
- 通过统一注册入口把这些工具交给 graph

## 当前工具集

### `agentbot/tools/basic.py`

当前基础工具：

- `get_current_time`
- `multiply`

### `agentbot/tools/filesystem.py`

当前文件系统工具：

- `list_directory`
- `read_file`
- `write_file`
- `read_pdf`
- `read_docx`

## 定义方式

工具使用 `langchain_core.tools.tool` 装饰器定义。

tool 的主要元数据来源于：

- 函数名
- docstring
- 参数签名
- 类型注解

## 注册方式

统一注册入口：

- `agentbot/tools/registry.py`

当前机制是：

1. 扫描 `agentbot.tools` 下的模块
2. 跳过 `_` 开头和 `registry`
3. 读取模块级 `TOOLS`
4. 汇总成当前 graph 可用的工具列表

这意味着当前不是隐式反射全模块函数，而是显式导出。

## graph 集成

当前 graph 会把同一份注册结果同时用于：

- `llm.bind_tools(tools)`
- `ToolNode(tools)`

这样模型看到的 schema 和实际可执行的工具保持一致。

## 文件系统边界

`filesystem.py` 里的工具并不是无限制访问磁盘。

当前主要边界是：

- 相对路径会解析到项目根目录
- 超出项目根目录的访问会被拒绝
- 读写行为都走统一路径解析

## 展示边界

当前工具输出和前端展示之间已经有明确分层：

- tool 原始输出用于 run steps 和运行时内部处理
- 用户可见最终回答不应直接照搬内部 raw tool 协议

这也是为什么当前执行区和 transcript 已经分离。

## 当前限制

当前工具层还没有系统化引入：

- 浏览器工具
- shell 工具
- MCP 外部工具注册
- 细粒度权限系统
- 插件化 marketplace

当前仍然保持“小而明确”的工具集合。
