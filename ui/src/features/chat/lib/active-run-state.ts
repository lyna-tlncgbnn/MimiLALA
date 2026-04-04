import type { ChatStreamEvent } from "@/features/chat/api/chat-schemas";
import type { ActiveRunState, ActiveRunStep } from "@/features/chat/types";

export type StreamPhase = "idle" | "running" | "completed" | "failed";
export type TerminalRunState = "completed" | "failed" | null;

export function upsertActiveStep(current: ActiveRunStep[], next: ActiveRunStep) {
  const index = current.findIndex(
    (step) =>
      (next.step_id && step.step_id === next.step_id) ||
      (!next.step_id && next.tool_call_id && step.tool_call_id === next.tool_call_id),
  );

  if (index === -1) {
    return [...current, next];
  }

  return current.map((step, stepIndex) => (stepIndex === index ? { ...step, ...next } : step));
}

export function createPendingActiveRun(params: {
  conversationId: string;
  content: string;
}): ActiveRunState {
  return {
    localId: `local-run-${crypto.randomUUID()}`,
    runId: null,
    conversationId: params.conversationId,
    startedAt: new Date().toISOString(),
    userMessageId: null,
    userContent: params.content,
    status: "running",
    steps: [],
    finalMessageId: null,
    finalContent: "",
    finalTimestamp: null,
    error: null,
  };
}

export function applyStreamEventToActiveRun(params: {
  current: ActiveRunState | null;
  event: ChatStreamEvent;
  fallbackUserContent: string;
  activeConversationId: string | null;
}): {
  nextActiveRun: ActiveRunState | null;
  nextPhase: StreamPhase | null;
  nextError: string | null | undefined;
} {
  const { current, event, fallbackUserContent, activeConversationId } = params;

  if (event.event === "run_started") {
    return {
      nextPhase: "running",
      nextError: null,
      nextActiveRun: {
        localId: current?.localId ?? `local-run-${crypto.randomUUID()}`,
        runId: event.data.run_id,
        conversationId: event.data.conversation_id,
        startedAt: event.data.started_at,
        userMessageId: event.data.user_message_id,
        userContent: event.data.content || fallbackUserContent,
        status: "running",
        steps: current?.steps ?? [],
        finalMessageId: null,
        finalContent: current?.finalContent ?? "",
        finalTimestamp: null,
        error: null,
      },
    };
  }

  if (event.event === "step_started") {
    return {
      nextPhase: "running",
      nextError: undefined,
      nextActiveRun: current
        ? {
            ...current,
            status: "running",
            steps: upsertActiveStep(current.steps, {
              step_id: event.data.step_id,
              step_type: event.data.step_type,
              title: event.data.title,
              status: event.data.status,
              display_mode: event.data.display_mode,
              tool_name: event.data.tool_name,
              tool_call_id: event.data.tool_call_id,
              args: event.data.args,
              timestamp: event.data.timestamp,
            }),
          }
        : current,
    };
  }

  if (event.event === "step_completed") {
    return {
      nextPhase: null,
      nextError: undefined,
      nextActiveRun: current
        ? {
            ...current,
            steps: upsertActiveStep(current.steps, {
              step_id: event.data.step_id,
              step_type: event.data.step_type,
              title: event.data.title,
              status: event.data.status,
              display_mode: "timeline",
              tool_name: event.data.tool_name,
              tool_call_id: event.data.tool_call_id,
              output: event.data.output,
              timestamp: event.data.timestamp,
            }),
          }
        : current,
    };
  }

  if (event.event === "assistant_final_delta") {
    return {
      nextPhase: "running",
      nextError: undefined,
      nextActiveRun: current
        ? {
            ...current,
            finalMessageId: event.data.message_id,
            finalContent: `${current.finalContent}${event.data.delta}`,
          }
        : current,
    };
  }

  if (event.event === "assistant_finalized") {
    return {
      nextPhase: "completed",
      nextError: null,
      nextActiveRun: current
        ? {
            ...current,
            status: "completed",
            finalMessageId: event.data.message_id,
            finalContent: event.data.content,
            finalTimestamp: event.data.timestamp,
          }
        : current,
    };
  }

  if (event.event === "run_failed") {
    return {
      nextPhase: "failed",
      nextError: event.data.message,
      nextActiveRun: current
        ? {
            ...current,
            status: "failed",
            error: event.data.message,
          }
        : {
            localId: `local-run-${crypto.randomUUID()}`,
            runId: event.data.run_id ?? null,
            conversationId: activeConversationId,
            startedAt: new Date().toISOString(),
            userMessageId: null,
            userContent: fallbackUserContent,
            status: "failed",
            steps: [],
            finalMessageId: null,
            finalContent: "",
            finalTimestamp: null,
            error: event.data.message,
          },
    };
  }

  if (event.event === "run_completed") {
    return {
      nextPhase: "completed",
      nextError: null,
      nextActiveRun: current,
    };
  }

  return {
    nextPhase: null,
    nextError: undefined,
    nextActiveRun: current,
  };
}
