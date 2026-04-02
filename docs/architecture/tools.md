# Tools Architecture

## 当前职责

`agentbot/tools/` 当前已经分成两层：

- 工具域模块
- 工具基础设施

这样做是为了让工具数量继续增长时，目录不会退化成平铺的单文件堆。

## 当前目录结构

```text
agentbot/tools/
  basic.py
  codebase.py
  common.py
  command.py
  editing.py
  filesystem.py
  web_fetch.py
  web_search.py
  registry.py
  infra/
    error_handling.py
  providers/
    base.py
    tavily.py
```

### 工具域模块

- `basic.py`
  基础通用工具
- `codebase.py`
  项目内查找与局部读取工具
- `command.py`
  受限本地命令执行工具
- `editing.py`
  更安全的局部文本修改工具
- `filesystem.py`
  文件系统工具
- `web_fetch.py`
  直接读取 URL 内容的联网工具
- `web_search.py`
  联网搜索工具

### 工具基础设施

- `infra/error_handling.py`
  ToolNode 的统一错误格式化
- `providers/`
  外部 provider 适配层，目前用于搜索能力

## 当前工具集

### 基础工具

- `get_current_time`
- `multiply`

### 文件系统工具

- `list_directory`
- `read_file`
- `write_file`
- `read_pdf`
- `read_docx`

### 代码库查找工具

- `glob_files`
- `search_in_files`
- `read_file_range`

### 局部编辑工具

- `replace_in_file`
- `append_file`

### 受限命令工具

- `run_command`

### 联网搜索工具

- `web_search`

### URL 读取工具

- `fetch_url`

当前第一版搜索 provider 是：

- `tavily`

## 为什么这样拆

这套拆分更接近主流 agent 工程里对 tools 的处理方式：

- 顶层保留“按能力域分文件”
- provider 和错误处理不和业务 tool 平铺在一起
- registry 继续作为统一入口

这样后面继续加：

- browser tools
- shell tools
- knowledge tools
- artifact tools

时，不需要重写现有结构。

## 定义方式

工具继续使用 `langchain_core.tools.tool` 装饰器定义。

tool 的主要元数据仍然来自：

- 函数名
- docstring
- 参数签名
- 类型注解

## 注册方式

统一注册入口仍然是：

- `agentbot/tools/registry.py`

当前机制保持不变：

1. 扫描 `agentbot.tools` 下的模块和 package
2. 跳过 `_` 开头和 `registry`
3. 读取模块级 `TOOLS`
4. 汇总成当前 graph 可用的工具列表

这意味着：

- registry 仍然稳定
- 新增工具模块时不用修改 graph
- provider / infra package 不会自动变成 tool，除非显式导出 `TOOLS`

## graph 集成

当前 graph 会把同一份注册结果同时用于：

- `llm.bind_tools(tools)`
- `ToolNode(tools, handle_tool_errors=...)`

这样模型看到的 schema 和实际可执行的工具保持一致。

## 搜索工具设计

`web_search.py` 当前不是直接把 Tavily API 暴露给模型，而是做了两层分离：

1. tool 层
   负责参数校验和统一结果格式
2. provider 层
   负责和外部搜索服务通信

当前 provider 接口已经预留为可替换结构，后续可继续扩展：

- Brave
- Exa
- 其他搜索 provider

## 配置边界

当前应用级配置统一来自根目录 `config.json`。

对搜索能力来说，当前使用：

```json
{
  "search": {
    "provider": "tavily",
    "api_key": "your_search_api_key",
    "max_results": 5,
    "timeout_seconds": 12
  }
}
```

这属于应用级配置，所以放在 `config.json`。

而运行数据和 UI 状态仍然不属于这里：

- transcript / runs / run_steps 进 SQLite
- 前端临时交互状态进 React Query / Zustand / local state

## 文件系统边界

`filesystem.py` 里的工具仍然不是无限制访问磁盘。

当前主要边界是：

- 相对路径解析到项目根目录
- 超出项目根目录的访问会被拒绝
- 读写行为都走统一路径解析

为了避免这套边界在更多 tool 中重复实现，当前公共路径与截断逻辑已经被抽到：

- `common.py`

由以下能力复用：

- `filesystem.py`
- `codebase.py`
- `editing.py`
- `command.py`

## 项目内查找边界

`codebase.py` 面向“找到内容、读取局部内容”的普通任务场景。

当前规则：

- 只在项目根目录内递归查找
- `glob_files` 只返回文件，不返回目录
- `search_in_files` 仅扫描可按 UTF-8 读取的文本文件
- 返回结果会截断，避免超长输出污染执行记录
- `read_file_range` 使用行号区间，适合局部查看大文件

## 局部编辑边界

`editing.py` 不是整文件覆盖，而是针对高频文本变更场景提供更小粒度操作。

当前规则：

- `replace_in_file` 要求显式提供 `old_text`
- 如果命中多个位置，默认拒绝替换，除非设置 `replace_all=true`
- `append_file` 只做追加，不做中间插入

这比直接使用 `write_file` 更适合普通用户任务，也能减少误覆盖已有内容的风险。

## 命令执行边界

`command.py` 当前不是面向开发者的完整 shell，而是面向普通用户工作流的“受限本地命令执行”。

当前规则：

- 必须在 `config.json` 中显式启用
- 只允许执行 `command.allowed_programs` 白名单里的程序
- 命令字符串命中 `command.blocked_patterns` 时直接拒绝
- 运行目录必须仍在项目根目录内
- 使用 `subprocess.run(..., shell=False)`，不走 shell 展开
- stdout / stderr 都会按 `command.max_output_chars` 截断
- timeout 不能超过 `command.max_timeout_seconds`

这类设计更接近主流 agent 在非完全沙箱环境中的保守做法：优先限制程序入口、危险模式、执行目录和资源消耗，而不是默认开放任意 shell。

## 展示边界

当前工具输出和前端展示之间仍然保持分层：

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

同时，当前 `fetch_url` 仍然保持最小实现：

- 仅支持 `http` / `https`
- 仅做 GET 请求
- 主要提取 HTML、JSON、纯文本内容
- 不处理需要登录、复杂交互、动态渲染页面

当前 `run_command` 也仍然保持保守实现：

- 不支持 `shell=True`
- 不支持管道、重定向、组合命令
- 不支持任意 PowerShell 脚本执行

但当前结构已经足够支撑后续继续加很多 tool，而不会马上混乱。
