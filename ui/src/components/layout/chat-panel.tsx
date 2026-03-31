import type { ChatMessage } from "@/lib/api";
import { ChatComposer } from "@/components/chat/chat-composer";
import { MessageList } from "@/components/chat/message-list";

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

      <MessageList
        error={error}
        loadingHistory={loadingHistory}
        messages={messages}
        onDraftSuggestion={onDraftChange}
      />

      <ChatComposer draft={draft} isSending={isSending} onDraftChange={onDraftChange} onSend={onSend} />
    </section>
  );
}
