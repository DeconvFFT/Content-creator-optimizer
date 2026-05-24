import type { UUID } from "@/lib/api/types";

export const REHEARSAL_TARGET_FORMATS = ["post", "reel", "substack"];

export function buildTranscriptRehearsalTurnInput(input: {
  realtimeSessionId: UUID;
  transcript: string;
}) {
  const transcript = input.transcript.trim();
  if (!transcript) {
    throw new Error("Enter a rehearsal transcript before routing the turn.");
  }
  return {
    realtimeSessionId: input.realtimeSessionId,
    transcript,
    modality: "voice" as const,
    topic: "voice rehearsal to source-backed content",
    targetFormats: [...REHEARSAL_TARGET_FORMATS],
    routeTurn: true,
    metadata: {
      input_surface: "voice_runtime_transcript_rehearsal",
      provider_backed_realtime: false,
      rehearsal_only: true
    }
  };
}
