import { memo } from "react";
import { ArrowUpRight } from "lucide-react";

import { Button } from "@/components/ui/button";

export const ChatComposer = memo(function ChatComposer({
  draft,
  isSending,
  onDraftChange,
  onSend,
}: {
  draft: string;
  isSending: boolean;
  onDraftChange: (value: string) => void;
  onSend: () => void | Promise<void>;
}) {
  return (
    <div className="mt-2 shrink-0 flex justify-center">
      <div className="flex w-full items-center gap-2 rounded-[12px] border border-border bg-[rgba(255,255,255,0.98)] px-3 py-2 shadow-[0_8px_24px_rgba(32,33,35,0.05)] sm:w-[88%] md:w-[68%] md:min-w-[520px] xl:w-1/2 xl:max-w-[820px]">
        <input
          className="h-8 w-full min-w-0 bg-transparent text-[13px] text-foreground outline-none placeholder:text-muted-foreground"
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void onSend();
            }
          }}
          placeholder="输入你的问题或任务..."
          value={draft}
        />
        <Button
          className="h-8 gap-1.5 rounded-[10px] px-3 text-[12px]"
          disabled={isSending || !draft.trim()}
          onClick={() => void onSend()}
          size="sm"
        >
          {isSending ? "处理中" : "发送"}
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
});
