# Browser Subgraph Frame-Aware Observation

## 日期

- 2026-04-03

## 目标

继续把 browser subgraph 的 observation 层向 browser-use 靠拢，但保持以下边界不变：

- 浏览器 agent 仍然属于 LangGraph 子图
- transcript / runs / run_steps / timeline 不改
- 数据落盘与前后端沟通层不改

本轮重点补齐：

1. iframe 感知
2. AX / 可访问性语义
3. 更强的交互元素判定
4. 执行前页面变化守卫

## 本次实现

### 1. observation 改为 page + frame 双层采集

文件：

- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

调整：

- 页面内 JS 负责采集“当前 document”的交互元素
- 不再只依赖页面内 `iframe.contentDocument` 递归
- 额外通过 Playwright `page.frames` 逐帧补采 iframe 内容
- 为 frame 内元素记录 `frame_path`
- 让执行层能按 frame 路径进入目标 frame 再定位元素

这解决了 `file://` fixture 等场景下宿主页拿不到 `contentDocument` 但 Playwright 仍能看到 frame 的问题。

### 2. 增加 AX / 语义字段

文件：

- [views.py](/F:/AgentBot/agentbot/browser/views.py)
- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

新增字段：

- `ax_role`
- `ax_name`
- `disabled`
- `checked`
- `expanded`
- `pressed`
- `iframe_hint`
- `observation_fingerprint`
- `iframe_summaries`

采集方式：

- 优先使用 Chromium 的 `getComputedAccessibleNode`
- 拿不到时回退到现有 HTML / ARIA 信息

### 3. 加强交互元素判定

文件：

- [dom_service.py](/F:/AgentBot/agentbot/browser/dom_service.py)

借鉴 browser-use 思路后，当前会综合判断：

- 原生交互标签
- ARIA role
- AX role / AX state
- 事件属性
- tabindex
- contenteditable
- cursor:pointer
- label/span 包裹表单控件
- 搜索类 class / id / data-* 语义
- iframe 尺寸

同时继续过滤：

- display:none
- visibility:hidden
- 透明元素
- hidden / aria-hidden
- pointer-events:none
- input[type=hidden]

### 4. 增加执行前页面变化守卫

文件：

- [actions.py](/F:/AgentBot/agentbot/browser/actions.py)

调整：

- 点击/输入前先比对当前 `runtime.page.url` 与 observation 时的 URL
- 如果页面已经变了，直接要求重新 observe
- 动作 locator 现在支持 frame 路径链式定位

## 验证

已完成：

1. `.\.venv\Scripts\python.exe -m compileall agentbot`
2. 隐藏 textarea fixture 验证
3. iframe fixture 验证

fixture 文件：

- [browser_fixture_hidden_textarea.html](/F:/AgentBot/workspace/browser_fixture_hidden_textarea.html)
- [browser_fixture_iframe.html](/F:/AgentBot/workspace/browser_fixture_iframe.html)
- [browser_fixture_iframe_child.html](/F:/AgentBot/workspace/browser_fixture_iframe_child.html)

验证结果：

- 隐藏 `textarea` 不会再进入交互元素列表
- iframe 内 `input` / `button` 能被 observation 正确采集
- `type -> observe -> click` 能在 iframe 内正常执行

## 结果

本轮完成后，browser subgraph 的 observation 层已经比初版更接近 browser-use 的核心设计：

- 不是只给 LLM 一个轻量文字摘要
- 而是先生成更可信的“可执行页面对象集合”
- 再让动作层基于这些对象执行

## 当前仍未引入

本轮仍未引入：

- browser-use 的 event bus / watchdog 体系
- 基于 CDP 的完整 DOM / AX tree / selector_map 架构
- 页面变化后的多动作批处理守卫
- 下载、弹窗、权限、导航事件的专门 watchdog

这些更像下一阶段的 runtime 基础设施升级。
