# 2026-04-02 Run Command Phase 1

## 本次执行目标

为普通用户工作流新增第一版受限本地命令执行工具：

- `run_command`

本次目标不是引入完整 shell，而是在现有项目根目录边界内，提供一个：

- 可配置
- 默认保守
- 输出稳定
- 易于后续扩展

的命令执行入口。

## 设计方向

本次设计采用“单一入口 + 配置驱动限制”的方式，而不是提前把每条命令都写成独立 tool。

具体做法：

1. 保留统一工具：
   - `run_command`
2. 把安全策略放到 `config.json`：
   - 是否启用
   - 白名单程序
   - 阻断模式
   - 超时上限
   - 输出截断上限

这样后续可以不改代码，只通过配置逐步放宽或收紧能力边界。

## 代码改动

### 1. 新增工具模块

新增文件：

- `agentbot/tools/command.py`

新增工具：

- `run_command`

当前行为：

- 解析命令字符串
- 校验命令不为空
- 校验首个程序是否在白名单内
- 校验命令是否命中危险模式
- 校验工作目录是否仍在项目根目录内
- 使用 `subprocess.run(..., shell=False)` 执行
- 返回稳定的结构化文本输出

输出格式包括：

- `Command`
- `Working directory`
- `Timed out`
- `Exit code`
- `Stdout`
- `Stderr`

### 2. 扩展配置模型

修改文件：

- `agentbot/config/settings.py`

新增：

- `CommandSettings`
- `Settings.command`
- `command` 段解析与校验逻辑

当前支持的配置项：

- `enabled`
- `default_timeout_seconds`
- `max_timeout_seconds`
- `max_output_chars`
- `allowed_programs`
- `blocked_patterns`

### 3. 更新默认配置示例

修改文件：

- `config.json`

新增 `command` 段，当前默认启用，并保守允许：

- `.venv\Scripts\python.exe`
- `python`
- `uv`
- `npm`

同时默认阻断：

- 删除类命令
- 高风险 git 清理命令
- 重定向
- 管道
- 组合命令

## 为什么不用完整 shell

当前产品定位不是开发者终端，而是普通用户可控的本地 Agent。

如果直接开放完整 shell，会立刻引入：

- 较大的误操作风险
- 很难解释的权限边界
- 很难在 UI 中说明“为什么这个命令能跑”
- 更高的恢复与审计成本

所以本次选择：

- 单一入口保留灵活性
- 配置限制保留安全边界

## 文档同步

本次同步更新：

- `README.md`
- `docs/runbooks/config.md`
- `docs/architecture/tools.md`
- `docs/architecture/project-structure.md`

## 验证建议

建议验证：

1. `Settings.from_file()` 能正常解析新增 `command` 配置
2. `get_registered_tool_names()` 中出现 `run_command`
3. 白名单内命令可执行
4. 非白名单命令会被拒绝
5. 包含阻断模式的命令会被拒绝
6. 超时与输出截断行为符合配置

## 当前结果

截至本次执行结束，项目已经具备第一版受限本地命令执行能力。

它更接近：

- “执行受控本地任务”

而不是：

- “给模型一个完整终端”

这更适合当前普通用户定位，也为后续继续加高频封装型命令工具保留了空间。
