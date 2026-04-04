import { Bot, Sparkles } from "lucide-react";

import { emptyConversationPrompts } from "@/features/chat/lib/conversation-run-list-utils";

export function ConversationEmptyState({
  onDraftSuggestion,
}: {
  onDraftSuggestion: (value: string) => void;
}) {
  return (
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
            这里会显示每一次任务的提问、执行过程和最终回答。
          </p>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {emptyConversationPrompts.map((prompt) => (
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
  );
}
