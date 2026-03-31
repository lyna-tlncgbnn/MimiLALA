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
export type ToolCallPayload = NonNullable<ChatMessage["tool_calls"]>[number];
export type ChatStreamEvent =
  | {
      event: "user_message_accepted";
      data: {
        conversation_id: string;
        message_id: string;
        timestamp: string;
        content: string;
      };
    }
  | {
      event: "assistant_waiting";
      data: {
        conversation_id: string;
        timestamp: string;
      };
    }
  | {
      event: "assistant_message_started";
      data: {
        message_id: string;
        timestamp: string;
      };
    }
  | {
      event: "assistant_delta";
      data: {
        message_id: string;
        delta: string;
      };
    }
  | {
      event: "tool_started";
      data: {
        tool_call_id: string;
        tool_name: string;
        args: Record<string, unknown>;
        timestamp: string;
      };
    }
  | {
      event: "tool_finished";
      data: {
        tool_call_id: string;
        tool_name: string;
        tool_output: string;
        timestamp: string;
      };
    }
  | {
      event: "assistant_completed";
      data: {
        message_id: string;
        timestamp: string;
        content: string;
      };
    }
  | {
      event: "conversation_committed";
      data: {
        conversation_id: string;
      };
    }
  | {
      event: "error";
      data: {
        message: string;
      };
    }
  | {
      event: "done";
      data: Record<string, never>;
    };

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

export async function streamMessage(
  conversationId: string,
  content: string,
  onEvent: (event: ChatStreamEvent) => void | Promise<void>,
) {
  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ content }),
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

  if (!response.body) {
    throw new Error("Streaming response body was empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex !== -1) {
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);

      const parsedEvent = parseSseEvent(rawEvent);
      if (parsedEvent) {
        await onEvent(parsedEvent);
      }

      boundaryIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }

  if (buffer.trim()) {
    const parsedEvent = parseSseEvent(buffer);
    if (parsedEvent) {
      await onEvent(parsedEvent);
    }
  }
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
