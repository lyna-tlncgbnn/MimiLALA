import { Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import { MessageContent } from "@/features/chat/components/message-content";

export function AgentSection({
  body,
  children,
  streaming = false,
}: {
  body: string;
  children?: ReactNode;
  streaming?: boolean;
}) {
  const hasBody = body.trim().length > 0;
  const showWaitingIndicator = streaming && !hasBody;

  return (
    <section className="max-w-[84%] space-y-4">
      {showWaitingIndicator ? (
        <div className="flex items-center gap-3 text-foreground">
          <Sparkles className="h-5 w-5 animate-pulse text-[rgba(32,33,35,0.78)]" />
        </div>
      ) : null}

      {children}

      {hasBody ? (
        <div className="pl-1 text-[15px] leading-8 text-foreground">
          <MessageContent content={body} mode="markdown" />
        </div>
      ) : null}
    </section>
  );
}
