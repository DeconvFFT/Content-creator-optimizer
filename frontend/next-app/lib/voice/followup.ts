import type { RealtimeVoiceAgentEventRecordResult } from "../api/types";

export type VoiceFollowupContinuationOptions = {
  agentIds?: string[];
  messageIds?: string[];
  continueMessageLineage?: boolean;
  useGemma?: boolean | null;
};

export type VoiceFollowupContinuation = {
  label: string;
  detail: string;
  failureLabel: string;
  options: VoiceFollowupContinuationOptions;
};

export function voiceFollowupContinuationForEvent(
  recorded: RealtimeVoiceAgentEventRecordResult
): VoiceFollowupContinuation {
  const isProviderRecovery =
    recorded.followup_kind === "provider_failure_recovery" ||
    recorded.event_type === "gemma_kokoro_voice_turn_failed";
  return {
    label: isProviderRecovery ? "Provider recovery queued" : "Voice follow-up queued",
    detail: isProviderRecovery
      ? "Continuing the Inference, Observability, and Harness recovery path."
      : "Continuing the specialist agent loop from the assistant voice response.",
    failureLabel: isProviderRecovery
      ? "Provider recovery continuation failed"
      : "Voice follow-up continuation failed",
    options: {
      agentIds: recorded.followup_worker_agent_ids,
      messageIds: recorded.followup_task_message_id
        ? [recorded.followup_task_message_id]
        : [],
      continueMessageLineage: Boolean(recorded.followup_task_message_id),
      useGemma: recorded.followup_worker_use_gemma
    }
  };
}
