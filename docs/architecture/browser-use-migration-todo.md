# Browser-Use Migration Todo

## 目标

这份文档用于跟踪 AgentBot 浏览器子图继续向 `browser-use` 靠拢时，哪些能力值得迁移、哪些边界当前保持不变，以及推荐的实施顺序。

前提保持不变：

- 浏览器 agent 继续作为 LangGraph 子图存在
- 不把浏览器细节上浮到主图或 transcript 主链路
- 不破坏现有 run / run_steps / artifacts / timeline / 数据落盘

## 已经迁移或已明显借鉴

- [x] 浏览器任务以 specialist subgraph 形式运行
- [x] 观察-规划-执行-评估的浏览器闭环
- [x] 稳定 selector 映射替代 DOM 序号回放
- [x] 面向 LLM 的可交互页面摘要
- [x] iframe-aware observation
- [x] AX / aria 相关信息补充
- [x] 轻量 loop detection
- [x] runtime 事件回收：navigation / dialog / download / tab
- [x] planner prompt 借鉴 `system_prompt_no_thinking.md` 的高价值浏览器规则
- [x] 第一轮关键动作补充：`press_enter`、`new_tab_navigate`

## 高优先级待迁移

### 1. Planner state 更像 browser-use

- [x] 在浏览器子图状态里引入更明确的上一步评估字段
- [x] 给 planner 显式输入 `evaluation_previous_goal`
- [x] 给 planner 增加轻量 `memory` 字段，而不是只看动作历史
- [x] 让 planner 更稳定地区分“已完成 / 未完成 / 卡住 / 需要换策略”

价值：

- 直接提升“聪明感”
- 降低搜索、自动完成、弹窗场景下的误判
- 比先上 event bus/watchdog 的收益更直接

### 2. 更丰富的浏览器动作集合

- [ ] `dismiss_overlay` / `close_popup`
- [ ] `open_link_in_new_tab`
- [ ] `extract_page` 或轻量页面深读动作
- [ ] 更明确的 `select_suggestion` / combobox 处理
- [ ] `hover`
- [ ] `select_option`

价值：

- 让提示词里的规则有对应的 runtime 能力
- 减少“模型知道该怎么做，但没有合适动作”的落差

### 3. Observation 再继续向 browser-use 靠拢

- [x] 把 observation 拆成 raw capture + serialization 两段式
- [x] 在 summary 中补 semantic groups / prioritized hints
- [ ] 更强的 modal / overlay / cookie banner 识别
- [ ] 更稳定的新旧元素差异标识
- [ ] 更清晰的元素层级和父子关系表达
- [ ] 更丰富的页面错误 / 阻塞态标记
- [ ] 如果需要，再评估截图框选标注层

价值：

- 继续提升 planner 判断质量
- 帮助模型优先处理阻塞页面元素

## 中优先级待迁移

### 4. 下载 / 新标签页 / 页面副作用继续细化

- [ ] 新 tab 的父子关系记录
- [ ] 新 tab 焦点策略与回切策略
- [ ] 更清晰的下载完成 / 下载中 / 下载失败状态
- [ ] PDF 相关专项处理

### 5. 更完整的 done / 完成校验语义

- [ ] 在子图内部显式记录任务完成核验结果
- [ ] 对“任务成功完成”和“提前结束”做更清晰区分
- [ ] 必要时为 browser_finish 增加更结构化结果模型

### 6. 轻量 plan / todo 能力

- [ ] 只在复杂长任务下启用浏览器子图内部 plan
- [ ] 不直接照搬 browser-use 全量文件工具链
- [ ] 先评估是否需要最小 todo state，而不是文件写入

## 低优先级或暂不建议立刻迁移

### 7. Event bus / watchdog 全量架构

- [ ] 继续观察 `actions.py` 和 `session.py` 的复杂度是否明显上升
- [ ] 如果副作用处理开始分散失控，再拆成 watcher / handler
- [ ] 先做轻量 runtime 分层，再决定是否抽成 event bus

当前判断：

- 这是中期演进方向
- 不是现在的第一优先级

### 8. browser-use 完整 Agent loop 输出结构

- [ ] 暂不直接迁移 `plan_update` / `current_plan_item` / 文件工具协议
- [ ] 暂不迁移整套 browser-use `done` schema
- [x] 浏览器子图已支持 browser-use 风格的多动作 step 输出与顺序执行

当前判断：

- 当前保留 LangGraph 子图外壳，但内部 step 已升级为多动作序列
- 等 planner state 和动作集合再长一层后再评估

## 推荐实施顺序

1. 先做 planner state 增强
2. 再做第二轮关键浏览器动作
3. 再做 observation 的阻塞态识别增强
4. 然后再看 runtime 分层是否值得继续抽象
5. 最后才考虑 event bus / watchdog 化和更完整 agent loop

## 不建议跨越的边界

- 不把浏览器 agent 下沉成普通 tool 黑盒
- 不把浏览器动作直接塞回主 agent 的普通 tool loop
- 不改动现有 run-oriented persistence 主链路
- 不为了模仿 browser-use 而放弃 LangGraph 子图编排
