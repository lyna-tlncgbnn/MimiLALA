import { ChevronRight, Wrench } from "lucide-react";

export function ExecutionHint({
  onOpen,
}: {
  onOpen: () => void;
}) {
  return (
    <button
      className="inline-flex items-center gap-2 px-1 py-1 text-left text-[13px] font-medium text-[rgba(60,62,68,0.62)] transition hover:text-foreground"
      onClick={onOpen}
      type="button"
    >
      <Wrench className="h-4 w-4" />
      <span>查看执行</span>
      <ChevronRight className="h-4 w-4" />
    </button>
  );
}
