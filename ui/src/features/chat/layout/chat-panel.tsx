import type { ChatMessage, RunSummary } from "@/shared/api/api";
import { ChatComposer } from "@/features/chat/components/chat-composer";
import { ConversationRunList } from "@/features/chat/components/conversation-run-list";
import type { ActiveRunState } from "@/features/chat/types";
import { ChatHeader } from "@/features/chat/layout/chat-header";

export function ChatPanel({
  activeRun,
  messages,
  draft,
  isSending,
  loadingHistory,
  loadingRuns,
  runs,
  error,
  sidebarCollapsed,
  onDraftChange,
  onSend,
  onToggleSidebar,
}: {
  activeRun: ActiveRunState | null;
  messages: ChatMessage[];
  draft: string;
  isSending: boolean;
  loadingHistory: boolean;
  loadingRuns: boolean;
  runs: RunSummary[];
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
        <ConversationRunList
          activeRun={activeRun}
          error={error}
          loadingHistory={loadingHistory}
          loadingRuns={loadingRuns}
          messages={messages}
          onDraftSuggestion={onDraftChange}
          runs={runs}
        />

        <ChatComposer draft={draft} isSending={isSending} onDraftChange={onDraftChange} onSend={onSend} />
      </div>
    </section>
  );
}
