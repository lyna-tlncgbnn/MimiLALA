# 配置说明

## 配置文件

运行时配置来自仓库根目录的 `config.json`。

当前主要结构：

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "your-model-name",
    "temperature": 0.1
  },
  "search": {
    "provider": "tavily",
    "api_key": "your_search_api_key",
    "max_results": 5,
    "timeout_seconds": 12
  },
  "command": {
    "enabled": true,
    "default_timeout_seconds": 20,
    "max_timeout_seconds": 60,
    "max_output_chars": 12000,
    "allowed_programs": [
      ".venv\\Scripts\\python.exe",
      "python",
      "uv",
      "npm"
    ],
    "blocked_patterns": [
      "del ",
      "remove-item",
      "rmdir",
      ">",
      "|",
      "&&"
    ]
  },
  "debug": false
}
```

## 配置边界

当前项目统一采用下面这条规则：

- 应用级配置放 `config.json`
- 运行数据 / UI 状态放 SQLite 或前端本地状态

这意味着：

### 放在 `config.json` 的

- `llm.*`
- `search.*`
- `command.*`
- 以后可能的 provider 选择、默认超时、默认参数、功能开关

### 不放在 `config.json` 的

- 当前选中的 conversation
- draft 内容
- 执行区展开状态
- 侧边栏宽度
- transcript / runs / run_steps

这些属于运行数据或 UI 状态，不属于应用级配置。

## 字段说明

- `llm.api_key`
  必填
- `llm.base_url`
  可选，使用 OpenAI-compatible 服务时可配置
- `llm.model`
  可选，默认是 `gpt-4.1-mini`
- `llm.temperature`
  数值型
- `search.provider`
  当前搜索 provider，第一版支持 `tavily`
- `search.api_key`
  搜索服务 API key
- `search.max_results`
  搜索工具默认返回结果数，范围建议 1 到 10
- `search.timeout_seconds`
  搜索请求超时秒数
- `command.enabled`
  是否启用 `run_command`
- `command.default_timeout_seconds`
  默认命令超时秒数
- `command.max_timeout_seconds`
  允许的最大超时秒数
- `command.max_output_chars`
  stdout / stderr 的截断上限
- `command.allowed_programs`
  允许执行的程序白名单
- `command.blocked_patterns`
  明确禁止出现在命令字符串中的危险模式
- `debug`
  布尔型

## 代码入口

配置读取与校验位于：

- `agentbot/config/settings.py`

## 当前建议

- 本地开发先确认 `api_key`
- 如果接第三方兼容服务，再设置 `base_url`
- 如需联网搜索，补充 `search` 段
- 如需受限本地命令执行，补充并调整 `command` 段
- 排障时可临时把 `debug` 设为 `true`
