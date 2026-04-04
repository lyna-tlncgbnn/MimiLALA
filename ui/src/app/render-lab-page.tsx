import { Link } from "react-router-dom";

import { MessageContent } from "@/features/chat/components/message-content";

const markdownFixture = `# Rich Markdown Render Lab

这页用于验证 agent 回答的渲染能力，覆盖标题、表格、代码块、公式、任务列表、脚注和图片。

## 1. Typography

支持 **粗体**、*斜体*、~~删除线~~、行内代码 \`pnpm build\`，以及 [外部链接](https://github.com/remarkjs/react-markdown)。

> 这是一个引用块，用来确认正文层级、背景和边线都已经生效。

### Task List

- [x] Markdown
- [x] Table
- [x] Code highlight
- [x] Math
- [ ] Mermaid（本阶段暂未启用）

## 2. GFM Table

| Capability | Status | Notes |
| --- | --- | --- |
| Paragraphs | Ready | 使用统一排版节奏 |
| Tables | Ready | 包含横向滚动和表头样式 |
| Code Blocks | Ready | 支持语言标签与复制 |
| Math | Ready | 通过 KaTeX 渲染 |

## 3. Code

\`\`\`python
from dataclasses import dataclass

@dataclass
class RunSummary:
    run_id: str
    status: str

def format_summary(run: RunSummary) -> str:
    return f"{run.run_id}: {run.status}"
\`\`\`

\`\`\`json
{
  "event": "assistant_finalized",
  "data": {
    "message_id": "msg_123",
    "content": "Rendered as markdown"
  }
}
\`\`\`

## 4. Math

行内公式：$E = mc^2$。

块级公式：

$$
\\int_0^1 x^2 \\, dx = \\frac{1}{3}
$$

## 5. Image

![OpenAI wordmark](https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg)

## 6. Footnote

这里有一个脚注示例。[^1]

[^1]: GFM 脚注由 \`remark-gfm\` 解析。
`;

export function RenderLabPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(17,24,39,0.03),_transparent_28%),linear-gradient(180deg,_#ffffff_0%,_#fbfbfc_52%,_#f4f4f5_100%)] px-6 py-8 text-foreground">
      <div className="mx-auto max-w-[960px]">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Render Lab
            </div>
            <h1 className="mt-2 text-[32px] font-semibold tracking-tight">AI Rich Content Renderer</h1>
            <p className="mt-2 max-w-[760px] text-[14px] leading-7 text-muted-foreground">
              用这页快速检查 markdown、代码块、表格、公式、图片和脚注的渲染表现。
            </p>
          </div>
          <Link
            className="rounded-full border border-border bg-white px-4 py-2 text-[13px] font-medium text-foreground transition hover:bg-panel-strong"
            to="/"
          >
            Back to Chat
          </Link>
        </div>

        <section className="rounded-[28px] border border-[rgba(32,33,35,0.08)] bg-[rgba(255,255,255,0.82)] px-6 py-6 shadow-[0_20px_60px_rgba(32,33,35,0.06)] backdrop-blur-sm">
          <MessageContent content={markdownFixture} mode="markdown" />
        </section>
      </div>
    </main>
  );
}
