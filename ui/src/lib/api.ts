import { z } from "zod";

const conversationSummarySchema = z.object({
  conversation_id: z.string(),
  name: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

const messageSchema = z.object({
  message_id: z.string().nullable().optional(),
  timestamp: z.string().nullable().optional(),
  role: z.string(),
  content: z.string(),
  name: z.string().nullable().optional(),
  tool_call_id: z.string().nullable().optional(),
  tool_calls: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
});

const conversationDetailSchema = z.object({
  conversation: conversationSummarySchema,
  messages: z.array(messageSchema),
});

const sendMessageResponseSchema = z.object({
  conversation: conversationSummarySchema,
  messages: z.array(messageSchema),
  reply: messageSchema,
});

export type ConversationSummary = z.infer<typeof conversationSummarySchema>;
export type ChatMessage = z.infer<typeof messageSchema>;
export type ConversationDetail = z.infer<typeof conversationDetailSchema>;

const API_BASE = "http://127.0.0.1:8000";

async function request<T>(path: string, init: RequestInit, schema: z.ZodSchema<T>) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = String(body.detail);
      }
    } catch {
      // ignore non-json errors
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return schema.parse(undefined);
  }

  return schema.parse(await response.json());
}

export async function listConversations() {
  return request("/api/conversations", { method: "GET" }, z.array(conversationSummarySchema));
}

export async function createConversation(name?: string) {
  return request(
    "/api/conversations",
    {
      method: "POST",
      body: JSON.stringify({ name: name || null }),
    },
    conversationSummarySchema,
  );
}

export async function getConversation(conversationId: string) {
  return request(
    `/api/conversations/${conversationId}`,
    { method: "GET" },
    conversationDetailSchema,
  );
}

export async function renameConversation(conversationId: string, name: string) {
  return request(
    `/api/conversations/${conversationId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ name }),
    },
    conversationSummarySchema,
  );
}

export async function deleteConversation(conversationId: string) {
  return request(
    `/api/conversations/${conversationId}`,
    { method: "DELETE" },
    z.undefined(),
  );
}

export async function sendMessage(conversationId: string, content: string) {
  return request(
    `/api/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
    sendMessageResponseSchema,
  );
}
