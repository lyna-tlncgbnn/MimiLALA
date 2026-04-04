export const chatQueryKeys = {
  conversation: (conversationId: string | null) => ["conversation", conversationId] as const,
  conversationRuns: (conversationId: string | null) => ["conversation-runs", conversationId] as const,
  runSteps: (runId: string) => ["run-steps", runId] as const,
  runArtifacts: (runId: string) => ["run-artifacts", runId] as const,
};
