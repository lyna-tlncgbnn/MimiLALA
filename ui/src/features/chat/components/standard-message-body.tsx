import { useEffect, useRef } from "react";

import type { ToolCallPayload } from "@/features/chat/api/chat-schemas";
import { MessageContent } from "@/features/chat/components/message-content";
import {
  formatToolCallArgs,
  getToolCallName,
} from "@/features/chat/components/message-body-utils";
import { cn } from "@/shared/lib/utils";

export function StandardMessageBody({
  role,
  main,
  toolCalls,
  contentId,
  isCollapsed,
  maxHeight,
  overlayClassName,
  onOverflowChange,
}: {
  role: "user" | "assistant";
  main: string;
  toolCalls: ToolCallPayload[];
  contentId: string;
  isCollapsed: boolean;
  maxHeight: number;
  overlayClassName: string;
  onOverflowChange: (isOverflowing: boolean) => void;
}) {
  const contentRef = useRef<HTMLDivElement | null>(null);
  const hasToolCalls = role === "assistant" && toolCalls.length > 0;
  const hasMainContent = main.trim().length > 0;
  const hasVisibleContent = hasMainContent || hasToolCalls;

  useEffect(() => {
    const node = contentRef.current;

    if (!node) {
      return undefined;
    }

    const updateOverflowState = () => {
      onOverflowChange(node.scrollHeight > maxHeight + 1);
    };

    updateOverflowState();

    const resizeObserver = new ResizeObserver(() => {
      updateOverflowState();
    });

    resizeObserver.observe(node);

    return () => {
      resizeObserver.disconnect();
    };
  }, [main, toolCalls, maxHeight, onOverflowChange]);

  return (
    <div className="relative min-w-0">
      <div
        aria-expanded={!isCollapsed}
        className={cn("min-w-0", isCollapsed && "overflow-hidden")}
        id={contentId}
        ref={contentRef}
        style={isCollapsed ? { maxHeight: `${maxHeight}px` } : undefined}
      >
        {hasToolCalls ? (
          <div className="mb-3 space-y-2 last:mb-0">
            {toolCalls.map((toolCall, index) => {
              const toolName = getToolCallName(toolCall);
              const argsSummary = formatToolCallArgs(toolCall);
              return (
                <div key={String(toolCall.id ?? `${toolName}:${index}`)} className="py-1">
                  <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Calling Tool
                  </div>
                  <div className="mt-1 text-[14px] font-medium leading-6 text-foreground">{toolName}</div>
                  {argsSummary ? (
                    <div className="mt-1 font-mono text-[12px] leading-5 text-muted-foreground">
                      {argsSummary}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}

        {hasMainContent ? <MessageContent content={main} mode={role === "assistant" ? "markdown" : "plain"} /> : null}

        {!hasVisibleContent ? (
          <div className="text-[13px] leading-6 text-muted-foreground">No visible content.</div>
        ) : null}
      </div>

      {isCollapsed ? (
        <div
          aria-hidden="true"
          className={cn("pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-b", overlayClassName)}
        />
      ) : null}
    </div>
  );
}
