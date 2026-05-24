import type { RunCreateInput } from "../api/types";

export const DEFAULT_LIVE_VOICE_RUN_GOAL =
  "Create source-backed social content from my live voice session.";

export type VoiceRunProvider = "openrouter_livekit" | "local_rehearsal";

export type VoiceRunCreateInput = RunCreateInput & {
  input_mode: "voice";
  initial_context: {
    input_surface: "live_voice_panel";
    voice_provider: VoiceRunProvider;
    provider_backed_realtime: boolean;
    voice_first: true;
    audio_understanding_model: "deepseek/deepseek-v4-flash" | null;
    tts_model: "hexgrad/Kokoro-82M" | null;
    rehearsal_only: boolean;
  };
};

export function buildVoiceRunCreateInput(
  goal: string,
  provider: VoiceRunProvider = "openrouter_livekit"
): VoiceRunCreateInput {
  const trimmedGoal = goal.trim();
  const providerBackedRealtime = provider === "openrouter_livekit";
  return {
    goal: trimmedGoal || DEFAULT_LIVE_VOICE_RUN_GOAL,
    input_mode: "voice",
    initial_context: {
      input_surface: "live_voice_panel",
      voice_provider: provider,
      provider_backed_realtime: providerBackedRealtime,
      voice_first: true,
      audio_understanding_model: providerBackedRealtime ? "deepseek/deepseek-v4-flash" : null,
      tts_model: providerBackedRealtime ? "hexgrad/Kokoro-82M" : null,
      rehearsal_only: !providerBackedRealtime
    }
  };
}
