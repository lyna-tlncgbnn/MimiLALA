# 配置说明

## 配置文件

运行时配置从仓库根目录的 `config.json` 中读取。

## 当前字段

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

- `llm.api_key` 必填
- `llm.base_url` 可选
- `llm.model` 省略时默认是 `gpt-4.1-mini`
- `llm.temperature` 必须是数字
- `debug` 必须是布尔值

## 实现位置

见 `agentbot/config/settings.py`。
