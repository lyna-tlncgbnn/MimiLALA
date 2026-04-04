# Config

运行配置来自仓库根目录的 [config.json](/F:/AgentBot/config.json)。

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
    "downloads_dir": "workspace/browser_downloads",
    "download_start_timeout_seconds": 4.0,
    "download_complete_timeout_seconds": 30.0
  },
  "debug": false
}
```

## LLM 字段

- `llm.api_key`
  必填。
- `llm.base_url`
  可选，适用于 OpenAI-compatible 服务。
- `llm.model`
  模型名。
- `llm.temperature`
  采样温度。
- `llm.max_tokens`
  单次输出 token 上限，不是上下文窗口大小。
- `llm.top_p`
  nucleus sampling 参数。
- `llm.frequency_penalty` / `llm.presence_penalty`
  常见惩罚参数。
- `llm.request_timeout_seconds`
  单次请求超时。
- `llm.max_retries`
  请求失败重试次数。
- `llm.reasoning_effort`
  对支持 reasoning 的兼容模型使用。
- `llm.reasoning`
  更细粒度的 reasoning 对象配置。
- `llm.extra_body`
  provider-specific 请求体透传入口，例如豆包的 `thinking` 配置。
- `llm.default_headers`
  provider-specific 请求头透传入口。

说明：
- 想走默认值时，优先直接省略字段。
- 只有明确设计成可选的字段才建议写 `null`。

## Browser 字段

- `browser.mode`
  `system` 或 `playwright`。
  `system` 会优先使用本机浏览器环境，并把本地 profile 复制到 workspace 下的临时目录，再直接启动本机浏览器进程并通过 CDP 接回该浏览器。
- `browser.channel`
  本机浏览器通道，例如 `chrome`、`msedge`。
- `browser.executable_path`
  显式指定浏览器可执行文件路径。
- `browser.user_data_dir`
  显式指定本机浏览器 `User Data` 根目录。
- `browser.profile_directory`
  指定要复制的 profile，例如 `Default`、`Profile 1`。
- `browser.temp_profiles_dir`
  临时 profile 根目录。当前推荐：
  [browser_profiles](/F:/AgentBot/workspace/browser_profiles)
  system 模式下，当前会在浏览器正常关闭时删除本次 session 目录；下次启动前还会自动清理遗留的 `browser_session_*` 临时目录。
- `browser.copy_local_profile`
  是否先复制本地 profile 再运行。建议保持 `true`。
- `browser.window_width` / `browser.window_height`
  浏览器窗口大小。
- `browser.no_viewport`
  `true` 时页面内容跟随真实窗口缩放，适合可见浏览器模式。
- `browser.viewport_width` / `browser.viewport_height`
  仅在 `no_viewport=false` 时使用。
- `browser.artifacts_dir`
  浏览器截图与页面快照根目录。
- `browser.downloads_dir`
  下载文件目录。当前推荐：
  [browser_downloads](/F:/AgentBot/workspace/browser_downloads)
  在 `browser.mode = "system"` 时，这个目录现在不仅是 runtime 的保存目标，也会被写进临时 profile 的浏览器默认下载设置。
- `browser.download_start_timeout_seconds`
  点击后等待“下载已开始”信号的 grace period。用于避免慢站点被重复点击。
- `browser.download_complete_timeout_seconds`
  下载开始后等待完成的时长。超时后会标记为“下载进行中”而不是立刻判失败。

## 当前推荐

如果你希望浏览器尽量接近真实本地使用体验，建议：

- `browser.mode = "system"`
- `browser.no_viewport = true`
- `browser.copy_local_profile = true`
- `browser.temp_profiles_dir = "workspace/browser_profiles"`
- `browser.downloads_dir = "workspace/browser_downloads"`

这样浏览器会运行在本机浏览器环境语义之上，同时把 agent 使用的临时 profile 收敛到 workspace 内，便于排查和清理。
