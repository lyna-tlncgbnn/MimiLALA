import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversationRuns,
  listConversations,
  renameConversation,
  streamMessage,
  type ChatStreamEvent,
} from "@/shared/api/api";
import { ChatPanel } from "@/features/chat/layout/chat-panel";
import type { ActiveRunState, ActiveRunStep } from "@/features/chat/types";
import { RenameDialog } from "@/features/conversations/components/rename-dialog";
import { SettingsDialog } from "@/features/settings/components/settings-dialog";
import { SidebarPanel } from "@/features/conversations/components/sidebar-panel";
import { useUiStore } from "@/state/ui-store";

type StreamPhase = "idle" | "running" | "completed" | "failed";
type TerminalRunState = "completed" | "failed" | null;

function upsertActiveStep(current: ActiveRunStep[], next: ActiveRunStep) {
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

export function AppShell() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sidebarCollapsed = useUiStore((state) => state.sidebarCollapsed);
  const sidebarWidth = useUiStore((state) => state.sidebarWidth);
  const settingsOpen = useUiStore((state) => state.settingsOpen);
  const renameTargetId = useUiStore((state) => state.renameTargetId);
  const toggleSidebarCollapsed = useUiStore((state) => state.toggleSidebarCollapsed);
  const setSidebarCollapsed = useUiStore((state) => state.setSidebarCollapsed);
  const setSidebarWidth = useUiStore((state) => state.setSidebarWidth);
  const setSettingsOpen = useUiStore((state) => state.setSettingsOpen);
  const setRenameTargetId = useUiStore((state) => state.setRenameTargetId);
  const [draft, setDraft] = useState("");
  const [activeRun, setActiveRun] = useState<ActiveRunState | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [streamPhase, setStreamPhase] = useState<StreamPhase>("idle");

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 1220px)");

    const syncSidebarState = () => {
      setSidebarCollapsed(mediaQuery.matches);
    };

    syncSidebarState();
    mediaQuery.addEventListener("change", syncSidebarState);
    return () => mediaQuery.removeEventListener("change", syncSidebarState);
  }, [setSidebarCollapsed]);

  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 5000,
  });

  const conversations = conversationsQuery.data ?? [];
  const activeConversationId = useMemo(() => conversationId ?? null, [conversationId]);

  useEffect(() => {
    setActiveRun(null);
    setStreamError(null);
    setStreamPhase("idle");
  }, [activeConversationId]);

  const conversationQuery = useQuery({
    queryKey: ["conversation", activeConversationId],
    queryFn: () => getConversation(activeConversationId!),
    enabled: Boolean(activeConversationId),
  });

  const runsQuery = useQuery({
    queryKey: ["conversation-runs", activeConversationId],
    queryFn: () => listConversationRuns(activeConversationId!),
    enabled: Boolean(activeConversationId),
  });

  const createConversationMutation = useMutation({
    mutationFn: (name?: string) => createConversation(name),
  });

  const renameConversationMutation = useMutation({
    mutationFn: ({ conversationId: targetId, name }: { conversationId: string; name: string }) =>
      renameConversation(targetId, name),
    onSuccess: async (_, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["conversations"] }),
        queryClient.invalidateQueries({ queryKey: ["conversation", variables.conversationId] }),
      ]);
    },
  });

  const deleteConversationMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: async (_, deletedConversationId) => {
      queryClient.removeQueries({ queryKey: ["conversation", deletedConversationId] });
      queryClient.removeQueries({ queryKey: ["conversation-runs", deletedConversationId] });
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      const nextConversations = await listConversations();
      queryClient.setQueryData(["conversations"], nextConversations);
      if (activeConversationId === deletedConversationId) {
        const nextConversationId = nextConversations[0]?.conversation_id;
        navigate(nextConversationId ? `/conversations/${nextConversationId}` : "/", { replace: true });
      }
    },
  });

  const renameConversationItem = conversations.find(
    (conversation) => conversation.conversation_id === renameTargetId,
  );

  const sidebarConversations = conversations.map((conversation) => ({
    id: conversation.conversation_id,
    title: conversation.name,
  }));

  const isStreaming = streamPhase === "running";

  const handleStartNewConversation = () => {
    setDraft("");
    setActiveRun(null);
    setStreamError(null);
    setStreamPhase("idle");
    navigate("/");
  };

  const applyStreamEvent = (event: ChatStreamEvent, fallbackUserContent: string) => {
    if (event.event === "run_started") {
      setStreamPhase("running");
      setActiveRun((current) => ({
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
      }));
      return;
    }

    if (event.event === "step_started") {
      setStreamPhase("running");
      setActiveRun((current) =>
        current
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
      );
      return;
    }

    if (event.event === "step_completed") {
      setActiveRun((current) =>
        current
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
      );
      return;
    }

    if (event.event === "assistant_final_delta") {
      setStreamPhase("running");
      setActiveRun((current) =>
        current
          ? {
              ...current,
              finalMessageId: event.data.message_id,
              finalContent: `${current.finalContent}${event.data.delta}`,
            }
          : current,
      );
      return;
    }

    if (event.event === "assistant_finalized") {
      setStreamPhase("completed");
      setStreamError(null);
      setActiveRun((current) =>
        current
          ? {
              ...current,
              status: "completed",
              finalMessageId: event.data.message_id,
              finalContent: event.data.content,
              finalTimestamp: event.data.timestamp,
            }
          : current,
      );
      return;
    }

    if (event.event === "run_failed") {
      setStreamPhase("failed");
      setStreamError(event.data.message);
      setActiveRun((current) =>
        current
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
      );
      return;
    }

    if (event.event === "run_completed") {
      setStreamPhase("completed");
      setStreamError(null);
    }
  };

  return (
    <main className="noise-overlay h-screen overflow-hidden text-[12px]">
      <div className="flex h-screen overflow-hidden border border-[rgba(32,33,35,0.08)] bg-[rgba(255,255,255,0.96)]">
        <SidebarPanel
          activeConversationId={activeConversationId}
          collapsed={sidebarCollapsed}
          conversations={sidebarConversations}
          deletingConversationId={deleteConversationMutation.isPending ? deleteConversationMutation.variables ?? null : null}
          loading={conversationsQuery.isLoading}
          onCreateConversation={handleStartNewConversation}
          onDeleteConversation={(targetId) => deleteConversationMutation.mutate(targetId)}
          onOpenSettings={() => setSettingsOpen(true)}
          onRenameConversation={(targetId) => setRenameTargetId(targetId)}
          onSelectConversation={(targetId) => navigate(`/conversations/${targetId}`)}
          onSidebarWidthChange={setSidebarWidth}
          sidebarWidth={sidebarWidth}
        />

        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[rgba(255,255,255,0.72)]">
          <ChatPanel
            activeRun={activeRun}
            draft={draft}
            error={
              streamError
                ? streamError
                : conversationQuery.error instanceof Error
                  ? conversationQuery.error.message
                  : runsQuery.error instanceof Error
                    ? runsQuery.error.message
                    : null
            }
            isSending={isStreaming}
            loadingHistory={conversationQuery.isLoading}
            loadingRuns={runsQuery.isLoading}
            messages={conversationQuery.data?.messages ?? []}
            onDraftChange={setDraft}
            onToggleSidebar={toggleSidebarCollapsed}
            onSend={async () => {
              if (!draft.trim() || isStreaming) {
                return;
              }

              const content = draft.trim();
              let targetConversationId: string;
              let createdConversationId: string | null = null;
              let runStarted = false;
              let terminalRunState: TerminalRunState = null;

              if (activeConversationId) {
                targetConversationId = activeConversationId;
              } else {
                const createdConversation = await createConversationMutation.mutateAsync(undefined);
                createdConversationId = createdConversation.conversation_id;
                targetConversationId = createdConversationId;
                await queryClient.invalidateQueries({ queryKey: ["conversations"] });
              }

              setDraft("");
              setStreamError(null);
              setStreamPhase("running");
              setActiveRun({
                localId: `local-run-${crypto.randomUUID()}`,
                runId: null,
                conversationId: targetConversationId,
                startedAt: new Date().toISOString(),
                userMessageId: null,
                userContent: content,
                status: "running",
                steps: [],
                finalMessageId: null,
                finalContent: "",
                finalTimestamp: null,
                error: null,
              });

              try {
                await streamMessage(targetConversationId, content, async (event) => {
                  if (event.event === "run_started") {
                    runStarted = true;
                  }
                  if (event.event === "assistant_finalized" || event.event === "run_completed") {
                    terminalRunState = "completed";
                  }
                  if (event.event === "run_failed") {
                    terminalRunState = "failed";
                  }
                  applyStreamEvent(event, content);
                });
              } catch (error) {
                const message = error instanceof Error ? error.message : "Streaming request failed.";
                if (terminalRunState === null) {
                  setStreamPhase("failed");
                  setStreamError(message);
                  setActiveRun((current) =>
                    current
                      ? {
                          ...current,
                          status: "failed",
                          error: message,
                        }
                      : current,
                  );
                }
              } finally {
                if (createdConversationId && !runStarted) {
                  try {
                    await deleteConversation(createdConversationId);
                    queryClient.removeQueries({ queryKey: ["conversation", createdConversationId] });
                    queryClient.removeQueries({ queryKey: ["conversation-runs", createdConversationId] });
                    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
                  } catch {
                    // Keep the original error state visible if cleanup fails.
                  }
                }

                await Promise.all([
                  queryClient.invalidateQueries({ queryKey: ["conversation", targetConversationId] }),
                  queryClient.invalidateQueries({ queryKey: ["conversation-runs", targetConversationId] }),
                  queryClient.invalidateQueries({ queryKey: ["conversations"] }),
                ]);

                setStreamPhase((current) => {
                  if (terminalRunState === "failed") {
                    return "failed";
                  }
                  if (terminalRunState === "completed") {
                    return "idle";
                  }
                  return current === "failed" ? "failed" : "idle";
                });
                setActiveRun((current) => {
                  if (!current) {
                    return null;
                  }
                  if (terminalRunState === "failed" || current.status === "failed") {
                    return current;
                  }
                  return null;
                });

                if (createdConversationId && runStarted) {
                  navigate(`/conversations/${createdConversationId}`);
                }
              }
            }}
            runs={runsQuery.data?.runs ?? []}
            sidebarCollapsed={sidebarCollapsed}
          />
        </section>
      </div>

      <SettingsDialog onOpenChange={setSettingsOpen} open={settingsOpen} />

      <RenameDialog
        initialName={renameConversationItem?.name ?? ""}
        onOpenChange={(open) => setRenameTargetId(open ? renameTargetId : null)}
        onSubmit={async (name) => {
          if (!renameTargetId) {
            return;
          }
          await renameConversationMutation.mutateAsync({ conversationId: renameTargetId, name });
        }}
        open={Boolean(renameTargetId)}
      />
    </main>
  );
}
