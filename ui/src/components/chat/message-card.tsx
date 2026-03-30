import { Hammer, Search, Sparkles } from "lucide-react";

import { MessageContent } from "@/components/chat/message-content";
import { cn } from "@/lib/utils";

export function MessageCard({
  role,
  title,
  main,
}: {
  role: "user" | "assistant" | "tool";
  title: string;
  main: string;
}) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";
  const isTool = role === "tool";

  return (
    <article
      className={cn(
        "inline-flex w-fit min-w-0 flex-col rounded-[14px] border px-3 py-2",
        isUser && "max-w-[70%] border-[rgba(180,106,44,0.12)] bg-[rgba(180,106,44,0.035)]",
        isAssistant && "max-w-[80%] border border-border bg-[rgba(255,255,255,0.92)]",
        isTool && "max-w-[84%] border border-border bg-[rgba(247,247,245,0.9)]",
      )}
    >
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
        {isAssistant ? (
          <Sparkles className="h-3.5 w-3.5" />
        ) : isTool ? (
          <Hammer className="h-3.5 w-3.5" />
        ) : (
          <Search className="h-3.5 w-3.5" />
        )}
        {title}
      </div>

      <div className="mt-1 text-[13px] leading-5 text-foreground">
        <MessageContent content={main} mode={isAssistant ? "markdown" : "plain"} />
      </div>
    </article>
  );
}
