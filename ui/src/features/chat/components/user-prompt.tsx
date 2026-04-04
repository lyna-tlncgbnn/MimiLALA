import { User2 } from "lucide-react";

export function UserPrompt({
  content,
  timestamp,
}: {
  content: string;
  timestamp?: string | null;
}) {
  return (
    <div className="flex w-full justify-end">
      <div className="max-w-[72%] px-2 py-1 text-right text-[14px] leading-7 text-foreground">
        <div className="flex items-center justify-end gap-2 text-[12px] font-medium text-muted-foreground">
          <User2 className="h-4 w-4" />
          <span>你</span>
          {timestamp ? <span>{timestamp}</span> : null}
        </div>
        <div className="mt-1 whitespace-pre-wrap break-words">{content}</div>
      </div>
    </div>
  );
}
