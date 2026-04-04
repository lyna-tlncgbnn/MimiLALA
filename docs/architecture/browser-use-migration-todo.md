# Browser-Use Migration Todo

## 目标

这份文档用于跟踪 AgentBot 浏览器子图继续向 `browser-use` 靠拢时，哪些能力已经迁移，哪些还值得继续做，以及推荐的实施顺序。

前提保持不变：

- 浏览器 agent 继续作为 LangGraph 子图存在
- 不把浏览器细节上浮到主图和 transcript 主链路
- 不破坏现有 `run / run_steps / artifacts / timeline / 数据落盘`

## 已经完成或已明显借鉴

- [x] 浏览器任务以 specialist subgraph 形式运行
- [x] observation -> planning -> action -> evaluate 的浏览器闭环
- [x] 稳定 selector 映射替代 DOM 序号回放
- [x] 面向 LLM 的 browser state summary
- [x] iframe-aware observation
- [x] AX / aria 信息补充
- [x] planner state：`evaluation_previous_goal / memory / next_goal`
- [x] 多动作 step
- [x] 本机浏览器 profile 复制到 workspace 临时目录
- [x] runtime event bus 基础骨架
- [x] downloads / popups / dialogs / navigation / lifecycle watchdog
- [x] BrowserStateRequestEvent -> DOMWatchdog -> runtime browser state cache
- [x] selector map 开始归 runtime 持有

## 当前高优先级待迁移

### 1. runtime effect object 继续统一

- [ ] 把当前 action output 里的平铺字段进一步收束成更清晰的 runtime effect object
- [ ] 区分 download started / in progress / completed / failed 的统一结果对象
- [ ] 区分 popup opened / popup closed / active page closed / browser closed 的统一结果对象
- [ ] graph 尽量少直接理解底层浏览器细节

价值：

- 降低 graph 层的字段拼装复杂度
- 继续向 `browser-use` 的“runtime 先建模，planner 再消费”靠拢

### 2. DOM/watchdog 继续做厚

- [x] DOM/watchdog 已接入 runtime 总线
- [x] browser state request 已经由 runtime 统一处理
- [ ] 更明确的 DOM cache invalidation 策略
- [ ] 更完整的 frame/tab 级 DOM state cache
- [ ] 更强的页面差异和阻塞态识别
- [ ] 更丰富的 browser state 元数据

价值：

- 提升 observation 稳定性
- 减少 graph 与 runtime 状态漂移

### 3. planner 对 runtime effect 的消费继续收紧

- [x] 已识别 download started / in progress / completed
- [ ] 对 popup / active page close / browser close 做更细粒度规划与汇总
- [ ] 根据 runtime effect 显式决定 wait / re-observe / finish，而不是靠更多 prompt 猜测
- [ ] 把更多“动作之后发生了什么”判断沉到底层 runtime

价值：

- 进一步减少“按钮其实已经生效，但 agent 以为没有生效”
- 降低重复点击、重复提交、误判失败

## 中优先级待迁移

### 4. 更完整的本地浏览器生命周期

- [x] system browser 模式已经可用
- [ ] 评估是否需要 `user_data_dir` 更细粒度配置文档
- [ ] 评估是否需要 channel / executable_path / profile_directory 的更强排障信息
- [ ] 评估是否需要更接近 `browser-use` 的 local browser watchdog 组织方式

### 5. 更丰富的浏览器动作集

- [ ] `dismiss_overlay` / `close_popup`
- [ ] `hover`
- [ ] `select_option`
- [ ] 更明确的 suggestion / combobox 选择动作
- [ ] `extract_page` 或轻量深读动作

### 6. 更完整的完成语义

- [ ] 对“任务已完成”和“只是停止执行”做更强区分
- [ ] 浏览器子图内部完成判定继续对齐 runtime effect
- [ ] `browser_finish` 汇总进一步结构化

## 当前低优先级或暂不直接迁移

### 7. browser-use 完整 CDP DOM / AX tree 建模

- [ ] 当前先不整体迁移
- [ ] 先继续把现有 observation pipeline 和 runtime DOM cache 做扎实
- [ ] 等确实需要更强 DOM fidelity 时再评估

### 8. browser-use 完整 agent/file 工具链

- [ ] 暂不迁移完整文件工具链
- [ ] 暂不迁移 browser-use 完整 `done` schema
- [ ] 继续保留本项目自己的 LangGraph 子图外壳与状态协议

## 推荐实施顺序

1. 继续统一 runtime effect object
2. 继续做厚 DOM/watchdog 和 browser state cache
3. 收紧 graph 层对 runtime effect 的消费
4. 再扩动作集与完成语义
5. 最后再评估是否继续往更重的 CDP/session/watchdog 生命周期组织方式迁移

## 当前判断

浏览器子图现在已经不再只是“浏览器工具集合”，而开始具备 `browser-use` 风格的内核分层：

- planner 是 planner
- runtime 是 runtime
- DOM state 是通过 runtime 请求
- 副作用由 watchdog 吸收

接下来的重点，不是再堆补丁，而是继续让 graph 只消费 runtime 建好的事实。
