import { memo, useCallback, useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, ChevronUp, Copy, Hammer, Search, Sparkles } from "lucide-react";

import type { ToolCallPayload } from "@/features/chat/api/chat-schemas";
import { formatToolCallLine } from "@/features/chat/components/message-body-utils";
import { StandardMessageBody } from "@/features/chat/components/standard-message-body";
import { ToolMessageBody } from "@/features/chat/components/tool-message-body";
import { cn } from "@/shared/lib/utils";

const STANDARD_COLLAPSE_MAX_HEIGHT = 240;
const TOOL_VIEWPORT_HEIGHT = 240;

const COLLAPSE_CONFIG = {
  user: {
    autoCollapse: true,
    overlayClassName: "from-[rgba(255,255,255,0)] to-[rgba(255,255,255,0.98)]",
  },
  assistant: {
    autoCollapse: false,
    overlayClassName: "from-[rgba(255,255,255,0)] to-[rgba(255,255,255,0.98)]",
  },
  tool: {
    autoCollapse: true,
    overlayClassName: "from-[rgba(249,249,249,0)] to-[rgba(249,249,249,0.98)]",
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
  const defaultExpanded = isTool ? false : !collapseConfig.autoCollapse;
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
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

  const showCollapseToggle = isTool ? main.trim().length > 0 : isOverflowing;
  const isCollapsed = isTool ? !isExpanded : showCollapseToggle && !isExpanded;
  const showActionBar = !isUser;
  const showInlineUserToggle = isUser && showCollapseToggle;
  const hasToolCalls = isAssistant && toolCalls.length > 0;
  const hasMainContent = main.trim().length > 0;
  const hasVisibleContent = hasMainContent || hasToolCalls;

  const toolCallLines = toolCalls.map(formatToolCallLine);
  const copyText = hasMainContent ? main : toolCallLines.join("\n");

  const handleStandardOverflowChange = useCallback(
    (nextOverflowing: boolean) => {
      if (isTool) {
        return;
      }

      const wasOverflowing = wasOverflowingRef.current;
      setIsOverflowing(nextOverflowing);

      if (!nextOverflowing) {
        setIsExpanded(true);
        hasUserToggledRef.current = false;
      } else if (!wasOverflowing && !hasUserToggledRef.current) {
        setIsExpanded(defaultExpanded);
      }

      wasOverflowingRef.current = nextOverflowing;
    },
    [defaultExpanded, isTool],
  );

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
        {isTool ? (
          <ToolMessageBody
            contentId={contentId}
            isExpanded={isExpanded}
            main={main}
            viewportHeight={TOOL_VIEWPORT_HEIGHT}
          />
        ) : (
          <StandardMessageBody
            contentId={contentId}
            isCollapsed={isCollapsed}
            main={main}
            maxHeight={STANDARD_COLLAPSE_MAX_HEIGHT}
            onOverflowChange={handleStandardOverflowChange}
            overlayClassName={collapseConfig.overlayClassName}
            role={role}
            toolCalls={toolCalls}
          />
        )}

        {showInlineUserToggle ? (
          <button
            aria-controls={contentId}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse message" : "Expand message"}
            className="mt-2 inline-flex h-8 w-8 items-center justify-center rounded-none text-muted-foreground transition hover:bg-panel-strong hover:text-foreground"
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
                "inline-flex h-8 w-8 items-center justify-center rounded-none transition",
                copyState === "copied" && "bg-[rgba(32,33,35,0.08)] text-accent",
                copyState === "error" && "bg-[rgba(154,50,36,0.08)] text-[rgba(154,50,36,0.9)]",
                copyState === "idle" && "hover:bg-panel-strong hover:text-foreground",
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
                className="inline-flex h-8 w-8 items-center justify-center rounded-none transition hover:bg-panel-strong hover:text-foreground"
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
