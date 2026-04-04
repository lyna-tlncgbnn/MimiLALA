import { z } from "zod";

export const conversationSummarySchema = z.object({
  conversation_id: z.string(),
  name: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type ConversationSummary = z.infer<typeof conversationSummarySchema>;
