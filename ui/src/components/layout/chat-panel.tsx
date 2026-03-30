import { useEffect, useRef } from "react";
import { ArrowUpRight, Bot, Sparkles } from "lucide-react";

import type { ChatMessage } from "@/lib/api";
import { MessageCard } from "@/components/chat/message-card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

const emptyStatePrompts = [
  "帮我总结一下这个项目目前的架构。",
  "读取某个文件然后帮我做一个摘要。",
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

export function ChatPanel({
  messages,
  draft,
  isSending,
  loadingHistory,
  error,
  onDraftChange,
  onSend,
}: {
  messages: ChatMessage[];
  draft: string;
  isSending: boolean;
  loadingHistory: boolean;
  error: string | null;
  onDraftChange: (value: string) => void;
  onSend: () => void | Promise<void>;
}) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loadingHistory, error]);

  return (
    <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-transparent px-3 py-3">
      <div className="flex shrink-0 items-center justify-between border-b border-[rgba(53,40,17,0.08)] pb-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Chat Surface
        </div>
        <div className="rounded-[10px] border border-border bg-[rgba(255,255,255,0.82)] px-2 py-1 text-[11px] text-muted-foreground">
          {isSending ? "处理中" : `${messages.length} 条消息`}
        </div>
      </div>

      <ScrollArea className="mt-2 min-h-0 flex-1 pr-1">
        <div className="space-y-2 pb-2">
          {loadingHistory ? (
            <article className="rounded-[14px] border border-border bg-[rgba(255,255,255,0.78)] px-3 py-2.5 text-[12px] text-muted-foreground">
              正在加载会话历史...
            </article>
          ) : messages.length === 0 ? (
            <section className="flex min-h-full items-center justify-center px-4 py-8">
              <div className="w-full max-w-[760px] px-6 py-7">
                <div className="flex items-center justify-center">
                  <div className="rounded-[18px] border border-[rgba(180,106,44,0.08)] bg-[rgba(180,106,44,0.025)] p-3 text-accent">
                    <Bot className="h-5 w-5" />
                  </div>
                </div>
                <div className="mt-4 text-center">
                  <div className="text-[24px] font-semibold tracking-tight text-foreground">
                    开始一个新的对话
                  </div>
                  <p className="mx-auto mt-2 max-w-[560px] text-[13px] leading-6 text-muted-foreground">
                    先从一个简单问题开始，或者点下面的提示快速填充输入框。
                  </p>
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {emptyStatePrompts.map((prompt) => (
                    <button
                      key={prompt}
                      className="rounded-[18px] border border-border bg-[rgba(255,255,255,0.78)] px-4 py-4 text-left transition hover:bg-white"
                      onClick={() => onDraftChange(prompt)}
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
            messages.map((message, index) => {
              const role =
                message.role === "tool" ? "tool" : message.role === "assistant" ? "assistant" : "user";
              const key = `${message.message_id ?? "msg"}:${message.timestamp ?? index}:${index}`;
              return (
                <div key={key} className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}>
                  <MessageCard main={message.content} role={role} title={getMessageTitle(message)} />
                </div>
              );
            })
          )}

          {error ? (
            <article className="rounded-[14px] border border-[rgba(154,50,36,0.16)] bg-[rgba(154,50,36,0.05)] px-3 py-2.5 text-[13px] leading-5 text-foreground">
              {error}
            </article>
          ) : null}

          <div ref={endRef} />
        </div>
      </ScrollArea>

      <div className="mt-2 shrink-0 flex items-center gap-2 rounded-[12px] border border-border bg-[rgba(255,255,255,0.84)] px-3 py-2">
        <input
          className="h-8 w-full min-w-0 bg-transparent text-[13px] text-foreground outline-none placeholder:text-muted-foreground"
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void onSend();
            }
          }}
          placeholder="输入你的问题或任务..."
          value={draft}
        />
        <Button
          className="h-8 gap-1.5 rounded-[10px] px-3 text-[12px]"
          disabled={isSending || !draft.trim()}
          onClick={() => void onSend()}
          size="sm"
        >
          {isSending ? "处理中" : "发送"}
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </section>
  );
}
