import {
  SidebarConversationRow,
  type SidebarConversationItem,
} from "@/components/layout/sidebar-conversation-row";

export function SidebarConversationList({
  conversations,
  activeConversationId,
  deletingConversationId,
  openMenuId,
  onCloseMenu,
  onDeleteConversation,
  onRenameConversation,
  onSelectConversation,
  onToggleMenu,
}: {
  conversations: SidebarConversationItem[];
  activeConversationId: string | null;
  deletingConversationId: string | null;
  openMenuId: string | null;
  onCloseMenu: () => void;
  onDeleteConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onToggleMenu: (conversationId: string) => void;
}) {
  return (
    <div className="space-y-0">
      {conversations.map((conversation) => (
        <SidebarConversationRow
          key={conversation.id}
          active={conversation.id === activeConversationId}
          conversation={conversation}
          deleting={deletingConversationId === conversation.id}
          menuOpen={openMenuId === conversation.id}
          onCloseMenu={onCloseMenu}
          onDeleteConversation={onDeleteConversation}
          onRenameConversation={onRenameConversation}
          onSelectConversation={onSelectConversation}
          onToggleMenu={onToggleMenu}
        />
      ))}
    </div>
  );
}
