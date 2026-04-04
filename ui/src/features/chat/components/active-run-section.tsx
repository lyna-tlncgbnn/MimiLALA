import { AgentSection } from "@/features/chat/components/agent-section";
import { RunStepsPanel } from "@/features/chat/components/run-steps-panel";
import { UserPrompt } from "@/features/chat/components/user-prompt";
import {
  formatRunMessageTime,
  toActiveTimelineStep,
} from "@/features/chat/lib/conversation-run-list-utils";
import type { ActiveRunState } from "@/features/chat/types";

export function ActiveRunSection({
  run,
}: {
  run: ActiveRunState;
}) {
  const hasSteps = run.steps.length > 0 || Boolean(run.error);

  return (
    <article className="space-y-4">
      <UserPrompt
        content={run.userContent}
        timestamp={formatRunMessageTime(run.startedAt)}
      />

      <AgentSection body={run.finalContent} streaming={run.status === "running"}>
        {hasSteps ? (
          <RunStepsPanel
            defaultExpanded
            error={run.error}
            status={run.status}
            steps={run.steps.map(toActiveTimelineStep)}
          />
        ) : null}
      </AgentSection>
    </article>
  );
}
