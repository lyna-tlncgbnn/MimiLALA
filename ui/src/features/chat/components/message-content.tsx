import { memo } from "react";

import { RichContentRenderer } from "@/features/chat/renderers/rich-content-renderer";

function MessageContentInner({
  content,
  mode = "plain",
}: {
  content: string;
  mode?: "plain" | "markdown";
}) {
  if (!content) {
    return null;
  }

  return <RichContentRenderer content={content} mode={mode} />;
}

export const MessageContent = memo(MessageContentInner);
