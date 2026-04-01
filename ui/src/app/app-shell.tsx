import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import {
  type ChatMessage,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  renameConversation,
  streamMessage,
} from "@/shared/api/api";
import { ChatPanel } from "@/features/chat/layout/chat-panel";
import { RenameDialog } from "@/features/conversations/components/rename-dialog";
import { SettingsDialog } from "@/features/settings/components/settings-dialog";
import { SidebarPanel } from "@/features/conversations/components/sidebar-panel";
import { useUiStore } from "@/state/ui-store";

type StreamPhase =
  | "idle"
  | "waiting_assistant"
  | "assistant_streaming"
  | "tool_running"
  | "completed"
  | "failed";

function createClientMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    message_id: `msg_${crypto.randomUUID()}`,
    timestamp: new Date().toISOString(),
    role,
    content,
    name: null,
    tool_call_id: null,
    tool_calls: null,
    response: role === "assistant" ? { text: content } : null,
    delegation: null,
    browser_task: null,
    state: role === "assistant" ? { kind: "final" } : null,
    metadata: null,
  };
}

function createEmptyAssistantMessage(messageId: string, timestamp: string): ChatMessage {
  return {
    message_id: messageId,
    timestamp,
    role: "assistant",
    content: "",
    name: null,
    tool_call_id: null,
    tool_calls: null,
    response: null,
    delegation: null,
    browser_task: null,
    state: { kind: "planning" },
    metadata: null,
  };
}

function formatToolPendingContent(toolName: string, args: Record<string, unknown>) {
  const entries = Object.entries(args ?? {});
  const argsSummary = entries.map(([key, value]) => `${key}=${formatToolValue(value)}`).join(", ");
  return argsSummary ? `Running ${toolName}\n${argsSummary}` : `Running ${toolName}`;
}

function formatToolValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value === null || value === undefined) {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function updateAssistantMessage(
  messages: ChatMessage[],
  assistantMessageId: string | null | undefined,
  updater: (message: ChatMessage) => ChatMessage,
) {
  if (!assistantMessageId) {
    return messages;
  }
  return messages.map((message) =>
    message.role === "assistant" && message.message_id === assistantMessageId ? updater(message) : message,
  );
}

function buildBrowserStatusText(browserTask: ChatMessage["browser_task"]): string {
  if (!browserTask) {
    return "";
  }

  const lines = [
    browserTask.task ? `正在使用浏览器执行任务: ${browserTask.task}` : "正在使用浏览器执行任务...",
    browserTask.page_title ? `当前页面: ${browserTask.page_title}` : null,
    browserTask.current_url ? `URL: ${browserTask.current_url}` : null,
  ];

  const lastStep = browserTask.steps?.[browserTask.steps.length - 1];
  if (lastStep) {
    const actionType = String(lastStep.action?.action_type ?? "unknown");
    lines.push(`最近步骤 ${lastStep.step_number}: ${actionType}`);
    const extractedContent =
      typeof lastStep.result?.extracted_content === "string" ? lastStep.result.extracted_content : null;
    const errorMessage = typeof lastStep.result?.error === "string" ? lastStep.result.error : null;
    if (errorMessage) {
      lines.push(`结果: ${errorMessage}`);
    } else if (extractedContent) {
      lines.push(`结果: ${extractedContent}`);
    }
  }

  if (browserTask.status === "completed" && browserTask.final_response) {
    lines.push("");
    lines.push(browserTask.final_response);
  }

  if (browserTask.status === "failed" && browserTask.error_message) {
    lines.push("");
    lines.push(`失败原因: ${browserTask.error_message}`);
  }

  return lines.filter(Boolean).join("\n");
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
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);
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
    setLiveMessages([]);
    setStreamError(null);
    setStreamPhase("idle");
  }, [activeConversationId]);

  const conversationQuery = useQuery({
    queryKey: ["conversation", activeConversationId],
    queryFn: () => getConversation(activeConversationId!),
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

  const displayedMessages = useMemo(
    () => [...(conversationQuery.data?.messages ?? []), ...liveMessages],
    [conversationQuery.data?.messages, liveMessages],
  );

  const sidebarConversations = conversations.map((conversation) => ({
    id: conversation.conversation_id,
    title: conversation.name,
  }));

  const isStreaming =
    streamPhase === "waiting_assistant" ||
    streamPhase === "assistant_streaming" ||
    streamPhase === "tool_running";

  const handleStartNewConversation = () => {
    setDraft("");
    setLiveMessages([]);
    setStreamError(null);
    setStreamPhase("idle");
    navigate("/");
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
            draft={draft}
            error={
              streamError
                ? streamError
                : conversationQuery.error instanceof Error
                  ? conversationQuery.error.message
                  : null
            }
            isSending={isStreaming}
            loadingHistory={conversationQuery.isLoading}
            messages={displayedMessages}
            onDraftChange={setDraft}
            onToggleSidebar={toggleSidebarCollapsed}
            onSend={async () => {
              if (!draft.trim() || isStreaming) {
                return;
              }

              const content = draft.trim();
              let targetConversationId: string;
              let createdConversationId: string | null = null;
              let userMessageAccepted = false;

              if (activeConversationId) {
                targetConversationId = activeConversationId;
              } else {
                const createdConversation = await createConversationMutation.mutateAsync(undefined);
                createdConversationId = createdConversation.conversation_id;
                targetConversationId = createdConversationId;
                await queryClient.invalidateQueries({ queryKey: ["conversations"] });
              }

              const optimisticUser = createClientMessage("user", content);
              const waitingAssistant = createClientMessage("assistant", "Waiting for reply...");
              let activeAssistantMessageId = waitingAssistant.message_id;

              setDraft("");
              setStreamError(null);
              setStreamPhase("waiting_assistant");
              setLiveMessages([optimisticUser, waitingAssistant]);

              try {
                await streamMessage(targetConversationId, content, async (event) => {
                  if (event.event === "user_message_accepted") {
                    userMessageAccepted = true;
                    setLiveMessages((current) =>
                      current.map((message) =>
                        message.message_id === optimisticUser.message_id
                          ? {
                              ...message,
                              message_id: event.data.message_id,
                              timestamp: event.data.timestamp,
                              content: event.data.content,
                            }
                          : message,
                      ),
                    );
                    return;
                  }

                  if (event.event === "assistant_waiting") {
                    setStreamPhase("waiting_assistant");
                    setLiveMessages((current) =>
                      current.map((message) =>
                        message.message_id === activeAssistantMessageId
                          ? { ...message, timestamp: event.data.timestamp }
                          : message,
                      ),
                    );
                    return;
                  }

                  if (event.event === "assistant_message_started") {
                    setStreamPhase("assistant_streaming");
                    activeAssistantMessageId = event.data.message_id;
                    setLiveMessages((current) => {
                      const existingIndex = current.findIndex(
                        (message) => message.role === "assistant" && message.message_id === waitingAssistant.message_id,
                      );

                      if (existingIndex >= 0) {
                        return current.map((message, index) =>
                          index === existingIndex
                            ? {
                                ...message,
                                message_id: event.data.message_id,
                                timestamp: event.data.timestamp,
                                content: "",
                                response: null,
                                delegation: null,
                                browser_task: null,
                                state: { kind: "planning" },
                              }
                            : message,
                        );
                      }

                      return [...current, createEmptyAssistantMessage(event.data.message_id, event.data.timestamp)];
                    });
                    return;
                  }

                  if (event.event === "supervisor_decision_made") {
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => ({
                        ...message,
                        delegation: {
                          target: event.data.decision === "browser" ? "browser" : event.data.decision,
                          status:
                            event.data.decision === "browser"
                              ? "planned"
                              : event.data.decision === "tools"
                                ? "planned"
                                : "completed",
                          reason: event.data.reason,
                          task: event.data.browser_task ?? undefined,
                        },
                        state: {
                          kind:
                            event.data.decision === "browser"
                              ? "delegating"
                              : event.data.decision === "tools"
                                ? "tooling"
                                : "final",
                        },
                      })),
                    );
                    return;
                  }

                  if (event.event === "assistant_delta") {
                    setStreamPhase("assistant_streaming");
                    setLiveMessages((current) =>
                      current.map((message) =>
                        message.role === "assistant" && message.message_id === activeAssistantMessageId
                          ? {
                              ...message,
                              content: `${message.content}${event.data.delta}`,
                              response: { text: `${message.content}${event.data.delta}` },
                              state: { kind: "final" },
                            }
                          : message,
                      ),
                    );
                    return;
                  }

                  if (event.event === "tool_started") {
                    setStreamPhase("tool_running");
                    setLiveMessages((current) => {
                      const nextMessages = current.filter(
                        (message) =>
                          !(
                            message.role === "assistant" &&
                            message.message_id === activeAssistantMessageId &&
                            message.content.trim() === "Waiting for reply..."
                          ),
                      );

                      return [
                        ...nextMessages,
                        {
                          message_id: `tool_${event.data.tool_call_id}`,
                          timestamp: event.data.timestamp,
                          role: "tool",
                          content: formatToolPendingContent(event.data.tool_name, event.data.args),
                          name: event.data.tool_name,
                          tool_call_id: event.data.tool_call_id,
                          tool_calls: null,
                        },
                      ];
                    });
                    return;
                  }

                  if (event.event === "tool_finished") {
                    setStreamPhase("assistant_streaming");
                    setLiveMessages((current) =>
                      current.map((message) =>
                        message.role === "tool" && message.tool_call_id === event.data.tool_call_id
                          ? {
                              ...message,
                              timestamp: event.data.timestamp,
                              name: event.data.tool_name,
                              content: event.data.tool_output,
                            }
                          : message,
                      ),
                    );
                    return;
                  }

                  if (event.event === "assistant_completed") {
                    setStreamPhase("completed");
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => ({
                        ...message,
                        timestamp: event.data.timestamp,
                        content: event.data.content,
                        response: { text: event.data.content },
                        state: { kind: "final" },
                      })),
                    );
                    return;
                  }

                  if (event.event === "browser_subgraph_started") {
                    setStreamPhase("assistant_streaming");
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => {
                        const browserTask = {
                          task: event.data.task,
                          status: "running",
                          final_response: null,
                          error_message: null,
                          current_url: null,
                          page_title: null,
                          step_count: 0,
                          steps: [],
                        };
                        return {
                          ...message,
                          delegation: {
                            target: "browser",
                            status: "running",
                            reason: message.delegation?.reason,
                            task: event.data.task,
                          },
                          browser_task: browserTask,
                          state: { kind: "delegating" },
                        };
                      }),
                    );
                    return;
                  }

                  if (event.event === "browser_observed") {
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => {
                        const browserTask = {
                          task: message.browser_task?.task,
                          status: message.browser_task?.status ?? "running",
                          final_response: message.browser_task?.final_response ?? null,
                          error_message: message.browser_task?.error_message ?? null,
                          current_url: event.data.current_url ?? message.browser_task?.current_url ?? null,
                          page_title: event.data.page_title ?? message.browser_task?.page_title ?? null,
                          step_count: message.browser_task?.step_count ?? 0,
                          steps: message.browser_task?.steps ?? [],
                        };
                        return {
                          ...message,
                          browser_task: browserTask,
                          state: { kind: "delegating" },
                        };
                      }),
                    );
                    return;
                  }

                  if (event.event === "browser_action_planned") {
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => {
                        const existingSteps = message.browser_task?.steps ?? [];
                        const stepNumber =
                          typeof event.data.step_number === "number"
                            ? event.data.step_number
                            : existingSteps.length + 1;
                        const nextSteps = [
                          ...existingSteps.filter((step) => step.step_number !== stepNumber),
                          {
                            step_number: stepNumber,
                            action: event.data.action ?? {},
                            result: null,
                          },
                        ].sort((a, b) => a.step_number - b.step_number);
                        const browserTask = {
                          task: message.browser_task?.task,
                          status: "running",
                          final_response: message.browser_task?.final_response ?? null,
                          error_message: message.browser_task?.error_message ?? null,
                          current_url: message.browser_task?.current_url ?? null,
                          page_title: message.browser_task?.page_title ?? null,
                          step_count: nextSteps.length,
                          steps: nextSteps,
                        };
                        return {
                          ...message,
                          browser_task: browserTask,
                          state: { kind: "delegating" },
                        };
                      }),
                    );
                    return;
                  }

                  if (event.event === "browser_action_started") {
                    setStreamPhase("assistant_streaming");
                    return;
                  }

                  if (event.event === "browser_action_finished") {
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => {
                        const existingSteps = message.browser_task?.steps ?? [];
                        const stepNumber =
                          typeof event.data.step_number === "number"
                            ? event.data.step_number
                            : existingSteps.length;
                        const nextSteps = existingSteps.map((step) =>
                          step.step_number === stepNumber
                            ? {
                                ...step,
                                result: event.data.result ?? null,
                              }
                            : step,
                        );
                        const browserTask = {
                          task: message.browser_task?.task,
                          status: event.data.status ?? message.browser_task?.status ?? "running",
                          final_response: message.browser_task?.final_response ?? null,
                          error_message:
                            typeof event.data.result?.error === "string"
                              ? event.data.result.error
                              : message.browser_task?.error_message ?? null,
                          current_url: message.browser_task?.current_url ?? null,
                          page_title: message.browser_task?.page_title ?? null,
                          step_count: nextSteps.length,
                          steps: nextSteps,
                        };
                        return {
                          ...message,
                          browser_task: browserTask,
                          state: { kind: "delegating" },
                        };
                      }),
                    );
                    return;
                  }

                  if (event.event === "browser_subgraph_completed" || event.event === "browser_subgraph_failed") {
                    setStreamPhase("assistant_streaming");
                    setLiveMessages((current) =>
                      updateAssistantMessage(current, activeAssistantMessageId ?? waitingAssistant.message_id, (message) => {
                        const browserTask = {
                          task: message.browser_task?.task,
                          status: event.data.status,
                          final_response: event.data.final_response ?? null,
                          error_message: event.data.error_message ?? null,
                          current_url: event.data.current_url ?? message.browser_task?.current_url ?? null,
                          page_title: event.data.page_title ?? message.browser_task?.page_title ?? null,
                          step_count: event.data.step_count ?? message.browser_task?.step_count ?? 0,
                          steps: message.browser_task?.steps ?? [],
                        };
                        return {
                          ...message,
                          delegation: {
                            target: "browser",
                            status: event.data.status,
                            reason: message.delegation?.reason,
                            task: browserTask.task,
                          },
                          browser_task: browserTask,
                          state: { kind: "delegating" },
                        };
                      }),
                    );
                    return;
                  }

                  if (event.event === "error") {
                    setStreamPhase("failed");
                    setStreamError(event.data.message);
                  }
                });
              } catch (error) {
                setStreamPhase("failed");
                setStreamError(error instanceof Error ? error.message : "Streaming request failed.");
              } finally {
                if (createdConversationId && !userMessageAccepted) {
                  try {
                    await deleteConversation(createdConversationId);
                    queryClient.removeQueries({ queryKey: ["conversation", createdConversationId] });
                    await queryClient.invalidateQueries({ queryKey: ["conversations"] });
                  } catch {
                    // Keep the original error state visible if cleanup fails.
                  }
                }

                await Promise.all([
                  queryClient.invalidateQueries({ queryKey: ["conversation", targetConversationId] }),
                  queryClient.invalidateQueries({ queryKey: ["conversations"] }),
                ]);
                setLiveMessages([]);
                setStreamPhase((current) => (current === "failed" ? "failed" : "idle"));

                if (createdConversationId && userMessageAccepted) {
                  navigate(`/conversations/${createdConversationId}`);
                }
              }
            }}
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

