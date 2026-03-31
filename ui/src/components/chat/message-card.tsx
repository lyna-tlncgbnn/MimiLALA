import { memo, useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, ChevronUp, Copy, Hammer, Search, Sparkles } from "lucide-react";

import { MessageContent } from "@/components/chat/message-content";
import type { ToolCallPayload } from "@/lib/api";
import { cn } from "@/lib/utils";

const COLLAPSE_MAX_HEIGHT = 240;

const COLLAPSE_CONFIG = {
  user: {
    autoCollapse: true,
    overlayClassName: "from-[rgba(249,246,241,0)] to-[rgba(249,246,241,0.98)]",
  },
  assistant: {
    autoCollapse: false,
    overlayClassName: "from-[rgba(252,251,247,0)] to-[rgba(252,251,247,0.98)]",
  },
  tool: {
    autoCollapse: true,
    overlayClassName: "from-[rgba(248,248,244,0)] to-[rgba(248,248,244,0.98)]",
  },
} satisfies Record<
  "user" | "assistant" | "tool",
  {
    autoCollapse: boolean;
    overlayClassName: string;
  }
>;

function MessageCardInner({
  role,
  title,
  main,
  toolCalls = [],
  timestamp,
}: {
  role: "user" | "assistant" | "tool";
  title: string;
  main: string;
  toolCalls?: ToolCallPayload[];
  timestamp?: string | null;
}) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";
  const isTool = role === "tool";
  const collapseConfig = COLLAPSE_CONFIG[role];
  const defaultExpanded = !collapseConfig.autoCollapse;
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const contentRef = useRef<HTMLDivElement | null>(null);
  const wasOverflowingRef = useRef(false);
  const hasUserToggledRef = useRef(false);
  const copyResetTimerRef = useRef<number | null>(null);
  const contentId = useId();

  useEffect(() => {
    return () => {
      if (copyResetTimerRef.current) {
        window.clearTimeout(copyResetTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setIsOverflowing(false);
    setIsExpanded(defaultExpanded);
    setCopyState("idle");
    wasOverflowingRef.current = false;
    hasUserToggledRef.current = false;

    if (copyResetTimerRef.current) {
      window.clearTimeout(copyResetTimerRef.current);
      copyResetTimerRef.current = null;
    }
  }, [defaultExpanded, main, role]);

  useEffect(() => {
    const node = contentRef.current;

    if (!node) {
      return undefined;
    }

    const updateOverflowState = () => {
      const nextOverflowing = node.scrollHeight > COLLAPSE_MAX_HEIGHT + 1;
      const wasOverflowing = wasOverflowingRef.current;

      setIsOverflowing(nextOverflowing);

      if (!nextOverflowing) {
        setIsExpanded(true);
        hasUserToggledRef.current = false;
      } else if (!wasOverflowing && !hasUserToggledRef.current) {
        setIsExpanded(defaultExpanded);
      }

      wasOverflowingRef.current = nextOverflowing;
    };

    updateOverflowState();

    const resizeObserver = new ResizeObserver(() => {
      updateOverflowState();
    });

    resizeObserver.observe(node);

    return () => {
      resizeObserver.disconnect();
    };
  }, [defaultExpanded, main]);

  const showCollapseToggle = isOverflowing;
  const isCollapsed = showCollapseToggle && !isExpanded;
  const showActionBar = !isUser;
  const showInlineUserToggle = isUser && showCollapseToggle;
  const hasToolCalls = isAssistant && toolCalls.length > 0;
  const hasMainContent = main.trim().length > 0;
  const hasVisibleContent = hasMainContent || hasToolCalls;

  const toolCallLines = toolCalls.map(formatToolCallLine);
  const copyText = hasMainContent ? main : toolCallLines.join("\n");

  const toggleExpanded = () => {
    hasUserToggledRef.current = true;
    setIsExpanded((current) => !current);
  };

  const handleCopy = async () => {
    if (copyResetTimerRef.current) {
      window.clearTimeout(copyResetTimerRef.current);
    }

    try {
      await navigator.clipboard.writeText(copyText);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }

    copyResetTimerRef.current = window.setTimeout(() => {
      setCopyState("idle");
      copyResetTimerRef.current = null;
    }, 1800);
  };

  return (
    <article
      className={cn(
        "inline-flex w-fit max-w-full min-w-0 flex-col px-1 py-1",
        isUser && "max-w-[70%]",
        isAssistant && "max-w-[80%]",
        isTool && "max-w-[84%]",
      )}
    >
      <div className="flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.22em] text-[rgba(60,62,68,0.72)]">
        {isAssistant ? (
          <Sparkles className="h-4 w-4" />
        ) : isTool ? (
          <Hammer className="h-4 w-4" />
        ) : (
          <Search className="h-4 w-4" />
        )}
        <span>{title.toUpperCase()}</span>
        {timestamp ? (
          <span className="text-[11px] font-medium tracking-[0.08em] text-muted-foreground normal-case">
            {timestamp}
          </span>
        ) : null}
      </div>

      <div className="mt-2 min-w-0 text-[14px] leading-7 text-foreground">
        <div className="relative min-w-0">
          <div
            aria-expanded={showCollapseToggle ? isExpanded : undefined}
            className={cn("min-w-0", isCollapsed && "overflow-hidden")}
            id={contentId}
            ref={contentRef}
            style={isCollapsed ? { maxHeight: `${COLLAPSE_MAX_HEIGHT}px` } : undefined}
          >
            {hasToolCalls ? (
              <div className="mb-3 space-y-2 last:mb-0">
                {toolCalls.map((toolCall, index) => {
                  const toolName = getToolCallName(toolCall);
                  const argsSummary = formatToolCallArgs(toolCall);
                  return (
                    <div
                      key={String(toolCall.id ?? `${toolName}:${index}`)}
                      className="py-1"
                    >
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

            {hasMainContent ? <MessageContent content={main} mode={isAssistant ? "markdown" : "plain"} /> : null}

            {!hasVisibleContent ? (
              <div className="text-[13px] leading-6 text-muted-foreground">No visible content.</div>
            ) : null}
          </div>

          {isCollapsed ? (
            <div
              aria-hidden="true"
              className={cn(
                "pointer-events-none absolute inset-x-0 bottom-0 h-24 rounded-b-[14px] bg-gradient-to-b",
                collapseConfig.overlayClassName,
              )}
            />
          ) : null}
        </div>

        {showInlineUserToggle ? (
          <button
            aria-controls={contentId}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse message" : "Expand message"}
            className="mt-2 inline-flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition hover:bg-[rgba(180,106,44,0.08)] hover:text-foreground"
            onClick={toggleExpanded}
            type="button"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        ) : null}

        {showActionBar ? (
          <div className="mt-3 flex items-center gap-1 text-muted-foreground">
            <button
              aria-label={copyState === "copied" ? "Copied" : copyState === "error" ? "Copy failed" : "Copy text"}
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-full transition",
                copyState === "copied" && "bg-[rgba(180,106,44,0.12)] text-accent",
                copyState === "error" && "bg-[rgba(154,50,36,0.08)] text-[rgba(154,50,36,0.9)]",
                copyState === "idle" && "hover:bg-[rgba(53,40,17,0.06)] hover:text-foreground",
              )}
              onClick={() => void handleCopy()}
              type="button"
            >
              {copyState === "copied" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </button>

            {showCollapseToggle ? (
              <button
                aria-controls={contentId}
                aria-expanded={isExpanded}
                aria-label={isExpanded ? "Collapse message" : "Expand message"}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full transition hover:bg-[rgba(53,40,17,0.06)] hover:text-foreground"
                onClick={toggleExpanded}
                type="button"
              >
                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function areToolCallsEqual(previous: ToolCallPayload[], next: ToolCallPayload[]) {
  if (previous === next) {
    return true;
  }

  if (previous.length !== next.length) {
    return false;
  }

  return previous.every((toolCall, index) => {
    const nextToolCall = next[index];
    return (
      toolCall.id === nextToolCall.id &&
      toolCall.name === nextToolCall.name &&
      JSON.stringify(toolCall.args ?? null) === JSON.stringify(nextToolCall.args ?? null)
    );
  });
}

export const MessageCard = memo(MessageCardInner, (previousProps, nextProps) => {
  return (
    previousProps.role === nextProps.role &&
    previousProps.title === nextProps.title &&
    previousProps.main === nextProps.main &&
    previousProps.timestamp === nextProps.timestamp &&
    areToolCallsEqual(previousProps.toolCalls ?? [], nextProps.toolCalls ?? [])
  );
});

function getToolCallName(toolCall: ToolCallPayload) {
  return typeof toolCall.name === "string" && toolCall.name.trim() ? toolCall.name : "unknown_tool";
}

function formatToolCallArgs(toolCall: ToolCallPayload) {
  const args = toolCall.args;

  if (!args || typeof args !== "object" || Array.isArray(args)) {
    return "";
  }

  const entries = Object.entries(args);

  if (entries.length === 0) {
    return "";
  }

  return entries
    .map(([key, value]) => `${key}=${formatToolCallValue(value)}`)
    .join(", ");
}

function formatToolCallLine(toolCall: ToolCallPayload) {
  const name = getToolCallName(toolCall);
  const argsSummary = formatToolCallArgs(toolCall);
  return argsSummary ? `Calling tool: ${name} (${argsSummary})` : `Calling tool: ${name}`;
}

function formatToolCallValue(value: unknown): string {
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
