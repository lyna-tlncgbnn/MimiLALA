# 2026-04-02 Execution Panel Timeline Alignment

## 背景

执行区此前存在两个问题：

1. 面板整体相对 `Agent` 主体有额外左缩进，视觉上像是漂浮出来的一层。
2. 折叠区样式更像普通卡片列表，不像清晰的时间线结构。

## 本次调整

文件：

- `ui/src/features/chat/components/run-steps-panel.tsx`
- `ui/src/features/chat/components/conversation-run-list.tsx`

### 1. 去掉执行区额外左缩进

历史 run 和当前 run 渲染时，不再额外包一层 `ml-6`。

结果：

- 执行区与 `Agent` 内容左边缘对齐
- 层级关系保留，但不会再向右漂移

### 2. 执行区改成时间线样式

`RunStepsPanel` 重新组织为：

- 标题行左侧圆点
- 展开时纵向连接线
- 每个 step 左侧圆点 + 竖线续接

这样更接近“步骤流”而不是“若干独立卡片”。

### 3. 折叠交互改成右侧箭头

执行标题行和每个步骤行都改成：

- 左侧标题信息
- 右侧 `ChevronRight / ChevronDown`

这样折叠状态更直观，且和参考图一致。

## 结果

执行区现在更像：

- `Agent` 下方的子时间线
- 左对齐的步骤轨迹
- 可展开 / 收起的结构化过程面板

## 验证

已完成：

- `npm run build`
