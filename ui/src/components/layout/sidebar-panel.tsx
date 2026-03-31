import { useEffect, useRef, useState } from "react";
import { Plus, Settings2 } from "lucide-react";

import logoWordmark from "@/assets/logos/minilala-wordmark-wide-transparent.png";
import { Button } from "@/components/ui/button";
import { SidebarConversationList } from "@/components/layout/sidebar-conversation-list";
import { type SidebarConversationItem } from "@/components/layout/sidebar-conversation-row";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 320;

export function SidebarPanel({
  conversations,
  activeConversationId,
  collapsed,
  loading,
  deletingConversationId,
  onCreateConversation,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onOpenSettings,
  sidebarWidth,
  onSidebarWidthChange,
}: {
  conversations: SidebarConversationItem[];
  activeConversationId: string | null;
  collapsed: boolean;
  loading: boolean;
  deletingConversationId: string | null;
  sidebarWidth: number;
  onCreateConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onOpenSettings: () => void;
  onSidebarWidthChange: (width: number) => void;
}) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const isResizingRef = useRef(false);

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      if (target.closest("[data-sidebar-menu-root]")) {
        return;
      }

      setOpenMenuId(null);
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  useEffect(() => {
    setOpenMenuId(null);
  }, [activeConversationId, collapsed]);

  useEffect(() => {
    if (collapsed) {
      return undefined;
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (!isResizingRef.current) {
        return;
      }

      const nextWidth = Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, event.clientX));
      onSidebarWidthChange(nextWidth);
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";
    };

    const stopResizing = () => {
      if (!isResizingRef.current) {
        return;
      }

      isResizingRef.current = false;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    window.addEventListener("pointercancel", stopResizing);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      window.removeEventListener("pointercancel", stopResizing);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [collapsed, onSidebarWidthChange]);

  return (
    <aside
      className={cn(
        "relative hidden min-h-0 shrink-0 bg-[rgba(247,247,248,0.96)] transition-[width,padding,border] duration-200 lg:flex lg:flex-col lg:overflow-hidden",
        collapsed ? "w-0 border-r-0 px-0 py-0" : "h-full border-r border-[rgba(32,33,35,0.08)] px-2.5 py-3",
      )}
      style={{ width: collapsed ? 0 : sidebarWidth }}
    >
      {!collapsed ? (
        <>
          <div className="flex h-9 shrink-0 items-center">
            <img alt="MiniLALA" className="h-4.5 w-auto object-contain object-left" draggable={false} src={logoWordmark} />
          </div>

          <Button
            className="mt-2 h-9 w-full justify-center gap-2 rounded-[11px] border border-border bg-[rgba(255,255,255,0.96)] px-3 text-[12px] text-foreground hover:bg-panel-strong hover:brightness-100"
            onClick={onCreateConversation}
            variant="secondary"
          >
            <Plus className="h-3.5 w-3.5" />
            新建会话
          </Button>

          <ScrollArea className="mt-2 min-h-0 flex-1">
            {loading ? (
              <div className="rounded-[12px] bg-[rgba(255,255,255,0.72)] px-3 py-3 text-[12px] text-muted-foreground">
                正在加载会话列表...
              </div>
            ) : (
              <SidebarConversationList
                activeConversationId={activeConversationId}
                conversations={conversations}
                deletingConversationId={deletingConversationId}
                onCloseMenu={() => setOpenMenuId(null)}
                onDeleteConversation={onDeleteConversation}
                onRenameConversation={onRenameConversation}
                onSelectConversation={onSelectConversation}
                onToggleMenu={(conversationId) =>
                  setOpenMenuId((current) => (current === conversationId ? null : conversationId))
                }
                openMenuId={openMenuId}
              />
            )}
          </ScrollArea>

          <button
            className="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 rounded-[11px] border border-border bg-panel-strong px-3 text-[12px] text-muted-foreground transition hover:bg-panel-muted hover:text-foreground"
            onClick={onOpenSettings}
            type="button"
          >
            <Settings2 className="h-4 w-4" />
            设置
          </button>

          <div
            aria-hidden="true"
            className="group/resize absolute inset-y-0 right-0 w-2 translate-x-1/2 cursor-col-resize"
            onPointerDown={(event) => {
              event.preventDefault();
              isResizingRef.current = true;
            }}
          >
            <div className="mx-auto h-full w-px bg-transparent transition group-hover/resize:bg-[rgba(32,33,35,0.08)]" />
          </div>
        </>
      ) : null}
    </aside>
  );
}
