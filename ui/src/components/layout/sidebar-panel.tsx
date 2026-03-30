import { Bot, ChevronLeft, ChevronRight, Pencil, Plus, Settings2, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

export type SidebarConversationItem = {
  id: string;
  title: string;
  time: string;
};

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
  onToggleCollapse,
}: {
  conversations: SidebarConversationItem[];
  activeConversationId: string | null;
  collapsed: boolean;
  loading: boolean;
  deletingConversationId: string | null;
  onCreateConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onOpenSettings: () => void;
  onToggleCollapse: () => void;
}) {
  return (
    <aside
      className={cn(
        "hidden h-full min-h-0 shrink-0 border-r border-[rgba(53,40,17,0.08)] bg-[rgba(250,248,243,0.78)] px-3 py-3 lg:flex lg:flex-col lg:overflow-hidden",
        collapsed ? "w-[78px]" : "w-[280px]",
      )}
    >
      <div className={cn("flex shrink-0 items-center border-b border-border pb-2", collapsed ? "justify-center" : "justify-between")}>
        {!collapsed ? (
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            AgentBot
          </div>
        ) : null}
        <button
          className="inline-flex h-7.5 w-7.5 items-center justify-center rounded-[12px] border border-border bg-panel-strong text-muted-foreground transition hover:bg-panel-muted hover:text-accent"
          onClick={onToggleCollapse}
          title={collapsed ? "展开侧栏" : "收起侧栏"}
          type="button"
        >
          {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>

      {collapsed ? (
        <>
          <Button
            className="mt-2 h-10 w-full rounded-[11px] border border-dashed border-[rgba(180,106,44,0.22)] bg-[rgba(255,255,255,0.9)] px-0 text-accent hover:bg-[rgba(180,106,44,0.04)] hover:brightness-100"
            onClick={onCreateConversation}
            variant="secondary"
          >
            <Plus className="h-4 w-4" />
          </Button>

          <ScrollArea className="mt-2 min-h-0 flex-1">
            {loading ? (
              <div className="flex justify-center px-1 py-2 text-[11px] text-muted-foreground">...</div>
            ) : (
              <div className="space-y-1.5">
                {conversations.map((conversation) => {
                  const active = conversation.id === activeConversationId;
                  return (
                    <div key={conversation.id} className="flex justify-center">
                      <button
                        className={cn(
                          "relative inline-flex h-11 w-11 items-center justify-center rounded-[14px] transition",
                          active
                            ? "bg-[rgba(180,106,44,0.05)] text-accent"
                            : "bg-transparent text-muted-foreground hover:bg-[rgba(180,106,44,0.10)] hover:text-accent",
                        )}
                        onClick={() => onSelectConversation(conversation.id)}
                        title={`${conversation.title}\n${conversation.time}`}
                        type="button"
                      >
                        <Bot className="h-4 w-4" />
                        {active ? (
                          <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-accent" />
                        ) : null}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>

          <button
            className="mt-2 inline-flex h-10 w-full items-center justify-center rounded-[11px] border border-border bg-panel-strong text-muted-foreground transition hover:bg-panel-muted hover:text-accent"
            onClick={onOpenSettings}
            type="button"
          >
            <Settings2 className="h-4 w-4" />
          </button>
        </>
      ) : (
        <>
          <Button
            className="mt-2 h-10 w-full justify-center gap-2 rounded-[11px] border border-dashed border-[rgba(180,106,44,0.22)] bg-[rgba(255,255,255,0.9)] px-3 text-[13px] text-accent hover:bg-[rgba(180,106,44,0.04)] hover:brightness-100"
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
              <div className="divide-y divide-[rgba(53,40,17,0.08)]">
                {conversations.map((conversation) => {
                  const active = conversation.id === activeConversationId;
                  return (
                    <div key={conversation.id} className="group relative py-1.5">
                      <div
                        className={cn(
                          "absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent transition-opacity",
                          active ? "opacity-100" : "opacity-0 group-hover:opacity-60",
                        )}
                      />
                      <div
                        className={cn(
                          "grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2 rounded-[12px] px-3 py-2 transition",
                          active ? "bg-[rgba(180,106,44,0.045)]" : "hover:bg-[rgba(180,106,44,0.08)]",
                        )}
                      >
                        <button
                          className="flex min-w-0 items-start gap-2.5 overflow-hidden text-left"
                          onClick={() => onSelectConversation(conversation.id)}
                          type="button"
                        >
                          <div
                            className={cn(
                              "mt-0.5 rounded-[10px] p-1.5 transition",
                              active ? "bg-[rgba(180,106,44,0.05)] text-accent" : "bg-panel-strong text-accent",
                            )}
                          >
                            <Bot className="h-3.5 w-3.5" />
                          </div>

                          <div className="min-w-0 flex-1 overflow-hidden">
                            <div className="truncate text-[14px] font-medium leading-5 text-foreground">
                              {conversation.title}
                            </div>
                            <div className="mt-0.5 text-[11px] leading-4 text-muted-foreground">
                              {conversation.time}
                            </div>
                          </div>
                        </button>

                        <div className="mt-0.5 flex shrink-0 items-center gap-1">
                          <button
                            className="inline-flex h-7 w-7 items-center justify-center rounded-[9px] text-muted-foreground transition hover:bg-[rgba(180,106,44,0.10)] hover:text-accent"
                            onClick={() => onRenameConversation(conversation.id)}
                            title="重命名会话"
                            type="button"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button
                            className="inline-flex h-7 w-7 items-center justify-center rounded-[9px] text-muted-foreground transition hover:bg-[rgba(180,106,44,0.10)] hover:text-accent disabled:opacity-50"
                            disabled={deletingConversationId === conversation.id}
                            onClick={() => onDeleteConversation(conversation.id)}
                            title="删除会话"
                            type="button"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>

          <button
            className="mt-2 inline-flex h-10 w-full items-center justify-center gap-2 rounded-[11px] border border-border bg-panel-strong px-3 text-[13px] text-muted-foreground transition hover:bg-panel-muted hover:text-accent"
            onClick={onOpenSettings}
            type="button"
          >
            <Settings2 className="h-4 w-4" />
            设置
          </button>
        </>
      )}
    </aside>
  );
}
