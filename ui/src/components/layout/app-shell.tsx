import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import { useNavigate, useParams } from "react-router-dom";

import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  renameConversation,
  sendMessage,
} from "@/lib/api";
import { ChatPanel } from "@/components/layout/chat-panel";
import { RenameDialog } from "@/components/layout/rename-dialog";
import { SettingsDialog } from "@/components/layout/settings-dialog";
import { SidebarPanel } from "@/components/layout/sidebar-panel";
import { useUiStore } from "@/stores/ui-store";

function formatRelativeTime(value: string) {
  try {
    return formatDistanceToNow(new Date(value), { addSuffix: true, locale: zhCN });
  } catch {
    return value;
  }
}

export function AppShell() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sidebarCollapsed = useUiStore((state) => state.sidebarCollapsed);
  const settingsOpen = useUiStore((state) => state.settingsOpen);
  const renameTargetId = useUiStore((state) => state.renameTargetId);
  const toggleSidebarCollapsed = useUiStore((state) => state.toggleSidebarCollapsed);
  const setSettingsOpen = useUiStore((state) => state.setSettingsOpen);
  const setRenameTargetId = useUiStore((state) => state.setRenameTargetId);
  const [draft, setDraft] = useState("");

  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    refetchInterval: 5000,
  });

  const conversations = conversationsQuery.data ?? [];
  const activeConversationId = useMemo(() => {
    if (conversationId) {
      return conversationId;
    }
    return conversations[0]?.conversation_id ?? null;
  }, [conversationId, conversations]);

  useEffect(() => {
    if (!conversationId && conversations[0]?.conversation_id) {
      navigate(`/conversations/${conversations[0].conversation_id}`, { replace: true });
    }
  }, [conversationId, conversations, navigate]);

  const conversationQuery = useQuery({
    queryKey: ["conversation", activeConversationId],
    queryFn: () => getConversation(activeConversationId!),
    enabled: Boolean(activeConversationId),
  });

  const createConversationMutation = useMutation({
    mutationFn: (name?: string) => createConversation(name),
    onSuccess: async (conversation) => {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      navigate(`/conversations/${conversation.conversation_id}`);
    },
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

  const sendMessageMutation = useMutation({
    mutationFn: ({ conversationId: targetId, content }: { conversationId: string; content: string }) =>
      sendMessage(targetId, content),
    onSuccess: (result) => {
      queryClient.setQueryData(["conversation", result.conversation.conversation_id], {
        conversation: result.conversation,
        messages: result.messages,
      });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setDraft("");
    },
  });

  const renameConversationItem = conversations.find(
    (conversation) => conversation.conversation_id === renameTargetId,
  );

  const sidebarConversations = conversations.map((conversation) => ({
    id: conversation.conversation_id,
    title: conversation.name,
    time: formatRelativeTime(conversation.updated_at),
  }));

  return (
    <main className="noise-overlay h-screen overflow-hidden text-[12px]">
      <div className="flex h-screen overflow-hidden border border-[rgba(53,40,17,0.08)] bg-[rgba(252,251,247,0.96)]">
        <SidebarPanel
          activeConversationId={activeConversationId}
          collapsed={sidebarCollapsed}
          conversations={sidebarConversations}
          deletingConversationId={deleteConversationMutation.isPending ? deleteConversationMutation.variables ?? null : null}
          loading={conversationsQuery.isLoading}
          onCreateConversation={() => createConversationMutation.mutate(undefined)}
          onDeleteConversation={(targetId) => deleteConversationMutation.mutate(targetId)}
          onOpenSettings={() => setSettingsOpen(true)}
          onRenameConversation={(targetId) => setRenameTargetId(targetId)}
          onSelectConversation={(targetId) => navigate(`/conversations/${targetId}`)}
          onToggleCollapse={toggleSidebarCollapsed}
        />

        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[rgba(255,255,255,0.42)]">
          <header className="flex items-center justify-between border-b border-[rgba(53,40,17,0.08)] px-4 py-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                Desktop Foundation
              </div>
              <div className="mt-1 text-[18px] font-semibold text-foreground">
                {conversationQuery.data?.conversation.name ?? "AgentBot"}
              </div>
            </div>
            <div className="rounded-[12px] border border-border bg-[rgba(255,255,255,0.75)] px-3 py-2 text-[12px] text-muted-foreground">
              FastAPI + Electron + React
            </div>
          </header>

          <ChatPanel
            draft={draft}
            error={
              sendMessageMutation.error instanceof Error
                ? sendMessageMutation.error.message
                : conversationQuery.error instanceof Error
                  ? conversationQuery.error.message
                  : null
            }
            isSending={sendMessageMutation.isPending}
            loadingHistory={conversationQuery.isLoading}
            messages={conversationQuery.data?.messages ?? []}
            onDraftChange={setDraft}
            onSend={async () => {
              if (!activeConversationId || !draft.trim() || sendMessageMutation.isPending) {
                return;
              }
              await sendMessageMutation.mutateAsync({
                conversationId: activeConversationId,
                content: draft.trim(),
              });
            }}
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
