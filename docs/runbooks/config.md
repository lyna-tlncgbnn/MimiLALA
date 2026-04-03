# Config

## 位置

运行配置来自仓库根目录的 `config.json`。

主要入口：

- [settings.py](/F:/AgentBot/agentbot/config/settings.py)
- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)
- [session.py](/F:/AgentBot/agentbot/browser/session.py)

## 示例

```json
{
  "llm": {
    "api_key": "your_api_key",
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "model": "your-model-name",
    "temperature": 0.1,
    "max_tokens": 4096,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "request_timeout_seconds": 120,
    "max_retries": 2,
    "reasoning_effort": null,
    "reasoning": null,
    "extra_body": {},
    "default_headers": {}
  },
  "browser": {
    "headless": false,
    "close_on_finish": false,
    "max_actions": 12,
    "max_actions_per_step": 3,
    "mode": "system",
    "window_width": 1440,
    "window_height": 900,
    "no_viewport": true,
    "start_maximized": false,
    "channel": "chrome",
    "profile_directory": "Default",
    "temp_profiles_dir": "workspace/browser_profiles",
    "copy_local_profile": true,
    "artifacts_dir": "workspace/browser_artifacts",
    "downloads_dir": "workspace/browser_downloads"
  },
  "debug": false
}
```

## 浏览器配置

## LLM 配置

- `llm.api_key`
  必填。

- `llm.base_url`
  可选，适用于 OpenAI-compatible 服务。

- `llm.model`
  模型名。

- `llm.temperature`
  采样温度。

- `llm.max_tokens`
  最大输出 token 数。

- `llm.top_p`
  nucleus sampling 参数。

- `llm.frequency_penalty` / `llm.presence_penalty`
  常见惩罚项参数。

- `llm.request_timeout_seconds`
  单次请求超时时间。

- `llm.max_retries`
  请求失败后的重试次数。

- `llm.reasoning_effort`
  对支持 reasoning 的兼容模型，可设置 `low` / `medium` / `high` 一类值。

- `llm.reasoning`
  可选对象，用于更细的 reasoning 配置。

- `llm.extra_body`
  provider-specific 请求体透传入口。
  如果某个 OpenAI-compatible 平台把 `thinking`、`seed`、`response_format` 之类的参数放在自定义 body 里，这里可以直接传。

- `llm.default_headers`
  provider-specific 请求头透传入口。

- `browser.mode`
  浏览器运行模式。
  `system`：优先使用本机 Chrome/Edge，并把本地 profile 复制到 workspace 下的临时目录后启动。
  `playwright`：保留旧的 Playwright 隔离浏览器模式。

- `browser.channel`
  可选浏览器渠道，例如 `chrome`、`msedge`。主要用于帮助 system 模式优先选择本机浏览器。

- `browser.executable_path`
  可选，显式指定浏览器可执行文件路径。设置后优先级最高。

- `browser.user_data_dir`
  可选，显式指定本地浏览器 `User Data` 根目录。

- `browser.profile_directory`
  可选，指定要复制的本地 profile 目录，比如 `Default`、`Profile 1`。

- `browser.temp_profiles_dir`
  临时 profile 根目录。建议放在 workspace 下，例如：
  `workspace/browser_profiles`

- `browser.copy_local_profile`
  是否在启动前把本地 profile 复制到临时目录。
  默认应为 `true`，这样更接近 browser-use 的本地模式，也避免直接占用原始 profile。

- `browser.window_width` / `browser.window_height`
  浏览器窗口大小。

- `browser.no_viewport`
  `true` 时，页面内容跟随真实窗口伸缩，适合可见浏览器模式。

- `browser.viewport_width` / `browser.viewport_height`
  仅在 `browser.no_viewport=false` 时使用。

- `browser.artifacts_dir`
  浏览器 session 的截图、页面快照等 artifacts 根目录。

- `browser.downloads_dir`
  下载文件根目录。
  如果未设置，会回落到当前 session 的 artifacts 目录下。

## 默认目录

推荐目录：

- 临时 profile：`F:/AgentBot/workspace/browser_profiles`
- artifacts：`F:/AgentBot/workspace/browser_artifacts`
- downloads：`F:/AgentBot/workspace/browser_downloads`

每个浏览器 session 会继续在 artifacts 根目录下创建自己的子目录。

## 当前建议

如果你希望浏览器更接近真实本地使用方式，建议：

- `browser.mode = "system"`
- `browser.no_viewport = true`
- `browser.copy_local_profile = true`
- `browser.temp_profiles_dir = "workspace/browser_profiles"`

这样浏览器会优先复用你本机浏览器环境，再复制到 workspace 临时 profile 中运行，而不是直接起一个全新的隔离 Chromium context。
