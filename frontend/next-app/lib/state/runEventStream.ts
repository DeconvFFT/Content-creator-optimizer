import type { RunEvent, UUID } from "@/lib/api/types";

export type RunEventStreamStatus = "idle" | "connecting" | "live" | "failed";

type SseFrame = {
  id?: string;
  event?: string;
  data: string;
};

type ConsumeRunEventStreamInput = {
  runId: UUID;
  afterEventId?: number;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
  onOpen?: () => void;
  onEvent: (event: RunEvent) => void;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

export function buildRunEventStreamUrl(runId: UUID, afterEventId?: number) {
  const params = new URLSearchParams();
  if (typeof afterEventId === "number" && Number.isFinite(afterEventId)) {
    params.set("after_event_id", String(Math.max(0, Math.floor(afterEventId))));
  }
  const query = params.toString();
  return `${API_BASE_URL}/api/runs/${encodeURIComponent(runId)}/events/stream${query ? `?${query}` : ""}`;
}

export function latestRunEventId(events: RunEvent[]) {
  return events.reduce((latest, event) => Math.max(latest, event.event_id ?? 0), 0);
}

export function mergeRecentRunEvents(
  existing: RunEvent[],
  incoming: RunEvent[],
  limit = 100
) {
  const byId = new Map<number, RunEvent>();
  for (const event of existing) {
    byId.set(event.event_id, event);
  }
  for (const event of incoming) {
    byId.set(event.event_id, event);
  }
  return [...byId.values()]
    .sort((left, right) => left.event_id - right.event_id)
    .slice(-limit);
}

export function parseSseFrames(
  text: string,
  { final = false }: { final?: boolean } = {}
): { frames: SseFrame[]; remainder: string } {
  const normalized = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const parts = normalized.split("\n\n");
  const remainder = final ? "" : parts.pop() ?? "";
  const candidateFrames = final ? parts : parts;
  return {
    frames: candidateFrames
      .map(parseSseFrame)
      .filter((frame): frame is SseFrame => frame !== null),
    remainder
  };
}

export function runEventFromSseFrame(frame: SseFrame): RunEvent | null {
  if (frame.event === "heartbeat") {
    return null;
  }
  const payload = JSON.parse(frame.data) as Partial<RunEvent>;
  if (
    typeof payload.event_id !== "number" ||
    typeof payload.run_id !== "string" ||
    typeof payload.event_type !== "string" ||
    typeof payload.actor !== "string" ||
    typeof payload.created_at !== "string"
  ) {
    return null;
  }
  return {
    event_id: payload.event_id,
    run_id: payload.run_id,
    event_type: payload.event_type,
    actor: payload.actor,
    payload: payload.payload ?? {},
    created_at: payload.created_at
  };
}

export async function consumeRunEventStream({
  runId,
  afterEventId,
  signal,
  fetchImpl = fetch,
  onOpen,
  onEvent
}: ConsumeRunEventStreamInput) {
  const response = await fetchImpl(buildRunEventStreamUrl(runId, afterEventId), {
    headers: { Accept: "text/event-stream" },
    signal
  });
  if (!response.ok) {
    throw new Error(`Run event stream failed with HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error("Run event stream did not provide a readable body.");
  }
  onOpen?.();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    const parsed = parseSseFrames(buffer + decoder.decode(value, { stream: true }));
    buffer = parsed.remainder;
    for (const frame of parsed.frames) {
      const event = runEventFromSseFrame(frame);
      if (event) {
        onEvent(event);
      }
    }
  }
  const parsed = parseSseFrames(buffer + decoder.decode(), { final: true });
  for (const frame of parsed.frames) {
    const event = runEventFromSseFrame(frame);
    if (event) {
      onEvent(event);
    }
  }
}

function parseSseFrame(rawFrame: string): SseFrame | null {
  const lines = rawFrame.split("\n");
  const dataLines: string[] = [];
  const frame: Omit<SseFrame, "data"> & { data?: string } = {};
  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    const separatorIndex = line.indexOf(":");
    const field = separatorIndex >= 0 ? line.slice(0, separatorIndex) : line;
    const rawValue = separatorIndex >= 0 ? line.slice(separatorIndex + 1) : "";
    const value = rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue;
    if (field === "id") {
      frame.id = value;
    } else if (field === "event") {
      frame.event = value;
    } else if (field === "data") {
      dataLines.push(value);
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return {
    ...frame,
    data: dataLines.join("\n")
  };
}
