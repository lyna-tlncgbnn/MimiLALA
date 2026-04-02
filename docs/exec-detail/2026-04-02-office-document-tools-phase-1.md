# 2026-04-02 Office Document Tools Phase 1

## 本次执行目标

为普通用户场景补上第一批更实用的办公类文档工具：

- `read_xlsx`
- `read_pptx`
- 增强 `read_docx`
- `batch_read_documents`

本次优先目标是：

- 保持当前主链路不变
- 继续沿用项目根目录访问边界
- 尽量不增加新的第三方依赖

## 实现策略

本次没有引入新的 Office 解析依赖，而是继续沿用 OOXML 文件本质上是 zip 包的特点，直接解析：

- `.docx`
- `.xlsx`
- `.pptx`

这样做的原因是：

- 当前项目已有 `read_docx` 的标准库解析基础
- 第一版以文本提取和结构预览为主，不需要完整 Office 编辑能力
- 避免为当前阶段过早引入较重依赖

## 代码改动

修改文件：

- `agentbot/tools/filesystem.py`

### 1. 增强 `read_docx`

从原先只提取段落文本，增强为：

- 识别标题样式并标注
- 提取表格内容
- 按文档主体顺序输出

当前结果更接近办公文档阅读，而不是简单 XML 扫描。

### 2. 新增 `read_xlsx`

当前能力：

- 读取 workbook 中的 sheet 列表
- 读取每个 sheet 的预览行
- 支持 shared strings、布尔值与普通数值
- 限制预览行数，避免超长输出

### 3. 新增 `read_pptx`

当前能力：

- 按 slide 顺序提取文本
- 适合快速阅读汇报、提纲、演示材料

### 4. 新增 `batch_read_documents`

当前能力：

- 读取目录第一层中的受支持文档
- 逐个拼接预览结果
- 适合作为“批量看一组资料”的第一版入口

当前支持的文件类型：

- `.txt`
- `.md`
- `.pdf`
- `.docx`
- `.xlsx`
- `.pptx`

## 验证

本次使用最小样例文件验证：

- `read_docx`
- `read_xlsx`
- `read_pptx`
- `batch_read_documents`

并额外运行：

```powershell
.\.venv\Scripts\python.exe -m compileall agentbot
```

验证通过，说明本次改动未引入明显语法或导入错误。

## 文档同步

本次同步更新：

- `README.md`
- `docs/architecture/tools.md`

## 当前边界

第一版办公工具仍然保持保守边界：

- `read_docx` 不处理批注、页眉页脚、图片 OCR
- `read_xlsx` 不做复杂公式求值与格式恢复
- `read_pptx` 主要提取文本，不还原版式与图表语义
- `batch_read_documents` 当前不递归子目录

## 当前结果

截至本次执行结束，项目的文件工具层已经从：

- 文本 / PDF / 简单 DOCX

扩展到：

- Word
- Excel
- PowerPoint
- 批量资料预览

这比继续只堆开发者向工具，更符合当前“给普通人用”的产品方向。
