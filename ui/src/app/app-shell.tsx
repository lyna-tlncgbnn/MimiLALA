import { ChatPanel } from "@/features/chat/layout/chat-panel";
import { useConversationScreen } from "@/features/chat/hooks/use-conversation-screen";
import { RenameDialog } from "@/features/conversations/components/rename-dialog";
import { SidebarPanel } from "@/features/conversations/components/sidebar-panel";
import { SettingsDialog } from "@/features/settings/components/settings-dialog";

export function AppShell() {
  const screen = useConversationScreen();

  return (
    <main className="noise-overlay h-screen overflow-hidden text-[12px]">
      <div className="flex h-screen overflow-hidden border border-[rgba(32,33,35,0.08)] bg-[rgba(255,255,255,0.96)]">
        <SidebarPanel
          activeConversationId={screen.activeConversationId}
          collapsed={screen.sidebarCollapsed}
          conversations={screen.conversations}
          deletingConversationId={screen.deletingConversationId}
          loading={screen.loadingConversations}
          onCreateConversation={screen.handleStartNewConversation}
          onDeleteConversation={screen.handleDeleteConversation}
          onOpenSettings={screen.handleOpenSettings}
          onRenameConversation={screen.handleOpenRenameDialog}
          onSelectConversation={screen.handleOpenConversation}
          onSidebarWidthChange={screen.setSidebarWidth}
          sidebarWidth={screen.sidebarWidth}
        />

        <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[rgba(255,255,255,0.72)]">
          <ChatPanel
            activeRun={screen.activeRun}
            draft={screen.draft}
            error={screen.chatError}
            isSending={screen.isSending}
            loadingHistory={screen.loadingHistory}
            loadingRuns={screen.loadingRuns}
            messages={screen.conversationMessages}
            onDraftChange={screen.handleDraftChange}
            onSend={screen.handleSend}
            onToggleSidebar={screen.toggleSidebarCollapsed}
            runs={screen.runs}
            sidebarCollapsed={screen.sidebarCollapsed}
          />
        </section>
      </div>

      <SettingsDialog onOpenChange={screen.setSettingsOpen} open={screen.settingsOpen} />

      <RenameDialog
        initialName={screen.renameDialogInitialName}
        onOpenChange={screen.handleRenameDialogChange}
        onSubmit={screen.handleRenameSubmit}
        open={screen.renameDialogOpen}
      />
    </main>
  );
}
