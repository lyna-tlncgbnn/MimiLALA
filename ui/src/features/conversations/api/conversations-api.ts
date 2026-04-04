import { z } from "zod";

import { requestJson } from "@/shared/api/http-client";
import { conversationSummarySchema, type ConversationSummary } from "@/features/conversations/api/conversations-schemas";

export async function listConversations() {
  return requestJson("/api/conversations", { method: "GET" }, (value) =>
    z.array(conversationSummarySchema).parse(value),
  );
}

export async function createConversation(name?: string) {
  return requestJson(
    "/api/conversations",
    {
      method: "POST",
      body: JSON.stringify({ name: name || null }),
    },
    (value) => conversationSummarySchema.parse(value),
  );
}

export async function renameConversation(conversationId: string, name: string) {
  return requestJson(
    `/api/conversations/${conversationId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ name }),
    },
    (value) => conversationSummarySchema.parse(value),
  );
}

export async function deleteConversation(conversationId: string) {
  return requestJson(
    `/api/conversations/${conversationId}`,
    { method: "DELETE" },
    () => undefined,
  );
}

export type { ConversationSummary };
