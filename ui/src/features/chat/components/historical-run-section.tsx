import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getRunSteps } from "@/features/chat/api/chat-api";
import { chatQueryKeys } from "@/features/chat/api/chat-query-keys";
import type { ChatMessage, RunSummary } from "@/features/chat/api/chat-schemas";
import { AgentSection } from "@/features/chat/components/agent-section";
import { ExecutionHint } from "@/features/chat/components/execution-hint";
import { RunStepsPanel } from "@/features/chat/components/run-steps-panel";
import { UserPrompt } from "@/features/chat/components/user-prompt";
import {
  formatRunMessageTime,
  toHistoricalTimelineStep,
} from "@/features/chat/lib/conversation-run-list-utils";

export function HistoricalRunSection({
  run,
  userMessage,
  assistantMessage,
}: {
  run: RunSummary;
  userMessage?: ChatMessage;
  assistantMessage?: ChatMessage;
}) {
  const [expanded, setExpanded] = useState(false);
  const stepsQuery = useQuery({
    queryKey: chatQueryKeys.runSteps(run.run_id),
    queryFn: () => getRunSteps(run.run_id),
    enabled: expanded,
  });

  const hasLoadedSteps = (stepsQuery.data?.steps.length ?? 0) > 0;
  const canShowExecutionHint = run.has_execution || run.status === "running" || run.status === "failed";
  const shouldShowExecution = expanded || stepsQuery.isLoading || stepsQuery.error instanceof Error;

  return (
    <article className="space-y-4">
      {userMessage?.content ? (
        <UserPrompt
          content={userMessage.content}
          timestamp={formatRunMessageTime(userMessage.timestamp)}
        />
      ) : null}

      {(assistantMessage?.content || run.error_message) ? (
        <AgentSection body={assistantMessage?.content ?? run.error_message ?? ""}>
          {shouldShowExecution && (stepsQuery.isLoading || stepsQuery.error instanceof Error || hasLoadedSteps) ? (
            <RunStepsPanel
              defaultExpanded={expanded}
              expanded={expanded}
              error={stepsQuery.error instanceof Error ? stepsQuery.error.message : null}
              loading={stepsQuery.isLoading}
              onExpandedChange={setExpanded}
              status={run.status === "failed" ? "failed" : "completed"}
              steps={(stepsQuery.data?.steps ?? []).map(toHistoricalTimelineStep)}
            />
          ) : canShowExecutionHint ? (
            <ExecutionHint onOpen={() => setExpanded(true)} />
          ) : null}
        </AgentSection>
      ) : null}
    </article>
  );
}
