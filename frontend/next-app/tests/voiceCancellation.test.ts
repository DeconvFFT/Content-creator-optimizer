import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  cancellationProofFromVoiceAgentEvent,
  failedCancellationProofFromControlError,
  IDLE_CANCELLATION_PROOF,
  requestedCancellationProof
} from "../lib/voice/cancellation";

test("requested cancellation proof records the control event", () => {
  const proof = requestedCancellationProof(42);

  assert.equal(proof.status, "requested");
  assert.equal(proof.label, "Requested");
  assert.equal(
    proof.summary,
    "Interrupt control was recorded; waiting for runtime cancellation acknowledgement."
  );
  assert.deepEqual(proof.evidence, ["Control event: #42"]);
});

test("voice-edge cancellation ack extracts nested runtime actions", () => {
  const proof = cancellationProofFromVoiceAgentEvent(
    IDLE_CANCELLATION_PROOF,
    "voice_edge_cancellation_acknowledged",
    {
      voice_edge_event: {
        cancellation: {
          response_id: "response-1",
          reason: "barge-in detected",
          drop_outbound_audio: true,
          cancel_gemma: true,
          clear_kokoro_buffers: true,
          stop_livekit_audio: true
        }
      }
    }
  );

  assert.equal(proof.status, "edge_acknowledged");
  assert.equal(proof.label, "Edge ack");
  assert.deepEqual(proof.evidence, [
    "Response: response-1",
    "Reason: barge-in detected",
    "Gemma: cancel acknowledged",
    "Kokoro: buffer clear acknowledged",
    "LiveKit: output stop acknowledged"
  ]);
});

test("Gemma Kokoro cancellation event confirms full output stop", () => {
  const proof = cancellationProofFromVoiceAgentEvent(
    requestedCancellationProof(),
    "gemma_kokoro_voice_turn_cancelled",
    {
      response_id: "response-2",
      reason: "creator interrupted",
      cancel_gemma: true,
      clear_kokoro_buffers: true,
      stop_livekit_audio: true
    }
  );

  assert.equal(proof.status, "stopped");
  assert.equal(proof.label, "Stopped");
  assert.equal(
    proof.summary,
    "Gemma cancellation, Kokoro buffer clearing, and LiveKit audio stop were acknowledged."
  );
  assert.deepEqual(proof.evidence, [
    "Response: response-2",
    "Reason: creator interrupted",
    "Gemma: cancel acknowledged",
    "Kokoro: buffer clear acknowledged",
    "LiveKit: output stop acknowledged"
  ]);
});

test("manual agent interrupt ack waits for final stop confirmation", () => {
  const proof = cancellationProofFromVoiceAgentEvent(
    requestedCancellationProof(),
    "voice_manual_interrupt_received",
    {
      response_id: "response-3",
      reason: "creator interrupted",
      cancel_gemma: true,
      clear_kokoro_buffers: true,
      stop_livekit_audio: true,
      canceled: true
    }
  );

  assert.equal(proof.status, "agent_acknowledged");
  assert.equal(proof.label, "Agent ack");
  assert.deepEqual(proof.evidence, [
    "Response: response-3",
    "Reason: creator interrupted",
    "Gemma: cancel acknowledged",
    "Kokoro: buffer clear acknowledged",
    "LiveKit: output stop acknowledged"
  ]);
});

test("manual interrupt without active response resolves as no active output", () => {
  const proof = cancellationProofFromVoiceAgentEvent(
    requestedCancellationProof(),
    "voice_interrupt_no_active_response",
    {
      reason: "creator interrupted",
      canceled: false
    }
  );

  assert.equal(proof.status, "stopped");
  assert.equal(proof.label, "No active response");
  assert.deepEqual(proof.evidence, ["Reason: creator interrupted"]);
});

test("control failure does not downgrade acknowledged cancellation proof", () => {
  const acknowledged = cancellationProofFromVoiceAgentEvent(
    requestedCancellationProof(),
    "voice_edge_cancellation_acknowledged",
    {
      cancellation: {
        response_id: "response-1",
        reason: "barge-in detected",
        cancel_gemma: true,
        clear_kokoro_buffers: true,
        drop_outbound_audio_packets: true
      }
    }
  );
  const proof = failedCancellationProofFromControlError(acknowledged, "network failed");

  assert.equal(proof.status, "edge_acknowledged");
  assert.deepEqual(proof.evidence, [
    "Response: response-1",
    "Reason: barge-in detected",
    "Gemma: cancel acknowledged",
    "Kokoro: buffer clear acknowledged",
    "LiveKit: output stop acknowledged"
  ]);
});

test("control failure marks only pending requested cancellation as failed", () => {
  const proof = failedCancellationProofFromControlError(
    requestedCancellationProof(),
    "network failed"
  );

  assert.equal(proof.status, "failed");
  assert.deepEqual(proof.evidence, ["network failed"]);
});

test("unrelated events keep the current cancellation proof", () => {
  const current = requestedCancellationProof();
  const proof = cancellationProofFromVoiceAgentEvent(current, "assistant_text_delta", {});

  assert.equal(proof, current);
});

test("live voice interrupt and stop controls have synchronous single-flight guards", () => {
  const panelSource = readFileSync(
    join(process.cwd(), "components/voice/RealtimeVoicePanel.tsx"),
    "utf8"
  );
  const interruptSource =
    panelSource.match(/async function handleInterrupt\(\)[\s\S]*?\n  async function handleToggleMicrophone/)?.[0] ?? "";
  const stopSource =
    panelSource.match(/async function handleStop\(\)[\s\S]*?\n  async function handleVoiceSmoke/)?.[0] ?? "";

  assert.match(panelSource, /const interruptControlInFlightRef = useRef\(false\)/);
  assert.match(panelSource, /const stopActionInFlightRef = useRef<number \| null>\(null\)/);
  assert.match(
    interruptSource,
    /if \(!liveSession \|\| interruptControlInFlightRef\.current \|\| status !== "ready"\)/
  );
  assert.match(
    interruptSource,
    /activeRealtimeSessionIdRef\.current === interruptSessionId/
  );
  assert.match(interruptSource, /if \(!isCurrentInterrupt\(\)\) \{\s+return;\s+\}/);
  assert.match(
    interruptSource,
    /interruptControlInFlightRef\.current = true;[\s\S]*?runtimeAtInterrupt\?\.clearRemoteAudio/
  );
  assert.match(
    interruptSource,
    /finally \{[\s\S]*?interruptControlInFlightRef\.current = false/
  );
  assert.match(stopSource, /if \(stopActionInFlightRef\.current !== null\)/);
  assert.match(stopSource, /onVoiceRunMutationStart\?\.\("Stopping voice session"\)/);
  assert.match(stopSource, /onVoiceRunMutationFinish\?\.\(parentMutationSnapshot\)/);
  assert.match(
    stopSource,
    /stopActionInFlightRef\.current = stopActionToken;[\s\S]*?setStatus\("stopping"\)/
  );
  assert.match(stopSource, /finally \{[\s\S]*?stopActionInFlightRef\.current = null/);
  const stopParentGate = stopSource.indexOf('onVoiceRunMutationStart?.("Stopping voice session")');
  const stopInFlightOwner = stopSource.indexOf("stopActionInFlightRef.current = stopActionToken");
  const stopStatus = stopSource.indexOf('setStatus("stopping")');
  const stopEndSession = stopSource.indexOf("await endRealtimeSession({");
  const stopParentFinish = stopSource.indexOf("onVoiceRunMutationFinish?.(parentMutationSnapshot)");

  assert.notEqual(stopParentGate, -1);
  assert.notEqual(stopInFlightOwner, -1);
  assert.notEqual(stopStatus, -1);
  assert.notEqual(stopEndSession, -1);
  assert.notEqual(stopParentFinish, -1);
  assert.ok(stopParentGate < stopInFlightOwner);
  assert.ok(stopInFlightOwner < stopStatus);
  assert.ok(stopStatus < stopEndSession);
  assert.ok(stopEndSession < stopParentFinish);
});
