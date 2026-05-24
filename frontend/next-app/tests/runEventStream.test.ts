import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRunEventStreamUrl,
  consumeRunEventStream,
  latestRunEventId,
  mergeRecentRunEvents,
  parseSseFrames,
  runEventFromSseFrame
} from "../lib/state/runEventStream";
import type { RunEvent } from "../lib/api/types";

const schedulerEvent: RunEvent = {
  event_id: 12,
  run_id: "run-1",
  event_type: "worker_scheduler_pass_completed",
  actor: "agent-harness-engineer",
  payload: {
    idle: true,
    idle_reason: "no_due_profiles"
  },
  created_at: "2026-05-18T12:00:00Z"
};

test("run event stream parser handles custom event names and heartbeats", () => {
  const text = [
    "id: 12",
    "event: worker_scheduler_pass_completed",
    `data: ${JSON.stringify(schedulerEvent)}`,
    "",
    "event: heartbeat",
    'data: {"status":"connected"}',
    "",
    ""
  ].join("\n");

  const parsed = parseSseFrames(text, { final: true });
  const events = parsed.frames
    .map(runEventFromSseFrame)
    .filter((event): event is RunEvent => event !== null);

  assert.equal(parsed.remainder, "");
  assert.equal(events.length, 1);
  assert.deepEqual(events[0], schedulerEvent);
});

test("run event stream merge dedupes ids and keeps latest bounded events", () => {
  const oldEvent = { ...schedulerEvent, event_id: 10, event_type: "old_event" };
  const replaced = { ...schedulerEvent, event_id: 12, event_type: "older_shape" };
  const newer = { ...schedulerEvent, event_id: 14, event_type: "newer_event" };

  const merged = mergeRecentRunEvents([oldEvent, replaced], [schedulerEvent, newer], 2);

  assert.deepEqual(
    merged.map((event) => [event.event_id, event.event_type]),
    [
      [12, "worker_scheduler_pass_completed"],
      [14, "newer_event"]
    ]
  );
  assert.equal(latestRunEventId(merged), 14);
});

test("run event stream consumer reads fetch SSE bodies without EventSource", async () => {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode("id: 12\nevent: worker_scheduler_pass_completed\n"));
      controller.enqueue(encoder.encode(`data: ${JSON.stringify(schedulerEvent)}\n\n`));
      controller.close();
    }
  });
  const seenUrls: string[] = [];
  const seenEvents: RunEvent[] = [];
  let opened = false;
  const fetchImpl: typeof fetch = async (url) => {
    seenUrls.push(String(url));
    return new Response(body, {
      status: 200,
      headers: { "content-type": "text/event-stream" }
    });
  };

  await consumeRunEventStream({
    runId: "run-1",
    afterEventId: 9,
    fetchImpl,
    onOpen: () => {
      opened = true;
    },
    onEvent: (event) => seenEvents.push(event)
  });

  assert.equal(opened, true);
  assert.deepEqual(seenUrls, [buildRunEventStreamUrl("run-1", 9)]);
  assert.deepEqual(seenEvents, [schedulerEvent]);
});
