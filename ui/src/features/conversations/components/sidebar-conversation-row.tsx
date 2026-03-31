import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { cn } from "@/shared/lib/utils";

export type SidebarConversationItem = {
  id: string;
  title: string;
};

export function SidebarConversationRow({
  conversation,
  active,
  deleting,
  menuOpen,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onToggleMenu,
  onCloseMenu,
}: {
  conversation: SidebarConversationItem;
  active: boolean;
  deleting: boolean;
  menuOpen: boolean;
  onSelectConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onToggleMenu: (conversationId: string) => void;
  onCloseMenu: () => void;
}) {
  return (
    <div className="group relative py-0.5" data-sidebar-menu-root>
      <div
        className={cn(
          "grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-1 rounded-[10px] px-2.5 py-1.5 transition",
          active ? "bg-[rgba(32,33,35,0.06)]" : "hover:bg-[rgba(32,33,35,0.045)]",
        )}
      >
        <button
          className="min-w-0 overflow-hidden text-left"
          onClick={() => {
            onCloseMenu();
            onSelectConversation(conversation.id);
          }}
          type="button"
        >
          <div className="truncate text-[13px] font-medium leading-5 text-foreground">
            {conversation.title}
          </div>
        </button>

        <div className="relative flex shrink-0 items-center">
          <button
            aria-expanded={menuOpen}
            aria-haspopup="menu"
            className={cn(
              "inline-flex h-6 w-6 items-center justify-center rounded-[8px] text-muted-foreground transition",
              menuOpen
                ? "bg-[rgba(32,33,35,0.08)] text-foreground"
                : "opacity-0 hover:bg-[rgba(32,33,35,0.08)] hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100",
              active && !menuOpen ? "opacity-100" : "",
            )}
            onClick={(event) => {
              event.stopPropagation();
              onToggleMenu(conversation.id);
            }}
            title="更多操作"
            type="button"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>

          {menuOpen ? (
            <div
              className="absolute right-0 top-8 z-20 w-40 rounded-[16px] border border-border bg-[rgba(255,255,255,0.98)] p-1.5 shadow-[0_16px_40px_rgba(32,33,35,0.14)]"
              role="menu"
            >
              <button
                className="flex w-full items-center gap-2 rounded-[10px] px-3 py-2 text-[13px] text-foreground transition hover:bg-panel-strong"
                onClick={(event) => {
                  event.stopPropagation();
                  onCloseMenu();
                  onRenameConversation(conversation.id);
                }}
                role="menuitem"
                type="button"
              >
                <Pencil className="h-3.5 w-3.5" />
                重命名
              </button>
              <button
                className="mt-1 flex w-full items-center gap-2 rounded-[10px] px-3 py-2 text-[13px] text-[rgba(185,28,28,0.92)] transition hover:bg-[rgba(185,28,28,0.08)] disabled:opacity-50"
                disabled={deleting}
                onClick={(event) => {
                  event.stopPropagation();
                  onCloseMenu();
                  onDeleteConversation(conversation.id);
                }}
                role="menuitem"
                type="button"
              >
                <Trash2 className="h-3.5 w-3.5" />
                删除
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
