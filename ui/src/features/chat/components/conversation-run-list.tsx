import { memo, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, ChevronRight, Sparkles, User2, Wrench } from "lucide-react";

import { MessageContent } from "@/features/chat/components/message-content";
import { RunStepsPanel, type TimelineStep } from "@/features/chat/components/run-steps-panel";
import type { ActiveRunState } from "@/features/chat/types";
import { getRunSteps, type ChatMessage, type RunStep, type RunSummary } from "@/shared/api/api";
import { ScrollArea } from "@/shared/ui/scroll-area";

const emptyStatePrompts = [
  "帮我总结一下这个项目目前的架构。",
  "读取某个文件，然后帮我做一个摘要。",
  "新建一个会话，并规划一下下一步开发任务。",
  "告诉我当前默认会话里最近做了什么。",
];

function formatMessageTime(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat("zh-CN", {
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

function stringifyPayload(raw: string | null | undefined) {
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "string") {
      return parsed;
    }
    if (parsed && typeof parsed === "object" && "text" in parsed && typeof parsed.text === "string") {
      return parsed.text;
    }
    return JSON.stringify(parsed, null, 2);
  } catch {
    return raw;
  }
}

function toHistoricalTimelineStep(step: RunStep): TimelineStep {
  return {
    id: step.step_id,
    stepType: step.step_type,
    title: step.title,
    status: step.status,
    timestamp: step.ended_at ?? step.started_at,
    toolName: step.tool_name,
    summary: step.summary_text,
    input: stringifyPayload(step.input_json),
    output: stringifyPayload(step.output_json),
  };
}

function toActiveTimelineStep(step: ActiveRunState["steps"][number]): TimelineStep {
  return {
    id: step.step_id ?? step.tool_call_id ?? `${step.step_type}:${step.timestamp}`,
    stepType: step.step_type,
    title: step.title,
    status: step.status,
    timestamp: step.timestamp,
    toolName: step.tool_name ?? null,
    input: step.args ? JSON.stringify(step.args, null, 2) : null,
    output: step.output ?? null,
  };
}

function UserPrompt({
  content,
  timestamp,
}: {
  content: string;
  timestamp?: string | null;
}) {
  return (
    <div className="flex w-full justify-end">
      <div className="max-w-[72%] px-2 py-1 text-right text-[14px] leading-7 text-foreground">
        <div className="flex items-center justify-end gap-2 text-[12px] font-medium text-muted-foreground">
          <User2 className="h-4 w-4" />
          <span>你</span>
          {timestamp ? <span>{timestamp}</span> : null}
        </div>
        <div className="mt-1 whitespace-pre-wrap break-words">{content}</div>
      </div>
    </div>
  );
}

function AgentSection({
  body,
  bodyTimestamp,
  children,
  streaming = false,
  status = "completed",
}: {
  body: string;
  bodyTimestamp?: string | null;
  children?: React.ReactNode;
  streaming?: boolean;
  status?: "running" | "completed" | "failed";
}) {
  const hasBody = body.trim().length > 0;
  const showWaitingIndicator = streaming && !hasBody;

  return (
    <section className="max-w-[84%] space-y-4">
      {showWaitingIndicator ? (
        <div className="flex items-center gap-3 text-foreground">
          <Sparkles className="h-5 w-5 animate-pulse text-[rgba(32,33,35,0.78)]" />
        </div>
      ) : null}

      {children}

      {hasBody ? (
        <div className="pl-1 text-[15px] leading-8 text-foreground">
          <MessageContent content={body} mode="markdown" />
        </div>
      ) : null}
    </section>
  );
}

function ExecutionHint({
  onOpen,
}: {
  onOpen: () => void;
}) {
  return (
    <button
      className="inline-flex items-center gap-2 px-1 py-1 text-left text-[13px] font-medium text-[rgba(60,62,68,0.62)] transition hover:text-foreground"
      onClick={onOpen}
      type="button"
    >
      <Wrench className="h-4 w-4" />
      <span>查看执行</span>
      <ChevronRight className="h-4 w-4" />
    </button>
  );
}

function HistoricalRunSection({
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
    queryKey: ["run-steps", run.run_id],
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
          timestamp={formatMessageTime(userMessage.timestamp)}
        />
      ) : null}

      {(assistantMessage?.content || run.error_message) ? (
        <AgentSection
          body={assistantMessage?.content ?? run.error_message ?? ""}
          bodyTimestamp={formatMessageTime(assistantMessage?.timestamp ?? run.ended_at)}
          status={run.status === "failed" ? "failed" : "completed"}
        >
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

function ActiveRunSection({
  run,
}: {
  run: ActiveRunState;
}) {
  const hasSteps = run.steps.length > 0 || Boolean(run.error);

  return (
    <article className="space-y-4">
      <UserPrompt
        content={run.userContent}
        timestamp={formatMessageTime(run.startedAt)}
      />

      <AgentSection
        body={run.finalContent}
        bodyTimestamp={formatMessageTime(run.finalTimestamp ?? run.startedAt)}
        status={run.status}
        streaming={run.status === "running"}
      >
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

        {shouldShowEmptyState ? (
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
        ) : null}

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
