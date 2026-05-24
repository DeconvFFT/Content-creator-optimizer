"use client";

import { Room, RoomEvent, Track } from "livekit-client";
import type { RemoteParticipant, RemoteTrack, RoomConnectOptions } from "livekit-client";
import type { RealtimeSessionCreateResult } from "@/lib/api/types";
import {
  buildLiveTextTurnPayload,
  LIVEKIT_AGENT_CONTROL_TOPIC,
  newLiveTextTurnId
} from "@/lib/voice/liveTextTurn";

export type LiveKitRuntimeEvent = {
  label: string;
  detail?: string;
  tone?: "info" | "good" | "warn" | "bad";
};

export type LiveKitRuntime = {
  room: Room;
  roomName: string;
  participantIdentity: string;
  agentIdentity?: string | null;
  probeAgentPresence: () => Promise<string>;
  interruptAgent: (input?: {
    reason?: string;
    interruptedResponseId?: string | null;
    controlEventId?: number | null;
  }) => Promise<string>;
  sendTranscriptTurn: (input: {
    transcript: string;
    voice?: string | null;
  }) => Promise<string>;
  setMicrophonePublishing: (enabled: boolean) => Promise<boolean>;
  clearRemoteAudio: () => void;
  disconnect: () => Promise<void>;
};

export type LiveKitJoinResult =
  | {
      status: "joined";
      runtime: LiveKitRuntime;
      message: string;
    }
  | {
      status: "blocked" | "failed";
      message: string;
    };

type LiveKitJoinOptions = {
  audioElementRoot?: HTMLElement | null;
  enableMicrophone?: boolean;
  onEvent?: (event: LiveKitRuntimeEvent) => void;
  onMicrophonePublishingChanged?: (publishing: boolean) => void;
  onAgentEvent?: (event: {
    event_type: string;
    payload: Record<string, unknown>;
    created_at?: string;
  }) => void | Promise<void>;
};

type RawAgentVoiceEvent = {
  event_type?: string;
  voice_agent_event_uid?: string;
  payload?: Record<string, unknown>;
  created_at?: string;
  [key: string]: unknown;
};

function transportBlocked(message: string): LiveKitJoinResult {
  return { status: "blocked", message };
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unknown LiveKit connection error";
}

function normalizeAgentVoiceEvent(event: RawAgentVoiceEvent) {
  if (!event.event_type) {
    return null;
  }
  const voiceAgentEventUid =
    typeof event.voice_agent_event_uid === "string" && event.voice_agent_event_uid.trim()
      ? event.voice_agent_event_uid
      : null;
  if (event.payload && typeof event.payload === "object") {
    return {
      event_type: event.event_type,
      payload: voiceAgentEventUid
        ? { voice_agent_event_uid: voiceAgentEventUid, ...event.payload }
        : event.payload,
      created_at: event.created_at
    };
  }
  const { event_type, voice_agent_event_uid: _voiceAgentEventUid, created_at, ...payload } = event;
  return {
    event_type,
    payload: voiceAgentEventUid
      ? { voice_agent_event_uid: voiceAgentEventUid, ...payload }
      : payload,
    created_at
  };
}

function newRuntimeMessageId(prefix: string) {
  const suffix =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random()}`;
  return `${prefix}-${suffix}`;
}

export async function joinLiveKitRuntime(
  session: RealtimeSessionCreateResult,
  options: LiveKitJoinOptions = {}
): Promise<LiveKitJoinResult> {
  const transport = session.transport;
  if (!transport || transport.framework !== "livekit") {
    return transportBlocked("The realtime session did not return a LiveKit transport grant.");
  }
  if (!transport.url) {
    return transportBlocked("LiveKit URL is missing. Configure GEMMA4_REALTIME_LIVEKIT_URL.");
  }
  if (!transport.token) {
    return transportBlocked("LiveKit join token is missing. Configure LIVEKIT_API_KEY and LIVEKIT_API_SECRET.");
  }
  if (transport.token_persisted) {
    return transportBlocked("LiveKit token was marked persisted; refusing to join with an unsafe grant.");
  }

  const room = new Room({
    adaptiveStream: true,
    dynacast: true
  });
  const attachedAudioElements = new Set<HTMLMediaElement>();
  const onEvent = options.onEvent;

  const emitMicrophonePublishing = (publishing: boolean) => {
    options.onMicrophonePublishingChanged?.(publishing);
    onEvent?.({
      label: publishing ? "Microphone publishing enabled" : "Microphone publishing disabled",
      detail: room.localParticipant.identity,
      tone: publishing ? "good" : "info"
    });
  };

  const syncLocalMicrophonePublication = (publishing: boolean) => {
    options.onMicrophonePublishingChanged?.(publishing);
  };

  const clearRemoteAudio = () => {
    attachedAudioElements.forEach((element) => {
      element.pause();
      element.srcObject = null;
      element.remove();
    });
    attachedAudioElements.clear();
  };

  const attachRemoteAudio = (track: RemoteTrack, participant: RemoteParticipant) => {
    if (track.kind !== Track.Kind.Audio) {
      return;
    }
    const element = track.attach();
    element.autoplay = true;
    element.controls = false;
    element.dataset.livekitRemoteAudio = session.realtime_session_id;
    element.dataset.livekitParticipant = participant.identity;
    element.style.display = "none";
    attachedAudioElements.add(element);
    options.audioElementRoot?.appendChild(element);
    onEvent?.({
      label: "Agent audio subscribed",
      detail: `Remote audio track from ${participant.identity}`,
      tone: "good"
    });
  };

  room.on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
    attachRemoteAudio(track, participant);
  });
  room.on(RoomEvent.ConnectionStateChanged, (state) => {
    onEvent?.({
      label: "LiveKit connection state",
      detail: state,
      tone: state === "connected" ? "good" : "info"
    });
  });
  room.on(RoomEvent.Reconnecting, () => {
    onEvent?.({ label: "LiveKit reconnecting", tone: "warn" });
  });
  room.on(RoomEvent.DataReceived, (payload, participant, _kind, topic) => {
    if (topic !== "agent.voice.event") {
      return;
    }
    try {
      const text = new TextDecoder().decode(payload);
      const event = normalizeAgentVoiceEvent(JSON.parse(text) as RawAgentVoiceEvent);
      if (!event) {
        return;
      }
      onEvent?.({
        label: event.event_type,
        detail: participant?.identity ? `From ${participant.identity}` : undefined,
        tone: "info"
      });
      void options.onAgentEvent?.({
        event_type: event.event_type,
        payload: {
          ...event.payload,
          livekit_sender_identity: participant?.identity ?? null,
          livekit_topic: topic ?? null
        },
        created_at: event.created_at
      });
    } catch (error) {
      onEvent?.({
        label: "Voice event parse failed",
        detail: errorMessage(error),
        tone: "warn"
      });
    }
  });
  room.on(RoomEvent.Disconnected, () => {
    clearRemoteAudio();
    syncLocalMicrophonePublication(false);
    onEvent?.({ label: "LiveKit disconnected", tone: "info" });
  });
  room.on(RoomEvent.LocalTrackPublished, (publication) => {
    if (publication.kind === Track.Kind.Audio) {
      syncLocalMicrophonePublication(true);
    }
  });
  room.on(RoomEvent.LocalTrackUnpublished, (publication) => {
    if (publication.kind === Track.Kind.Audio) {
      syncLocalMicrophonePublication(false);
    }
  });
  room.on(RoomEvent.TrackMuted, (publication, participant) => {
    if (participant.identity === room.localParticipant.identity && publication.kind === Track.Kind.Audio) {
      syncLocalMicrophonePublication(false);
    }
  });
  room.on(RoomEvent.TrackUnmuted, (publication, participant) => {
    if (participant.identity === room.localParticipant.identity && publication.kind === Track.Kind.Audio) {
      syncLocalMicrophonePublication(true);
    }
  });

  try {
    const connectOptions: RoomConnectOptions = { autoSubscribe: true };
    await room.connect(transport.url, transport.token, connectOptions);
    if (options.enableMicrophone ?? true) {
      await room.localParticipant.setMicrophoneEnabled(true);
      emitMicrophonePublishing(true);
    }
  } catch (error) {
    clearRemoteAudio();
    await room.disconnect(false).catch(() => undefined);
    return {
      status: "failed",
      message: `LiveKit room join failed: ${errorMessage(error)}`
    };
  }

  const controlBindingToken =
    typeof transport.metadata?.control_binding_token === "string"
      ? transport.metadata.control_binding_token
      : null;
  const runtime: LiveKitRuntime = {
    room,
    roomName: transport.room_name ?? room.name,
    participantIdentity: transport.participant_identity ?? room.localParticipant.identity,
    agentIdentity: transport.agent_identity ?? null,
    probeAgentPresence: async () => {
      const probeId = newRuntimeMessageId("voice-presence-probe");
      await room.localParticipant.publishData(
        new TextEncoder().encode(
          JSON.stringify({
            type: "voice_agent_presence_probe",
            probe_id: probeId,
            run_id: session.run_id,
            realtime_session_id: session.realtime_session_id,
            room_name: transport.room_name ?? room.name,
            expected_agent_identity: transport.agent_identity ?? null,
            control_binding_token: controlBindingToken
          })
        ),
        {
          reliable: true,
          topic: LIVEKIT_AGENT_CONTROL_TOPIC
        }
      );
      return probeId;
    },
    interruptAgent: async (input = {}) => {
      const interruptId = newRuntimeMessageId("voice-interrupt");
      const interruptedResponseId = input.interruptedResponseId ?? null;
      await room.localParticipant.publishData(
        new TextEncoder().encode(
          JSON.stringify({
            type: "voice_interrupt",
            interrupt_id: interruptId,
            run_id: session.run_id,
            realtime_session_id: session.realtime_session_id,
            room_name: transport.room_name ?? room.name,
            expected_agent_identity: transport.agent_identity ?? null,
            control_binding_token: controlBindingToken,
            reason: input.reason ?? "Creator interrupted the Gemma/Kokoro voice response.",
            response_id: interruptedResponseId,
            interrupted_response_id: interruptedResponseId,
            control_event_id: input.controlEventId ?? null,
            drop_outbound_audio_packets: true,
            cancel_gemma: true,
            clear_kokoro_buffers: true,
            stop_livekit_audio: true,
            required_runtime_actions: [
              "drop_outbound_audio_packets",
              "cancel_gemma_inference",
              "clear_kokoro_tts_buffer",
              "stop_livekit_audio"
            ]
          })
        ),
        {
          reliable: true,
          topic: LIVEKIT_AGENT_CONTROL_TOPIC
        }
      );
      onEvent?.({
        label: "Agent interrupt control sent",
        detail: interruptId,
        tone: "warn"
      });
      return interruptId;
    },
    sendTranscriptTurn: async (input) => {
      const turnId = newLiveTextTurnId();
      const payload = buildLiveTextTurnPayload({
        turnId,
        runId: session.run_id,
        realtimeSessionId: session.realtime_session_id,
        roomName: transport.room_name ?? room.name,
        expectedAgentIdentity: transport.agent_identity ?? null,
        controlBindingToken,
        transcript: input.transcript,
        voice: input.voice ?? null
      });
      await room.localParticipant.publishData(
        new TextEncoder().encode(JSON.stringify(payload)),
        {
          reliable: true,
          topic: LIVEKIT_AGENT_CONTROL_TOPIC
        }
      );
      onEvent?.({
        label: "Live text turn sent",
        detail: turnId,
        tone: "info"
      });
      return turnId;
    },
    setMicrophonePublishing: async (enabled) => {
      await room.localParticipant.setMicrophoneEnabled(enabled);
      emitMicrophonePublishing(enabled);
      return enabled;
    },
    clearRemoteAudio,
    disconnect: async () => {
      clearRemoteAudio();
      await room.disconnect(true);
    }
  };

  return {
    status: "joined",
    runtime,
    message: `Joined LiveKit room ${runtime.roomName} as ${runtime.participantIdentity}.`
  };
}
