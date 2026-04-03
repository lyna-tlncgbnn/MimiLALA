# Browser Visible Mode And Response Layering

## 日期

- 2026-04-03

## 目标

修正当前 browser 子图两处产品表现问题：

1. 支持在配置里切换后台浏览器和可见浏览器窗口
2. 把长页面摘要从最终回答中拿掉，更多留在 timeline / artifacts

## 本次实现

### 1. 新增 browser 配置段

当前 `config.json` 支持：

```json
"browser": {
  "headless": true
}
```

说明：

- `true`：后台浏览器模式
- `false`：可见浏览器窗口模式

相关文件：

- [settings.py](/F:/AgentBot/agentbot/config/settings.py)
- [config.json](/F:/AgentBot/config.json)
- [README.md](/F:/AgentBot/README.md)
- [config.md](/F:/AgentBot/docs/runbooks/config.md)

### 2. browser session 支持 headless 切换

Playwright 启动时不再写死 `headless=True`，而是从配置读取。

相关文件：

- [session.py](/F:/AgentBot/agentbot/browser/session.py)
- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

### 3. 收紧 browser 最终回答

`browser_finish` 不再把整段页面摘要直接塞进最终回答。

现在的策略是：

- 最终回答只保留简洁结论
- 页面长摘要继续保留在 `browser_observe` 的 timeline 输出和 artifacts 中
- `browser_finish` 的 step output 仍保留详细信息，便于后续 UI 展示

相关文件：

- [browser_nodes.py](/F:/AgentBot/agentbot/graph/browser_nodes.py)

## 当前行为

调整后：

- 用户主回答更短
- 页面长内容主要在 timeline / artifacts
- 如需可见浏览器，只需把 `browser.headless` 改为 `false`

## 验证

已完成：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. `ui` 前端构建通过：`npm run build`

## 结果

这次调整后，browser 子图更符合产品预期：

- 可以切换可见/不可见浏览器模式
- 主回答不再被页面原文和交互元素列表淹没
- timeline / artifacts 的角色更清晰
