import { PanelLeft } from "lucide-react";

type ChatHeaderProps = {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
};

export function ChatHeader({ sidebarCollapsed, onToggleSidebar }: ChatHeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-stretch border-b border-[rgba(32,33,35,0.08)] bg-[rgba(255,255,255,0.9)]">
      <div className="flex w-[88px] shrink-0 items-center justify-center">
        <button
          aria-label={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
          className="inline-flex h-10 w-10 items-center justify-center rounded-[12px] border border-border bg-[rgba(255,255,255,0.96)] text-foreground transition hover:bg-panel-strong"
          onClick={onToggleSidebar}
          type="button"
        >
          <PanelLeft className="h-4.5 w-4.5" />
        </button>
      </div>
      <div className="min-w-0 flex-1" />
    </header>
  );
}
