import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { getConversation, listConversationRuns, streamMessage } from "@/features/chat/api/chat-api";
import { chatQueryKeys } from "@/features/chat/api/chat-query-keys";
import {
  applyStreamEventToActiveRun,
  createPendingActiveRun,
  type StreamPhase,
  type TerminalRunState,
} from "@/features/chat/lib/active-run-state";
import type { ActiveRunState } from "@/features/chat/types";
import {
  createConversation,
  deleteConversation,
  listConversations,
  renameConversation,
} from "@/features/conversations/api/conversations-api";
import { conversationsQueryKeys } from "@/features/conversations/api/conversations-query-keys";
import { useUiStore } from "@/state/ui-store";

const SIDEBAR_COLLAPSE_MEDIA_QUERY = "(max-width: 1220px)";
const CONVERSATIONS_REFETCH_INTERVAL_MS = 5000;

export function useConversationScreen() {
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

  const activeConversationId = conversationId ?? null;

  useEffect(() => {
    const mediaQuery = window.matchMedia(SIDEBAR_COLLAPSE_MEDIA_QUERY);

    const syncSidebarState = () => {
      setSidebarCollapsed(mediaQuery.matches);
    };

    syncSidebarState();
    mediaQuery.addEventListener("change", syncSidebarState);
    return () => mediaQuery.removeEventListener("change", syncSidebarState);
  }, [setSidebarCollapsed]);

  useEffect(() => {
    setActiveRun(null);
    setStreamError(null);
    setStreamPhase("idle");
  }, [activeConversationId]);

  const conversationsQuery = useQuery({
    queryKey: conversationsQueryKeys.all,
    queryFn: listConversations,
    refetchInterval: CONVERSATIONS_REFETCH_INTERVAL_MS,
  });

  const conversationQuery = useQuery({
    queryKey: chatQueryKeys.conversation(activeConversationId),
    queryFn: () => getConversation(activeConversationId!),
    enabled: Boolean(activeConversationId),
  });

  const runsQuery = useQuery({
    queryKey: chatQueryKeys.conversationRuns(activeConversationId),
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
        queryClient.invalidateQueries({ queryKey: conversationsQueryKeys.all }),
        queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversation(variables.conversationId) }),
      ]);
    },
  });

  const deleteConversationMutation = useMutation({
    mutationFn: deleteConversation,
    onSuccess: async (_, deletedConversationId) => {
      queryClient.removeQueries({ queryKey: chatQueryKeys.conversation(deletedConversationId) });
      queryClient.removeQueries({ queryKey: chatQueryKeys.conversationRuns(deletedConversationId) });
      await queryClient.invalidateQueries({ queryKey: conversationsQueryKeys.all });

      const nextConversations = await listConversations();
      queryClient.setQueryData(conversationsQueryKeys.all, nextConversations);

      if (activeConversationId === deletedConversationId) {
        const nextConversationId = nextConversations[0]?.conversation_id;
        navigate(nextConversationId ? `/conversations/${nextConversationId}` : "/", { replace: true });
      }
    },
  });

  const conversations = conversationsQuery.data ?? [];
  const renameConversationItem = conversations.find(
    (conversation) => conversation.conversation_id === renameTargetId,
  );

  const sidebarConversations = useMemo(
    () =>
      conversations.map((conversation) => ({
        id: conversation.conversation_id,
        title: conversation.name,
      })),
    [conversations],
  );

  const isStreaming = streamPhase === "running";

  const handleStartNewConversation = () => {
    setDraft("");
    setActiveRun(null);
    setStreamError(null);
    setStreamPhase("idle");
    navigate("/");
  };

  const handleSend = async () => {
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
      await queryClient.invalidateQueries({ queryKey: conversationsQueryKeys.all });
    }

    setDraft("");
    setStreamError(null);
    setStreamPhase("running");
    setActiveRun(createPendingActiveRun({ conversationId: targetConversationId, content }));

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

        setActiveRun((current) => {
          const { nextActiveRun, nextError, nextPhase } = applyStreamEventToActiveRun({
            current,
            event,
            fallbackUserContent: content,
            activeConversationId,
          });

          if (nextPhase) {
            setStreamPhase(nextPhase);
          }
          if (nextError !== undefined) {
            setStreamError(nextError);
          }

          return nextActiveRun;
        });
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
          queryClient.removeQueries({ queryKey: chatQueryKeys.conversation(createdConversationId) });
          queryClient.removeQueries({ queryKey: chatQueryKeys.conversationRuns(createdConversationId) });
          await queryClient.invalidateQueries({ queryKey: conversationsQueryKeys.all });
        } catch {
          // Keep the original error state visible if cleanup fails.
        }
      }

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversation(targetConversationId) }),
        queryClient.invalidateQueries({ queryKey: chatQueryKeys.conversationRuns(targetConversationId) }),
        queryClient.invalidateQueries({ queryKey: conversationsQueryKeys.all }),
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
  };

  const chatError = useMemo(() => {
    if (streamError) {
      return streamError;
    }
    if (conversationQuery.error instanceof Error) {
      return conversationQuery.error.message;
    }
    if (runsQuery.error instanceof Error) {
      return runsQuery.error.message;
    }
    return null;
  }, [conversationQuery.error, runsQuery.error, streamError]);

  return {
    activeConversationId,
    activeRun,
    chatError,
    conversationMessages: conversationQuery.data?.messages ?? [],
    conversations: sidebarConversations,
    deletingConversationId: deleteConversationMutation.isPending ? deleteConversationMutation.variables ?? null : null,
    draft,
    handleDeleteConversation: (targetId: string) => deleteConversationMutation.mutate(targetId),
    handleDraftChange: setDraft,
    handleOpenConversation: (targetId: string) => navigate(`/conversations/${targetId}`),
    handleOpenRenameDialog: (targetId: string) => setRenameTargetId(targetId),
    handleOpenSettings: () => setSettingsOpen(true),
    handleRenameDialogChange: (open: boolean) => setRenameTargetId(open ? renameTargetId : null),
    handleRenameSubmit: async (name: string) => {
      if (!renameTargetId) {
        return;
      }
      await renameConversationMutation.mutateAsync({ conversationId: renameTargetId, name });
    },
    handleSend,
    handleStartNewConversation,
    isSending: isStreaming,
    loadingConversations: conversationsQuery.isLoading,
    loadingHistory: conversationQuery.isLoading,
    loadingRuns: runsQuery.isLoading,
    renameDialogInitialName: renameConversationItem?.name ?? "",
    renameDialogOpen: Boolean(renameTargetId),
    runs: runsQuery.data?.runs ?? [],
    settingsOpen,
    setSettingsOpen,
    sidebarCollapsed,
    sidebarWidth,
    toggleSidebarCollapsed,
    setSidebarWidth,
  };
}
