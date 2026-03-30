# 2026-03-30 Richer Tools Implementation

## 本次执行目标

本次执行围绕 `docs/exec-plans/active/richer-tools.md` 落地了两类工作：

1. 把 tools 注册方式从手动维护改成自动扫描注册
2. 新增第一批基础文件工具，并继续扩展到 PDF 与 DOCX 读取能力

本次工作优先保证主链路可运行，不扩大到 web、shell、browser、MCP 或 multi-agent 相关工具。

## 本次实际改动

### 1. tools 注册方式改为自动扫描

修改文件：

- `agentbot/tools/registry.py`
- `agentbot/tools/basic.py`

具体变更：

- 在 `registry.py` 中新增模块扫描逻辑
- 扫描 `agentbot.tools` 包下的模块
- 跳过 `_` 开头模块和 `registry` 自身
- 导入模块后读取模块级 `TOOLS` 变量
- 汇总所有模块中的 `TOOLS` 作为当前 graph 的注册结果返回

同时在 `basic.py` 中补充：

```python
TOOLS = [get_current_time, multiply]
```

这样原有工具也进入统一注册流程，不再依赖手写固定列表。

### 2. 新增 filesystem 工具模块

新增文件：

- `agentbot/tools/filesystem.py`

本次加入的工具：

- `list_directory`
- `read_file`
- `write_file`
- `read_pdf`
- `read_docx`

其中前 3 个属于执行计划要求的基础 filesystem 能力，后 2 个是在用户后续明确提出“支持 PDF/Word 读取”后追加实现。

### 3. filesystem 工具的边界控制

`filesystem.py` 中所有工具统一通过内部路径解析逻辑限制在项目根目录内。

具体规则：

- 相对路径按仓库根目录解析
- 绝对路径只有在项目根目录内时才允许访问
- 超出项目根目录的路径直接报错

这样可以先提供真实文件操作能力，同时保持边界清晰，不把当前阶段扩展成无约束文件系统访问。

### 4. PDF 与 DOCX 读取实现方式

PDF：

- 使用 `pypdf` 解析文本
- 新增依赖到 `pyproject.toml`
- `uv.lock` 因安装依赖而更新

DOCX：

- 未引入额外 `python-docx`
- 直接按 `.docx` 是 zip 包的结构读取 `word/document.xml`
- 使用 XML 命名空间解析段落文本

这样做的原因是：

- PDF 在当前环境中没有现成解析库，因此补充一个轻量依赖
- DOCX 可先用标准库完成最小文本提取，减少额外依赖

### 5. 新增 tools 架构说明文档

新增文件：

- `docs/architecture/tools.md`

并更新：

- `docs/architecture/index.md`

这份架构文档说明了：

- tool 的定义方式
- tool 描述和参数从哪里来
- 自动注册机制如何工作
- `TOOLS` 约定是什么
- graph 和 runner 如何使用注册结果

## 本次验证

本次执行完成后做了以下验证：

### 1. 自动注册验证

通过脚本调用 `get_registered_tool_names()`，确认注册结果已经变为：

- `get_current_time`
- `multiply`
- `list_directory`
- `read_file`
- `read_pdf`
- `read_docx`
- `write_file`

说明：

- 原有工具仍然可用
- 新工具已进入统一注册流程

### 2. filesystem 工具直接调用验证

已验证：

- `list_directory` 可读取目录
- `read_file` 可读取文本文件
- `write_file` 可写入项目内文件

并额外验证：

- 越界路径访问会被拦截

示例结论：

- 访问 `..\\outside.txt` 会返回项目根目录外访问错误

### 3. DOCX 工具验证

创建最小 `.docx` 样例文件后，`read_docx` 能正确提取段落文本。

验证结论：

- DOCX 文本读取能力可用

### 4. PDF 工具验证

创建带文本内容的最小 PDF 样例后，`read_pdf` 能提取页面文字。

验证结论：

- PDF 文本读取能力可用

说明：

- 对于扫描版 PDF 或本身没有文本层的 PDF，当前实现可能返回“没有可提取文本”

### 5. 代码级验证

运行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果通过，说明本次改动未引入明显语法或导入错误。

### 6. CLI 主链路尝试

尝试运行：

```powershell
.\.venv\Scripts\python.exe main.py "list the files in agentbot/tools and tell me what tools are available"
```

结果：

- `tools_registered` 事件中已经能看到新工具
- 运行在模型调用阶段失败，报错为 `Model execution failed: Connection error.`

这说明：

- tools 注册和 graph 构建层面未出现本次改动导致的报错
- 失败原因来自模型连接，而不是 tool 注册逻辑本身

## 涉及文件

本次执行中涉及的主要文件如下：

- `agentbot/tools/basic.py`
- `agentbot/tools/registry.py`
- `agentbot/tools/filesystem.py`
- `pyproject.toml`
- `uv.lock`
- `docs/architecture/tools.md`
- `docs/architecture/index.md`

另外，工作区中已存在：

- `docs/exec-plans/active/richer-tools.md`

该文件在当前工作树中本来就有变更，本次未对其内容做同步整理。

## 当前结果

截至本次执行结束，项目已经具备：

- 自动扫描注册 tools 的能力
- `读目录`
- `读文件`
- `写文件`
- `读 PDF`
- `读 DOCX`

并且：

- graph 主入口未改形状
- runner 主流程未改接口
- 工具注册事件仍然会进入 execution log

## 当前已知边界

本次实现仍然保持以下边界：

- 没有新增 web tools
- 没有新增 shell tools
- 没有新增 browser tools
- 没有新增 MCP tools
- 没有引入 multi-agent 相关工具
- 没有实现扫描版 PDF 的 OCR
- `read_docx` 当前主要提取段落文本，未专门处理复杂表格、批注、页眉页脚等更完整结构

## 建议给 plan agent 的后续动作

后续如果要做总结归档，建议 plan agent 重点关注：

1. 是否将 `richer-tools.md` 从“计划态”补到“已执行进展态”
2. 是否补充 README 中的工具能力说明
3. 是否在架构文档中继续补 `project-structure.md` 对 tools 层的细化
4. 是否为工具注册顺序、重复工具名冲突、更多文档格式支持补后续计划
