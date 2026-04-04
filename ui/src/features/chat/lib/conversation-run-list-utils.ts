import type { RunStep } from "@/features/chat/api/chat-schemas";
import type { TimelineStep } from "@/features/chat/components/run-steps-panel";
import type { ActiveRunState } from "@/features/chat/types";

export const emptyConversationPrompts = [
  "帮我总结一下这个项目目前的架构。",
  "读取某个文件，然后帮我做一个摘要。",
  "新建一个会话，并规划一下下一步开发任务。",
  "告诉我当前默认会话里最近做了什么。",
];

export function formatRunMessageTime(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function stringifyRunPayload(raw: string | null | undefined) {
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "string") {
      return parsed;
    }
    if (parsed && typeof parsed === "object" && "text" in parsed && typeof parsed.text === "string") {
      return parsed.text;
    }
    return JSON.stringify(parsed, null, 2);
  } catch {
    return raw;
  }
}

export function toHistoricalTimelineStep(step: RunStep): TimelineStep {
  return {
    id: step.step_id,
    stepType: step.step_type,
    title: step.title,
    status: step.status,
    timestamp: step.ended_at ?? step.started_at,
    toolName: step.tool_name,
    summary: step.summary_text,
    input: stringifyRunPayload(step.input_json),
    output: stringifyRunPayload(step.output_json),
  };
}

export function toActiveTimelineStep(step: ActiveRunState["steps"][number]): TimelineStep {
  return {
    id: step.step_id ?? step.tool_call_id ?? `${step.step_type}:${step.timestamp}`,
    stepType: step.step_type,
    title: step.title,
    status: step.status,
    timestamp: step.timestamp,
    toolName: step.tool_name ?? null,
    input: step.args ? JSON.stringify(step.args, null, 2) : null,
    output: step.output ?? null,
  };
}
