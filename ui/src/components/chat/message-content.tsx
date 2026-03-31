import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function MessageContentInner({
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

  return (
    <div className="markdown-content min-w-0 break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-3 list-disc pl-5 last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 list-decimal pl-5 last:mb-0">{children}</ol>,
          li: ({ children }) => <li className="mb-1">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="mb-3 border-l-2 border-border pl-3 text-muted-foreground last:mb-0">
              {children}
            </blockquote>
          ),
          a: ({ children, href }) => (
            <a
              className="text-accent underline underline-offset-2"
              href={href}
              rel="noreferrer"
              target="_blank"
            >
              {children}
            </a>
          ),
          code: ({ children, className }) => {
            const isBlock = Boolean(className);
            if (isBlock) {
              return (
                <code className="block overflow-x-auto rounded-[10px] bg-[rgba(53,40,17,0.06)] px-3 py-2 font-mono text-[12px] leading-5">
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded bg-[rgba(53,40,17,0.08)] px-1.5 py-0.5 font-mono text-[0.92em]">
                {children}
              </code>
            );
          },
          pre: ({ children }) => <pre className="mb-3 last:mb-0">{children}</pre>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export const MessageContent = memo(MessageContentInner);
