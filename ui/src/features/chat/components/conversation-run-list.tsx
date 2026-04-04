import { memo, useEffect, useMemo, useRef } from "react";

import type { ChatMessage, RunSummary } from "@/features/chat/api/chat-schemas";
import { ActiveRunSection } from "@/features/chat/components/active-run-section";
import { ConversationEmptyState } from "@/features/chat/components/conversation-empty-state";
import { HistoricalRunSection } from "@/features/chat/components/historical-run-section";
import type { ActiveRunState } from "@/features/chat/types";
import { ScrollArea } from "@/shared/ui/scroll-area";

export const ConversationRunList = memo(function ConversationRunList({
  activeRun,
  error,
  loadingHistory,
  loadingRuns,
  messages,
  onDraftSuggestion,
  runs,
}: {
  activeRun: ActiveRunState | null;
  error: string | null;
  loadingHistory: boolean;
  loadingRuns: boolean;
  messages: ChatMessage[];
  onDraftSuggestion: (value: string) => void;
  runs: RunSummary[];
}) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, runs, activeRun, loadingHistory, loadingRuns, error]);

  const messagesById = useMemo(() => {
    const map = new Map<string, ChatMessage>();
    for (const message of messages) {
      if (message.message_id) {
        map.set(message.message_id, message);
      }
    }
    return map;
  }, [messages]);

  const orderedRuns = useMemo(
    () =>
      [...runs].sort(
        (left, right) => new Date(left.started_at).getTime() - new Date(right.started_at).getTime(),
      ),
    [runs],
  );

  const persistedRunIds = useMemo(() => new Set(runs.map((run) => run.run_id)), [runs]);
  const shouldShowActiveRun =
    Boolean(activeRun) &&
    (!activeRun?.runId || !persistedRunIds.has(activeRun.runId) || activeRun.status === "failed");
  const shouldShowEmptyState =
    !loadingHistory && !loadingRuns && orderedRuns.length === 0 && !shouldShowActiveRun;

  return (
    <ScrollArea className="mt-2 min-h-0 flex-1 pr-1">
      <div className="min-w-0 space-y-10 pb-4">
        {loadingHistory || loadingRuns ? (
          <article className="rounded-[18px] border border-border bg-[rgba(255,255,255,0.88)] px-4 py-3 text-[13px] text-muted-foreground">
            正在加载会话内容...
          </article>
        ) : null}

        {shouldShowEmptyState ? <ConversationEmptyState onDraftSuggestion={onDraftSuggestion} /> : null}

        {!loadingHistory && !loadingRuns
          ? orderedRuns.map((run) => (
              <HistoricalRunSection
                key={run.run_id}
                assistantMessage={run.final_message_id ? messagesById.get(run.final_message_id) : undefined}
                run={run}
                userMessage={run.user_message_id ? messagesById.get(run.user_message_id) : undefined}
              />
            ))
          : null}

        {shouldShowActiveRun && activeRun ? <ActiveRunSection run={activeRun} /> : null}

        {error ? (
          <article className="rounded-[18px] border border-[rgba(154,50,36,0.16)] bg-[rgba(154,50,36,0.05)] px-4 py-3 text-[13px] leading-5 text-foreground">
            {error}
          </article>
        ) : null}

        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
});
