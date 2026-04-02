export type ActiveRunStep = {
  step_id: string | null;
  step_type: string;
  title: string;
  status: string;
  display_mode: string;
  tool_name?: string | null;
  tool_call_id?: string | null;
  args?: Record<string, unknown>;
  output?: string;
  timestamp: string;
};

export type ActiveRunState = {
  localId: string;
  runId: string | null;
  conversationId: string | null;
  startedAt: string | null;
  userMessageId: string | null;
  userContent: string;
  status: "running" | "completed" | "failed";
  steps: ActiveRunStep[];
  finalMessageId: string | null;
  finalContent: string;
  finalTimestamp: string | null;
  error: string | null;
};
