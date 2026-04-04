import { memo, useEffect, useMemo, useRef } from "react";
import { Bot, Sparkles } from "lucide-react";

import type { ChatMessage } from "@/features/chat/api/chat-schemas";
import { MessageCard } from "@/features/chat/components/message-card";
import { ScrollArea } from "@/shared/ui/scroll-area";

const emptyStatePrompts = [
  "帮我总结一下这个项目目前的架构。",
  "读取某个文件，然后帮我做一个摘要。",
  "帮我新建一个会话，并规划一下下一步开发任务。",
  "告诉我当前默认会话里最近做了什么。",
];

function getMessageTitle(message: ChatMessage) {
  if (message.role === "assistant") {
    return "Agent";
  }
  if (message.role === "tool") {
    return "Tool";
  }
  return "You";
}

function formatMessageTime(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export const MessageList = memo(function MessageList({
  messages,
  loadingHistory,
  error,
  onDraftSuggestion,
}: {
  messages: ChatMessage[];
  loadingHistory: boolean;
  error: string | null;
  onDraftSuggestion: (value: string) => void;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loadingHistory, error]);

  const messageItems = useMemo(
    () =>
      messages.map((message, index) => {
        const role: "user" | "assistant" | "tool" =
          message.role === "tool" ? "tool" : message.role === "assistant" ? "assistant" : "user";

        return {
          key: message.message_id ?? `message-${index}`,
          role,
          main: message.content,
          timestamp: formatMessageTime(message.timestamp),
          title: getMessageTitle(message),
          toolCalls: role === "assistant" ? message.tool_calls ?? [] : [],
        };
      }),
    [messages],
  );

  return (
    <ScrollArea className="mt-2 min-h-0 flex-1 pr-1">
      <div className="min-w-0 space-y-2 pb-2">
        {loadingHistory ? (
          <article className="rounded-[14px] border border-border bg-[rgba(255,255,255,0.9)] px-3 py-2.5 text-[12px] text-muted-foreground">
            正在加载会话历史...
          </article>
        ) : messages.length === 0 ? (
          <section className="flex min-h-full items-center justify-center px-4 py-8">
            <div className="w-full max-w-[760px] px-6 py-7">
              <div className="flex items-center justify-center">
                <div className="rounded-[18px] border border-[rgba(32,33,35,0.08)] bg-[rgba(32,33,35,0.03)] p-3 text-accent">
                  <Bot className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4 text-center">
                <div className="text-[24px] font-semibold tracking-tight text-foreground">开始一个新的对话</div>
                <p className="mx-auto mt-2 max-w-[560px] text-[13px] leading-6 text-muted-foreground">
                  先从一个简单问题开始，或者点下面的提示快速填充输入框。
                </p>
              </div>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {emptyStatePrompts.map((prompt) => (
                  <button
                    key={prompt}
                    className="rounded-[18px] border border-border bg-[rgba(255,255,255,0.92)] px-4 py-4 text-left transition hover:bg-white hover:shadow-[0_8px_22px_rgba(32,33,35,0.04)]"
                    onClick={() => onDraftSuggestion(prompt)}
                    type="button"
                  >
                    <div className="flex items-center gap-2 text-[13px] font-medium text-foreground">
                      <div className="rounded-[12px] bg-panel-strong p-2 text-accent">
                        <Sparkles className="h-4 w-4" />
                      </div>
                      <span>快速开始</span>
                    </div>
                    <p className="mt-3 text-[12px] leading-5 text-muted-foreground">{prompt}</p>
                  </button>
                ))}
              </div>
            </div>
          </section>
        ) : (
          messageItems.map((message) => (
            <div
              key={message.key}
              className={`flex min-w-0 w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <MessageCard
                main={message.main}
                role={message.role}
                timestamp={message.timestamp}
                title={message.title}
                toolCalls={message.toolCalls}
              />
            </div>
          ))
        )}

        {error ? (
          <article className="rounded-[14px] border border-[rgba(154,50,36,0.16)] bg-[rgba(154,50,36,0.05)] px-3 py-2.5 text-[13px] leading-5 text-foreground">
            {error}
          </article>
        ) : null}

        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
});
