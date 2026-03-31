import { MessageContent } from "@/features/chat/components/message-content";
import { cn } from "@/shared/lib/utils";

export function ToolMessageBody({
  main,
  contentId,
  isExpanded,
  viewportHeight,
}: {
  main: string;
  contentId: string;
  isExpanded: boolean;
  viewportHeight: number;
}) {
  if (!isExpanded) {
    return null;
  }

  return (
    <div
      className={cn(
        "min-w-0 overflow-y-auto border border-[rgba(32,33,35,0.10)] bg-[rgba(255,255,255,0.82)] px-3 py-2",
        "scrollbar-thin scrollbar-track-transparent",
      )}
      id={contentId}
      style={{ height: `${viewportHeight}px` }}
    >
      <MessageContent content={main} mode="plain" />
    </div>
  );
}

