# 2026-04-02 First-Tier Tools Phase 1

## 本次执行目标

围绕“面向普通用户的第一梯队工具”先落第一批 6 个能力：

1. 项目内文件查找
2. 项目内文本搜索
3. 大文件局部读取
4. 更安全的局部文本替换
5. 文件追加写入
6. 直接读取 URL 内容

本次不引入：

- git 工具
- shell 工具
- browser automation
- 多 agent 编排

## 本次新增工具

### 1. `codebase.py`

新增文件：

- `agentbot/tools/codebase.py`

新增工具：

- `glob_files`
- `search_in_files`
- `read_file_range`

用途：

- 让 agent 更容易在项目内“找到文件”
- 让 agent 更容易在项目内“找到某段内容”
- 在不整文件读取的情况下查看局部行区间

### 2. `editing.py`

新增文件：

- `agentbot/tools/editing.py`

新增工具：

- `replace_in_file`
- `append_file`

用途：

- 避免高频场景下只能依赖整文件 `write_file`
- 把“替换一段内容”“往文件末尾补一段内容”变成更安全的原子动作

### 3. `web_fetch.py`

新增文件：

- `agentbot/tools/web_fetch.py`

新增工具：

- `fetch_url`

用途：

- 补齐 `web_search` 之后的“打开并读取页面内容”这一步
- 让 agent 能直接读取公开网页、JSON 接口或纯文本页面

## 公共能力抽取

新增文件：

- `agentbot/tools/common.py`

抽取内容：

- 项目根目录路径解析
- 项目相对路径展示
- 长文本截断

这样可以避免：

- `filesystem.py`
- `codebase.py`
- `editing.py`

各自重复维护路径边界逻辑。

## 具体行为边界

### 路径边界

本次新增工具继续沿用项目根目录边界：

- 相对路径按仓库根目录解析
- 绝对路径必须仍在仓库根目录内
- 越界访问直接报错

### `glob_files`

- 只返回文件
- 支持 `*.md`、`docs/**/*.md` 这类模式
- 返回数量受限，避免超长输出

### `search_in_files`

- 只扫描能按 UTF-8 读取的文本文件
- 返回命中行号与行内容
- 限制最大命中数，避免执行记录爆炸

### `read_file_range`

- 使用 `start_line` 与 `end_line`
- 返回时保留行号
- 超出文件总行数时会明确报错或自动裁切结束行

### `replace_in_file`

- 要求显式提供 `old_text`
- 未命中时报错
- 命中多个位置时默认拒绝，避免误改多个位置
- 只有在 `replace_all=true` 时才允许批量替换

### `append_file`

- 支持不存在文件时自动创建
- 支持自动补换行后再追加

### `fetch_url`

- 只支持 `http` / `https`
- 只做 GET 请求
- 识别 HTML / JSON / 纯文本
- HTML 当前做最小清洗，不处理动态渲染

## 文档同步

本次同步更新：

- `README.md`
- `docs/architecture/tools.md`
- `docs/architecture/project-structure.md`

确保工具能力清单和目录说明与代码一致。

## 验证建议

本次实现后建议至少验证：

1. `get_registered_tool_names()` 已包含新增工具
2. `compileall agentbot` 通过
3. `glob_files` / `search_in_files` / `read_file_range` 能在仓库内正常工作
4. `replace_in_file` / `append_file` 能在测试文件上完成局部修改
5. `fetch_url` 能读取一个公开 URL 或本地临时 HTTP 页面

## 当前结果

截至本次执行结束，第一梯队中以下工具已经落地：

- `glob_files`
- `search_in_files`
- `read_file_range`
- `replace_in_file`
- `append_file`
- `fetch_url`

这批能力相比之前的工具层，更接近“先找到内容，再局部读取，再小心修改，再读取外部页面”的普通用户工作流。
