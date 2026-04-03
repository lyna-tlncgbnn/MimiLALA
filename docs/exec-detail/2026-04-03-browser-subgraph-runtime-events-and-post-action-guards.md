# 2026-04-03 Browser Subgraph Runtime Events And Post-Action Guards

## 背景

浏览器子图已经完成了稳定 selector、frame-aware observation 和更强的交互元素判定，但动作执行层还缺少更接近 `browser-use` 的运行时闭环：

- 点击后缺少主动的下载探测
- 新标签页/弹窗只能依赖被动事件，动作结果里不够稳定
- 动作执行后缺少明确的页面变化守卫信号

这会让子图虽然能执行点击，但对“页面是否已经变化、是否触发下载、是否出现弹窗/新页签”的感知仍然偏弱。

## 本次实现

本次保持“浏览器 agent 仍然是 LangGraph 子图”的前提不变，没有修改 run/timeline/数据落盘和前后端沟通层，只增强浏览器 runtime。

涉及文件：

- `agentbot/browser/actions.py`
- `agentbot/browser/session.py`

### 1. 点击动作增加主动运行时探测

`browser_act -> execute_browser_action -> _click()` 现在不再只是执行 `locator.click()`，而是通过 `_click_with_runtime_guards()` 在点击前后补充运行时探测：

- 临时监听 `context.on("page")`，捕获点击后新建的 tab/page
- 临时监听 `page.on("download")`，捕获点击触发的下载
- 点击后等待短时间窗口，优先让 session 常驻事件处理器完成落盘和事件记录
- 如果常驻下载处理未接住，再回退到动作层手动 `save_as`

这套方式与 `browser-use` 的思路一致：动作执行时主动感知下载/页面副作用，同时保留底层 watchdog/session 级事件处理作为兜底。

### 2. 动作结果补充 post-action guard 信号

`_collect_post_action_effects()` 现在会统一产出：

- `page_changed`
- `observation_stale`
- `recent_events`
- `downloads`
- `dialogs`
- `tab_events`
- `navigation_events`

其中 `observation_stale` 用来显式标记“这一步动作已经让 observation 失效，下一步应重新观察页面”。判断依据包括：

- URL 变化
- 导航事件
- 下载事件
- dialog 事件
- 新 tab 事件

这样浏览器子图的 `observe -> decide -> act -> evaluate -> observe` 闭环就更明确了。

### 3. session 事件记录支持去重

`record_runtime_event()` 新增 `dedupe_recent` 参数，用于避免主动探测和被动监听在同一事件上重复记账。

这主要用于：

- 下载事件
- 新 tab 事件

## 验证

### 编译验证

执行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

结果：通过。

### 本地 runtime 验证

使用 `workspace/browser_fixture_dialog_popup_download.html` 直接走 AgentBot 自身的：

- `start_browser_session`
- `capture_page_state`
- `execute_browser_action`

验证结果：

- 点击 `Open Dialog` 后，动作结果包含 `dialogs` 和 `recent_events`
- 点击 `Download File` 后，动作结果包含 `downloads`
- 下载文件成功落到 `workspace/browser_artifacts/<session>/downloads/`
- 点击本地导航链接后，动作结果包含 `page_changed=True` 和 `navigation_events`

## 结论

浏览器子图现在已经具备一套更接近 `browser-use` 的轻量 runtime 基础设施：

- observation 负责提供稳定页面状态
- action 在执行期主动探测下载/新页签/导航副作用
- session 保持常驻事件监听与落盘兜底

下一步如果继续向 `browser-use` 靠拢，可以优先考虑：

- 更系统的 popup/modal 分类与自动处理
- 新 tab 的父子关系、焦点策略和回切策略
- 更完整的 browser session/watchdog 分层
