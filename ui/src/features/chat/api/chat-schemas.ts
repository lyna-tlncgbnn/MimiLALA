import { z } from "zod";

import { conversationSummarySchema } from "@/features/conversations/api/conversations-schemas";

export const messageSchema = z.object({
  message_id: z.string().nullable().optional(),
  run_id: z.string().nullable().optional(),
  timestamp: z.string().nullable().optional(),
  role: z.string(),
  content: z.string(),
  name: z.string().nullable().optional(),
  tool_call_id: z.string().nullable().optional(),
  tool_calls: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
});

export const conversationDetailSchema = z.object({
  conversation: conversationSummarySchema,
  messages: z.array(messageSchema),
});

export const runSummarySchema = z.object({
  run_id: z.string(),
  conversation_id: z.string(),
  thread_id: z.string(),
  status: z.string(),
  started_at: z.string(),
  ended_at: z.string().nullable().optional(),
  workflow_name: z.string().nullable().optional(),
  user_message_id: z.string().nullable().optional(),
  final_message_id: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  step_count: z.number().default(0),
  visible_step_count: z.number().default(0),
  has_execution: z.boolean().default(false),
});

export const conversationRunsDetailSchema = z.object({
  conversation: conversationSummarySchema,
  runs: z.array(runSummarySchema),
});

export const runStepSchema = z.object({
  step_id: z.string(),
  run_id: z.string(),
  parent_step_id: z.string().nullable().optional(),
  step_type: z.string(),
  title: z.string(),
  status: z.string(),
  display_mode: z.string(),
  sort_order: z.number(),
  started_at: z.string(),
  ended_at: z.string().nullable().optional(),
  tool_name: z.string().nullable().optional(),
  tool_call_id: z.string().nullable().optional(),
  input_json: z.string().nullable().optional(),
  output_json: z.string().nullable().optional(),
  summary_text: z.string().nullable().optional(),
});

export const runStepsDetailSchema = z.object({
  run: runSummarySchema,
  steps: z.array(runStepSchema),
});

export const artifactSchema = z.object({
  artifact_id: z.string(),
  run_id: z.string(),
  step_id: z.string().nullable().optional(),
  artifact_type: z.string(),
  name: z.string(),
  uri: z.string(),
  metadata_json: z.string().nullable().optional(),
  created_at: z.string(),
});

export const runArtifactsDetailSchema = z.object({
  run: runSummarySchema,
  artifacts: z.array(artifactSchema),
});

export const sendMessageResponseSchema = z.object({
  conversation: conversationSummarySchema,
  messages: z.array(messageSchema),
  reply: messageSchema,
});

export const sendRunResponseSchema = z.object({
  conversation: conversationSummarySchema,
  run: runSummarySchema,
  messages: z.array(messageSchema),
  reply: messageSchema,
});

export type ChatMessage = z.infer<typeof messageSchema>;
export type ConversationDetail = z.infer<typeof conversationDetailSchema>;
export type RunSummary = z.infer<typeof runSummarySchema>;
export type ConversationRunsDetail = z.infer<typeof conversationRunsDetailSchema>;
export type RunStep = z.infer<typeof runStepSchema>;
export type RunStepsDetail = z.infer<typeof runStepsDetailSchema>;
export type Artifact = z.infer<typeof artifactSchema>;
export type RunArtifactsDetail = z.infer<typeof runArtifactsDetailSchema>;
export type ToolCallPayload = NonNullable<ChatMessage["tool_calls"]>[number];
export type ChatStreamEvent =
  | {
      event: "run_started";
      data: {
        run_id: string;
        conversation_id: string;
        user_message_id: string;
        started_at: string;
        content: string;
      };
    }
  | {
      event: "step_started";
      data: {
        run_id: string;
        step_id: string | null;
        step_type: string;
        title: string;
        status: string;
        display_mode: string;
        tool_name: string;
        tool_call_id: string;
        args: Record<string, unknown>;
        timestamp: string;
      };
    }
  | {
      event: "step_completed";
      data: {
        run_id: string;
        step_id: string | null;
        step_type: string;
        title: string;
        status: string;
        tool_name: string;
        tool_call_id: string;
        output: string;
        timestamp: string;
      };
    }
  | {
      event: "assistant_final_delta";
      data: {
        run_id: string;
        message_id: string;
        delta: string;
      };
    }
  | {
      event: "assistant_finalized";
      data: {
        run_id: string;
        message_id: string;
        timestamp: string;
        content: string;
      };
    }
  | {
      event: "run_completed";
      data: {
        run_id: string;
        conversation_id: string;
        final_message_id: string;
        ended_at: string;
      };
    }
  | {
      event: "run_failed";
      data: {
        run_id?: string;
        message: string;
      };
    }
  | {
      event: "done";
      data: Record<string, never>;
    };
