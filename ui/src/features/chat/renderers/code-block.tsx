import { Check, Copy } from "lucide-react";
import { memo, useEffect, useState, type ReactNode } from "react";

import { extractTextContent } from "@/features/chat/renderers/render-utils";
import { cn } from "@/shared/lib/utils";

export const CodeBlock = memo(function CodeBlock({
  children,
  language,
}: {
  children: ReactNode;
  language?: string | null;
}) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");

  useEffect(() => {
    if (copyState === "idle") {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      setCopyState("idle");
    }, 1800);

    return () => {
      window.clearTimeout(timer);
    };
  }, [copyState]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(extractTextContent(children).replace(/\n$/, ""));
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  };

  return (
    <div className="not-prose my-3 overflow-hidden rounded-[16px] border border-[rgba(32,33,35,0.08)] bg-[rgba(255,255,255,0.96)] shadow-[0_10px_28px_rgba(32,33,35,0.05)]">
      <div className="flex items-center justify-between border-b border-[rgba(32,33,35,0.07)] bg-[rgba(32,33,35,0.02)] px-3 py-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[rgba(32,33,35,0.5)]">
          {language ?? "text"}
        </span>
        <button
          aria-label={copyState === "copied" ? "Copied code" : "Copy code"}
          className={cn(
            "inline-flex h-7 items-center gap-1 rounded-full px-2.5 text-[11px] font-medium transition",
            copyState === "copied"
              ? "bg-[rgba(32,33,35,0.08)] text-foreground"
              : copyState === "error"
                ? "bg-[rgba(180,35,24,0.10)] text-[rgba(154,50,36,0.92)]"
                : "bg-[rgba(32,33,35,0.04)] text-[rgba(32,33,35,0.72)] hover:bg-[rgba(32,33,35,0.08)] hover:text-foreground",
          )}
          onClick={() => void handleCopy()}
          type="button"
        >
          {copyState === "copied" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          <span>{copyState === "copied" ? "Copied" : copyState === "error" ? "Retry" : "Copy"}</span>
        </button>
      </div>
      <div className="overflow-x-auto px-3 py-2.5">
        <pre className="m-0 min-w-full bg-transparent p-0">
          <code className="block bg-transparent font-mono text-[12px] leading-[1.7] text-[rgba(32,33,35,0.9)]">
            {children}
          </code>
        </pre>
      </div>
    </div>
  );
});
