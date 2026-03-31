import type { ChatMessage } from "@/lib/api";
import { ChatComposer } from "@/components/chat/chat-composer";
import { MessageList } from "@/components/chat/message-list";
import { ChatHeader } from "@/components/layout/chat-header";

export function ChatPanel({
  messages,
  draft,
  isSending,
  loadingHistory,
  error,
  sidebarCollapsed,
  onDraftChange,
  onSend,
  onToggleSidebar,
}: {
  messages: ChatMessage[];
  draft: string;
  isSending: boolean;
  loadingHistory: boolean;
  error: string | null;
  sidebarCollapsed: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void | Promise<void>;
  onToggleSidebar: () => void;
}) {
  return (
    <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-transparent">
      <ChatHeader onToggleSidebar={onToggleSidebar} sidebarCollapsed={sidebarCollapsed} />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden px-3 py-3">
        <MessageList
          error={error}
          loadingHistory={loadingHistory}
          messages={messages}
          onDraftSuggestion={onDraftChange}
        />

        <ChatComposer draft={draft} isSending={isSending} onDraftChange={onDraftChange} onSend={onSend} />
      </div>
    </section>
  );
}
