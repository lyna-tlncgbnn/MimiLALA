import { MarkdownRenderer } from "@/features/chat/renderers/markdown-renderer";

export function RichContentRenderer({
  content,
  mode = "plain",
}: {
  content: string;
  mode?: "plain" | "markdown";
}) {
  if (!content) {
    return null;
  }

  if (mode === "plain") {
    return <div className="min-w-0 whitespace-pre-wrap break-words">{content}</div>;
  }

  return <MarkdownRenderer content={content} />;
}
