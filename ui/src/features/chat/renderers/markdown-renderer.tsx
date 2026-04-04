import { Component, type ReactNode } from "react";
import type { Components } from "react-markdown";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { CodeBlock } from "@/features/chat/renderers/code-block";
import { getCodeLanguage } from "@/features/chat/renderers/render-utils";

const markdownComponents: Components = {
  p: ({ children }) => <p>{children}</p>,
  strong: ({ children }) => <strong>{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  del: ({ children }) => <del>{children}</del>,
  h1: ({ children }) => <h1>{children}</h1>,
  h2: ({ children }) => <h2>{children}</h2>,
  h3: ({ children }) => <h3>{children}</h3>,
  h4: ({ children }) => <h4>{children}</h4>,
  h5: ({ children }) => <h5>{children}</h5>,
  h6: ({ children }) => <h6>{children}</h6>,
  ul: ({ children }) => <ul>{children}</ul>,
  ol: ({ children }) => <ol>{children}</ol>,
  li: ({ children, ...props }) => (
    <li className={props.className?.includes("task-list-item") ? "agent-markdown-task-item" : undefined}>
      {children}
    </li>
  ),
  blockquote: ({ children }) => <blockquote>{children}</blockquote>,
  hr: () => <hr />,
  a: ({ children, href }) => (
    <a href={href} rel="noreferrer noopener" target="_blank">
      {children}
    </a>
  ),
  img: ({ alt, src }) => <img alt={alt ?? ""} loading="lazy" src={src ?? ""} />,
  table: ({ children }) => (
    <div className="agent-markdown-table-wrap">
      <table>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead>{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr>{children}</tr>,
  th: ({ children }) => <th>{children}</th>,
  td: ({ children }) => <td>{children}</td>,
  input: ({ checked, disabled, type }) => {
    if (type !== "checkbox") {
      return <input checked={checked} disabled={disabled} type={type} />;
    }
    return <input checked={checked} className="agent-markdown-checkbox" disabled readOnly type="checkbox" />;
  },
  code: ({ children, className, node, ...props }) => {
    const isInline = !className && node?.position?.start.line === node?.position?.end.line;
    if (isInline) {
      return (
        <code className="agent-inline-code" {...props}>
          {children}
        </code>
      );
    }

    return <CodeBlock language={getCodeLanguage(className)}>{children}</CodeBlock>;
  },
  pre: ({ children }) => <>{children}</>,
};

class MarkdownErrorBoundary extends Component<
  {
    children: ReactNode;
    content: string;
  },
  {
    hasError: boolean;
  }
> {
  state = {
    hasError: false,
  };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidUpdate(previousProps: Readonly<{ children: ReactNode; content: string }>) {
    if (previousProps.content !== this.props.content && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  override render() {
    if (this.state.hasError) {
      return <div className="min-w-0 whitespace-pre-wrap break-words">{this.props.content}</div>;
    }

    return this.props.children;
  }
}

export function MarkdownRenderer({
  content,
}: {
  content: string;
}) {
  return (
    <MarkdownErrorBoundary content={content}>
      <div className="agent-markdown min-w-0 break-words">
        <ReactMarkdown
          components={markdownComponents}
          rehypePlugins={[rehypeKatex, rehypeHighlight]}
          remarkPlugins={[remarkGfm, remarkMath]}
          urlTransform={defaultUrlTransform}
        >
          {content}
        </ReactMarkdown>
      </div>
    </MarkdownErrorBoundary>
  );
}
