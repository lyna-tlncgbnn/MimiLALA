import { requestJson } from "@/shared/api/http-client";
import { streamJsonEvents } from "@/shared/api/sse";
import {
  conversationDetailSchema,
  conversationRunsDetailSchema,
  runArtifactsDetailSchema,
  runStepsDetailSchema,
  sendMessageResponseSchema,
  sendRunResponseSchema,
  type ChatStreamEvent,
} from "@/features/chat/api/chat-schemas";

export async function getConversation(conversationId: string) {
  return requestJson(
    `/api/conversations/${conversationId}`,
    { method: "GET" },
    (value) => conversationDetailSchema.parse(value),
  );
}

export async function sendMessage(conversationId: string, content: string) {
  return requestJson(
    `/api/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
    (value) => sendMessageResponseSchema.parse(value),
  );
}

export async function sendRun(conversationId: string, content: string) {
  return requestJson(
    `/api/conversations/${conversationId}/runs`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
    (value) => sendRunResponseSchema.parse(value),
  );
}

export async function listConversationRuns(conversationId: string) {
  return requestJson(
    `/api/conversations/${conversationId}/runs`,
    { method: "GET" },
    (value) => conversationRunsDetailSchema.parse(value),
  );
}

export async function getRunSteps(runId: string) {
  return requestJson(`/api/runs/${runId}/steps`, { method: "GET" }, (value) =>
    runStepsDetailSchema.parse(value),
  );
}

export async function getRunArtifacts(runId: string) {
  return requestJson(`/api/runs/${runId}/artifacts`, { method: "GET" }, (value) =>
    runArtifactsDetailSchema.parse(value),
  );
}

export async function streamMessage(
  conversationId: string,
  content: string,
  onEvent: (event: ChatStreamEvent) => void | Promise<void>,
) {
  return streamJsonEvents(
    `/api/conversations/${conversationId}/runs/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content }),
    },
    parseSseEvent,
    onEvent,
  );
}

function parseSseEvent(rawEvent: string): ChatStreamEvent | null {
  const normalized = rawEvent.replace(/\r/g, "");
  const lines = normalized.split("\n");
  let eventName = "";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!eventName) {
    return null;
  }

  const rawData = dataLines.join("\n");
  const data = rawData ? JSON.parse(rawData) : {};
  return {
    event: eventName,
    data,
  } as ChatStreamEvent;
}
