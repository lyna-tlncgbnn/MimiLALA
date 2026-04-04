import { useState } from "react";
import * as Collapsible from "@radix-ui/react-collapsible";
import {
  BookOpenText,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileSearch,
  FileText,
  LoaderCircle,
  Search,
  Wrench,
  XCircle,
} from "lucide-react";

import { MessageContent } from "@/features/chat/components/message-content";

export type TimelineStep = {
  id: string;
  stepType: string;
  title: string;
  status: string;
  timestamp?: string | null;
  toolName?: string | null;
  summary?: string | null;
  input?: string | null;
  output?: string | null;
};

function statusLabel(status: string, stepCount: number) {
  if (status === "running") {
    return "执行中";
  }
  if (status === "failed") {
    return "执行失败";
  }
  if (stepCount > 0) {
    return `已执行，${stepCount} 个步骤`;
  }
  return "已执行";
}

function iconForStep(step: TimelineStep) {
  const text = `${step.title} ${step.toolName ?? ""}`.toLowerCase();

  if (step.status === "running") {
    return LoaderCircle;
  }
  if (step.status === "failed") {
    return XCircle;
  }
  if (text.includes("search") || text.includes("搜索")) {
    return Search;
  }
  if (text.includes("read") || text.includes("文档") || text.includes("file")) {
    return BookOpenText;
  }
  if (text.includes("confirm") || text.includes("确认") || text.includes("requirement")) {
    return ClipboardList;
  }
  if (text.includes("ppt") || text.includes("write") || text.includes("生成")) {
    return FileText;
  }
  return FileSearch;
}

function TimelineDot({ active = false, failed = false }: { active?: boolean; failed?: boolean }) {
  const color = failed ? "bg-[#b42318]" : active ? "bg-[#3b82f6]" : "bg-[rgba(32,33,35,0.28)]";
  return <span className={`absolute left-0 top-[12px] h-[8px] w-[8px] rounded-full ${color}`} />;
}

function TimelineLine() {
  return <span className="absolute bottom-[-24px] left-[3.5px] top-[20px] w-px bg-[rgba(32,33,35,0.12)]" />;
}

function StepStatusIcon({ step }: { step: TimelineStep }) {
  const Icon = iconForStep(step);

  if (step.status === "running") {
    return <LoaderCircle className="h-4 w-4 animate-spin text-[#3b82f6]" />;
  }

  if (step.status === "failed") {
    return <XCircle className="h-4 w-4 text-[#b42318]" />;
  }

  return <Icon className="h-4 w-4 text-[rgba(32,33,35,0.72)]" />;
}

function StepRow({
  step,
  isLast,
}: {
  step: TimelineStep;
  isLast: boolean;
}) {
  const [open, setOpen] = useState(false);
  const detailText = [step.summary, step.input, step.output].filter(Boolean).join("\n\n").trim();
  const hasDetail = detailText.length > 0;

  return (
    <Collapsible.Root className="relative pl-8" disabled={!hasDetail} onOpenChange={setOpen} open={open}>
      <TimelineDot active={step.status === "running"} failed={step.status === "failed"} />
      {!isLast ? <TimelineLine /> : null}

      <Collapsible.Trigger asChild>
        <button
          className={[
            "grid w-full grid-cols-[16px_minmax(0,1fr)] items-center gap-x-3 py-1 text-left",
            hasDetail
              ? "text-[rgba(32,33,35,0.72)] transition hover:text-[rgba(32,33,35,0.82)]"
              : "cursor-default text-[rgba(32,33,35,0.72)]",
          ].join(" ")}
          type="button"
        >
          <div className="flex h-4 w-4 items-center justify-center self-center">
            <StepStatusIcon step={step} />
          </div>

          <div className="flex min-w-0 items-center gap-1 text-[15px] font-medium leading-6">
            <span className="truncate">{step.title}</span>
            {hasDetail ? (
              <span className="shrink-0 text-[rgba(32,33,35,0.42)]">
                {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </span>
            ) : null}
          </div>
        </button>
      </Collapsible.Trigger>

      {hasDetail ? (
        <Collapsible.Content className="overflow-hidden">
          <div className="ml-2 mt-1 border-l border-[rgba(32,33,35,0.1)] pl-4 text-[14px] leading-7 text-[rgba(32,33,35,0.82)]">
            <MessageContent content={detailText} mode="plain" />
          </div>
        </Collapsible.Content>
      ) : null}
    </Collapsible.Root>
  );
}

export function RunStepsPanel({
  status,
  steps,
  loading = false,
  error = null,
  defaultExpanded = false,
  expanded: expandedProp,
  onExpandedChange,
}: {
  status: "running" | "completed" | "failed";
  steps: TimelineStep[];
  loading?: boolean;
  error?: string | null;
  defaultExpanded?: boolean;
  expanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
}) {
  const [uncontrolledExpanded, setUncontrolledExpanded] = useState(defaultExpanded);
  const expanded = expandedProp ?? uncontrolledExpanded;
  const headerLabel = statusLabel(status, steps.length);
  const hasVisibleBody = loading || Boolean(error) || steps.length > 0;

  if (!hasVisibleBody) {
    return null;
  }

  return (
    <Collapsible.Root className="pl-1" onOpenChange={onExpandedChange ?? setUncontrolledExpanded} open={expanded}>
      <Collapsible.Trigger asChild>
        <button className="flex w-full items-center gap-3 py-1 text-left" type="button">
          <Wrench className="h-4 w-4 shrink-0 text-[rgba(32,33,35,0.72)]" />
          <span className="inline-flex items-center gap-1 text-[14px] font-medium text-[rgba(32,33,35,0.62)]">
            <span>{headerLabel}</span>
            <span className="text-[rgba(32,33,35,0.42)]">
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </span>
          </span>
        </button>
      </Collapsible.Trigger>

      <Collapsible.Content className="overflow-hidden">
        <div className="mt-2.5 space-y-3">
          {loading ? (
            <div className="relative pl-8">
              <TimelineDot />
              <div className="border-l border-[rgba(32,33,35,0.1)] pl-4 text-[13px] text-muted-foreground">
                正在加载执行过程...
              </div>
            </div>
          ) : null}

          {error ? (
            <div className="relative pl-8">
              <TimelineDot failed />
              <div className="border-l border-[rgba(180,35,24,0.18)] pl-4 text-[13px] text-[#b42318]">
                {error}
              </div>
            </div>
          ) : null}

          {!loading && !error
            ? steps.map((step, index) => (
                <StepRow
                  key={step.id}
                  isLast={index === steps.length - 1}
                  step={step}
                />
              ))
            : null}
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
