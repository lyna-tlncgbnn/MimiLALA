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
  "debug": false
}
```

## 字段说明

- `llm.api_key`
  必填
- `llm.base_url`
  可选，使用 OpenAI-compatible 服务时可配置
- `llm.model`
  可选，默认是 `gpt-4.1-mini`
- `llm.temperature`
  数值型
- `debug`
  布尔型

## 代码入口

配置读取与校验位于：

- `agentbot/config/settings.py`

## 当前建议

- 本地开发先确认 `api_key`
- 如果接第三方兼容服务，再设置 `base_url`
- 排障时可临时把 `debug` 设为 `true`
