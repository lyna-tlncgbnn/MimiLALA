import type { ToolCallPayload } from "@/features/chat/api/chat-schemas";

export function getToolCallName(toolCall: ToolCallPayload) {
  return typeof toolCall.name === "string" && toolCall.name.trim() ? toolCall.name : "unknown_tool";
}

export function formatToolCallArgs(toolCall: ToolCallPayload) {
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

export function formatToolCallLine(toolCall: ToolCallPayload) {
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
