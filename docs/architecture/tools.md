# Tools Architecture

## 这一层负责什么

`agentbot/tools/` 这一层负责两件事：

- 定义可以被模型调用的工具
- 把这些工具整理成当前 graph 可直接使用的 tool 列表

当前实现保持了比较简单的结构：

- tool 定义放在具体模块中
- tool 注册统一收口到 `agentbot/tools/registry.py`
- graph 和 runner 不关心某个 tool 来自哪个模块，只依赖统一注册出口

这样做的好处是，新增工具时不需要修改 graph 主流程，只需要在 `tools/` 目录下按约定新增模块即可。

## 当前目录角色

- `agentbot/tools/basic.py`
  放当前最基础的演示工具，例如 `get_current_time` 和 `multiply`
- `agentbot/tools/filesystem.py`
  放文件系统相关工具，例如 `list_directory`、`read_file`、`read_pdf`、`read_docx`、`write_file`
- `agentbot/tools/registry.py`
  负责自动扫描 `agentbot.tools` 包下的模块，并返回当前可用工具列表

## Tool 是如何定义的

当前项目里的工具使用 `langchain_core.tools.tool` 装饰器定义。

示意如下：

```python
from langchain_core.tools import tool


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b
```

这个写法同时表达了三层信息：

- 工具名
  默认来自函数名，例如 `multiply`
- 工具描述
  默认来自函数 docstring，例如 `Multiply two numbers and return the result.`
- 工具参数
  默认来自函数签名和类型标注，例如 `a: float`、`b: float`

因此，当前工具定义的主要信息来源是函数本身，而不是额外单独维护一份 schema 文件。

## 描述和参数是怎么来的

在当前实现里：

- tool 的描述主要来自函数 docstring
- tool 的参数结构主要来自函数签名与类型注解

例如：

```python
@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file from a project-relative or absolute path."""
```

这里会自然生成出：

- tool name: `read_file`
- description: `Read a UTF-8 text file from a project-relative or absolute path.`
- parameters:
  - `path`
  - type 为字符串

所以在这个仓库里，想修改工具给模型看的说明，最直接的方式就是修改函数 docstring；想修改参数结构，最直接的方式就是修改函数入参和类型注解。

## 自动注册机制

当前自动注册逻辑位于 `agentbot/tools/registry.py`。

整体规则很简单：

1. 扫描 `agentbot.tools` 包下的模块
2. 跳过 `_` 开头模块和 `registry` 自身
3. 导入每个模块
4. 读取模块中的 `TOOLS` 变量
5. 把所有模块里的 `TOOLS` 汇总成一个统一列表返回

也就是说，当前不是“扫描每个函数并自动猜测谁是 tool”，而是“扫描模块，再读取模块显式导出的 `TOOLS` 列表”。

这个约定的好处是：

- 比完全隐式扫描更清晰
- 模块作者可以明确决定哪些 tool 对外暴露
- 不容易把内部辅助函数误注册进去

## `TOOLS` 约定

每个参与自动注册的模块，需要暴露一个模块级变量：

```python
TOOLS = [multiply, get_current_time]
```

或者：

```python
TOOLS = [list_directory, read_file, read_pdf, read_docx, write_file]
```

注册器只认这个约定，不会自动注册没有放进 `TOOLS` 的函数。

因此，新增一个工具模块的最小步骤是：

1. 在 `agentbot/tools/` 下创建新模块
2. 用 `@tool` 定义工具函数
3. 在模块底部把需要暴露的工具加入 `TOOLS`

如果缺少第 3 步，模块虽然存在，但不会进入当前 graph 的工具列表。

## graph 是怎么拿到 tools 的

`agentbot/graph/builder.py` 不直接依赖具体工具模块，而是调用：

```python
from agentbot.tools.registry import get_registered_tools
```

然后：

```python
tools = get_registered_tools()
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)
```

这意味着同一份注册结果会同时用于：

- 给模型绑定工具 schema
- 给 `ToolNode` 提供可执行工具集合

这样模型“看到的工具列表”和 graph 真正“能执行的工具列表”来自同一个入口，不会出现两边各维护一份的分叉。

## runner 如何记录工具注册结果

`agentbot/app/runner.py` 在每次执行开始时会调用 `get_registered_tools()`，并记录一个 `tools_registered` 事件。

这件事的意义是：

- 可以从 execution log 里看到当次运行到底注册了哪些工具
- 调试时更容易确认自动注册是否生效

因此，tools 注册不仅影响 graph 构建，也会影响本地 execution logging 中的可观察性。

## filesystem tools 的边界

当前 `filesystem.py` 中的工具不是无边界文件系统访问，而是统一通过内部路径解析逻辑约束在项目根目录内。

核心约束是：

- 相对路径会被解析到仓库根目录下
- 绝对路径只有在项目根目录内时才允许访问
- 超出项目根目录的路径会直接报错

这样做的目的是在增加真实文件操作能力的同时，先保持边界清晰、行为可预测。

## 新增一个 tool 的推荐方式

推荐按下面的顺序扩展：

1. 先判断它是否属于已有模块职责
2. 如果属于新的能力簇，就新增一个模块
3. 使用 `@tool` 定义函数，并写清楚 docstring
4. 给参数加上明确类型标注
5. 把对外暴露的工具加入 `TOOLS`
6. 通过 `get_registered_tool_names()` 或 CLI 运行确认它已被发现

这个过程不需要修改：

- `agentbot/graph/builder.py`
- `agentbot/app/runner.py`
- CLI 入口

## 当前限制

当前 tools 层仍然有一些明确边界：

- 没有按类别做更复杂的插件系统
- 没有额外的 tool metadata 注册中心
- 没有 tool 级权限模型
- 没有 web、shell、browser、MCP 等其他工具类型

这和当前项目阶段一致：先用最小可读结构把 tool loop、注册机制和基础文件能力跑通，再决定后续是否继续扩展。
