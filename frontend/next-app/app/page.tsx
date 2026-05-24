"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ActivityPanel } from "@/components/run/ActivityPanel";
import { Composer, type ComposerSubmit } from "@/components/composer/Composer";
import { ConversationPanel } from "@/components/conversation/ConversationPanel";
import { DraftBoard, isContentArtifact } from "@/components/drafts/DraftBoard";
import { ProductionPanel, type ProductionStatus } from "@/components/production/ProductionPanel";
import { RunRail } from "@/components/run/RunRail";
import { SourcePanel } from "@/components/sources/SourcePanel";
import { RealtimeVoicePanel } from "@/components/voice/RealtimeVoicePanel";
import {
  beginRunAction,
  clearBusyForOwnedRun,
  clearBusyForOwnedRunSnapshot,
  finishRunAction,
  invalidateRunAction,
  isRunOwnerCurrent,
  isRunVersionedActionCurrent,
  isRunVersionCurrent
} from "@/lib/state/runOwnership";
import {
  isRunMutationInFlight as isRunMutationGateInFlight,
  isWorkPlanPlanningInFlight as isWorkPlanGatePlanningInFlight
} from "@/lib/state/runMutationGate";
import { buildAutopilotAutoWakeDecision } from "@/lib/state/autopilotAutoWake";
import { appendCreatorStatusDetail, creatorStatusText } from "@/lib/state/creatorStatusCopy";
import {
  nextWorkerSchedulerStatusToken,
  selectedWorkerSchedulerProfile,
  shouldCommitWorkerSchedulerStatus
} from "@/lib/state/workerSchedulerProcess";
import { buildContentReadinessSnapshot } from "@/lib/state/contentReadiness";
import {
  buildRunEventStreamSummary,
  buildStreamedRunRefreshSummary,
  shouldRefreshRunForStreamEvent,
  STREAMED_RUN_REFRESH_DEBOUNCE_MS
} from "@/lib/state/runEventRefresh";
import {
  consumeRunEventStream,
  latestRunEventId,
  mergeRecentRunEvents,
  type RunEventStreamStatus
} from "@/lib/state/runEventStream";
import {
  buildSourceRefreshCycleInput,
  buildSourceRefreshMessage,
  hasRunnableWebResearchTask,
  sourceRefreshActivitySummary
} from "@/lib/state/sourceResearch";
import {
  workPlanMaterializationInput,
  workPlanPostRunRefreshInput,
  workPlanRunnableAgentIds
} from "@/lib/state/workPlan";
import {
  authorizeAgentMessageRetry,
  buildGrowthPackage,
  buildMediaProductionPlan,
  buildRunWorkPlan,
  checkPublishReadiness,
  createRun,
  getRunContext,
  getWorkerSchedulerProcessStatus,
  heartbeatWorkerProfile,
  launchAutopilot,
  listWorkerProfiles,
  resolveFeedback,
  routeConversationTurn,
  runAgentWorkerCycle,
  runWorkerScheduler,
  sendAgentMessage,
  startWorkerSchedulerProcess,
  stopWorkerProfile,
  stopWorkerSchedulerProcess,
  submitRevision
} from "@/lib/api/client";
import { buildVoiceRunCreateInput, type VoiceRunProvider } from "@/lib/voice/voiceRun";
import type {
  AgentMessage,
  ArtifactRecord,
  ClaimRecord,
  FeedbackItem,
  RealtimeSessionCreateResult,
  RunContextPacket,
  RunEvent,
  RunWorkPlanResult,
  SourceRecord,
  UUID,
  WorkerProfile,
  WorkerSchedulerProcessStatusResult
} from "@/lib/api/types";

const RUN_STORAGE_KEY = "all-about-llms-next-run-id";
const ACTIVE_AUTOPILOT_STATUSES = new Set(["active", "running", "started"]);
const AUTOPILOT_AUTO_WAKE_INTERVAL_MS = 5_000;

type AppState = {
  runId?: UUID;
  context?: RunContextPacket;
  workerProfiles?: WorkerProfile[];
  workerSchedulerProcess?: WorkerSchedulerProcessStatusResult | null;
  realtimeSession?: RealtimeSessionCreateResult;
  realtimeSessionKey?: string;
  workPlan?: RunWorkPlanResult;
  selectedArtifactIds: UUID[];
  productionStatus?: ProductionStatus;
  busyLabel?: string;
  error?: string;
  lastSummary?: string;
  useGemmaAgentCycle?: boolean;
  autopilotAutoWakeEnabled?: boolean;
  autopilotAutoWakeSummary?: string;
  runEventStreamStatus?: RunEventStreamStatus;
  runEventStreamSummary?: string;
};

type AgentContinuationOptions = {
  agentIds?: string[];
  messageIds?: UUID[];
  continueMessageLineage?: boolean;
  maxTasksPerAgent?: number;
  maxRounds?: number;
  useGemma?: boolean | null;
};

type VoiceRunCreateOptions = {
  provider: VoiceRunProvider;
};

type VoiceRunMutationSnapshot = {
  runId: UUID;
  version: number;
  token: number;
};

type RefreshRunOptions = {
  silent?: boolean;
};

export default function HomePage() {
  const [state, setState] = useState<AppState>({
    selectedArtifactIds: [],
    useGemmaAgentCycle: false,
    autopilotAutoWakeEnabled: true
  });
  const [autopilotAutoWakeNow, setAutopilotAutoWakeNow] = useState(() => new Date());
  const [retryingMessageIds, setRetryingMessageIds] = useState<UUID[]>([]);
  const agentCycleInFlightRef = useRef(false);
  const retryInFlightMessageIdsRef = useRef<Set<UUID>>(new Set());
  const autopilotHeartbeatInFlightRef = useRef(false);
  const autopilotSchedulerInFlightRunsRef = useRef<Set<UUID>>(new Set());
  const autopilotAutoWakeLastKeyRef = useRef<string | null>(null);
  const workerSchedulerStatusTokenRef = useRef(0);
  const latestRunEventIdRef = useRef(0);
  const liveRunRefreshTimerRef = useRef<number | undefined>(undefined);
  const liveRunRefreshEventRef = useRef<RunEvent | undefined>(undefined);
  const voiceRunCreateInFlightRef = useRef(false);
  const composerSubmitGateRef = useRef({ inFlight: false, token: 0 });
  const sourceRefreshActionGateRef = useRef({ inFlight: false, token: 0 });
  const productionActionGateRef = useRef({ inFlight: false, token: 0 });
  const feedbackActionGateRef = useRef({ inFlight: false, token: 0 });
  const voiceSessionActionGateRef = useRef({ inFlight: false, token: 0 });
  const voiceProofActionGateRef = useRef({ inFlight: false, token: 0 });
  const autopilotActionGateRef = useRef({ inFlight: false, token: 0 });
  const localSchedulerActionGateRef = useRef({ inFlight: false, token: 0 });
  const workPlanActionGateRef = useRef({ inFlight: false, token: 0 });
  const runVersionRef = useRef(0);
  const activeRunIdRef = useRef<UUID | undefined>(undefined);

  const artifacts = state.context?.artifacts ?? [];
  const sources = state.context?.sources ?? [];
  const claims = state.context?.claims ?? [];
  const feedback = state.context?.feedback_items ?? [];
  const sourceEvidence = state.context?.source_evidence ?? [];
  const useGemmaAgentCycle = state.useGemmaAgentCycle ?? false;
  const autopilotAutoWakeEnabled = state.autopilotAutoWakeEnabled ?? true;

  useEffect(() => {
    let cancelled = false;
    const refreshWorkerSchedulerStatus = async () => {
      const statusToken = workerSchedulerStatusTokenRef.current;
      try {
        const result = await getWorkerSchedulerProcessStatus();
        if (
          !cancelled &&
          shouldCommitWorkerSchedulerStatus(statusToken, workerSchedulerStatusTokenRef.current)
        ) {
          setState((current) => ({
            ...current,
            workerSchedulerProcess: result
          }));
        }
      } catch {
        if (
          !cancelled &&
          shouldCommitWorkerSchedulerStatus(statusToken, workerSchedulerStatusTokenRef.current)
        ) {
          setState((current) => ({
            ...current,
            workerSchedulerProcess: current.workerSchedulerProcess ?? null
          }));
        }
      }
    };
    void refreshWorkerSchedulerStatus();
    const intervalId = window.setInterval(refreshWorkerSchedulerStatus, 10_000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    activeRunIdRef.current = state.runId;
  }, [state.runId]);

  useEffect(() => {
    retryInFlightMessageIdsRef.current.clear();
    setRetryingMessageIds([]);
  }, [state.runId]);

  useEffect(() => {
    const intervalId = window.setInterval(
      () => setAutopilotAutoWakeNow(new Date()),
      AUTOPILOT_AUTO_WAKE_INTERVAL_MS
    );
    return () => window.clearInterval(intervalId);
  }, []);

  const clearBusyForRun = useCallback((
    runId?: UUID | null,
    expectedVersion?: number
  ) => {
    setState((current) => {
      if (expectedVersion !== undefined) {
        return clearBusyForOwnedRunSnapshot(
          current,
          { runId: runId ?? undefined, version: expectedVersion },
          runVersionRef.current
        );
      }
      return clearBusyForOwnedRun(current, runId);
    });
  }, []);

  const isActiveRunOwner = useCallback((runId: UUID, version: number) => (
    isRunOwnerCurrent({ runId, version }, activeRunIdRef.current, runVersionRef.current)
  ), []);

  const selectedArtifacts = useMemo(
    () =>
      artifacts.filter(
        (artifact) =>
          isContentArtifact(artifact) &&
          state.selectedArtifactIds.includes(artifact.artifact_id)
      ),
    [artifacts, state.selectedArtifactIds]
  );
  const contentReadiness = useMemo(
    () =>
      buildContentReadinessSnapshot({
        artifacts: artifacts as ArtifactRecord[],
        claims: claims as ClaimRecord[],
        feedback: feedback as FeedbackItem[],
        sourceEvidence
      }),
    [artifacts, claims, feedback, sourceEvidence]
  );

  function isWorkPlanPlanningInFlight() {
    return isWorkPlanGatePlanningInFlight(workPlanActionGateRef.current);
  }

  function isRunMutationInFlight(runId?: UUID) {
    return isRunMutationGateInFlight({
      composer: composerSubmitGateRef.current,
      sourceRefresh: sourceRefreshActionGateRef.current,
      production: productionActionGateRef.current,
      feedback: feedbackActionGateRef.current,
      voiceSession: voiceSessionActionGateRef.current,
      voiceProof: voiceProofActionGateRef.current,
      autopilot: autopilotActionGateRef.current,
      localScheduler: localSchedulerActionGateRef.current,
      agentCycleInFlight: agentCycleInFlightRef.current,
      autopilotHeartbeatInFlight: autopilotHeartbeatInFlightRef.current,
      autopilotSchedulerInFlightRunIds: autopilotSchedulerInFlightRunsRef.current
    }, runId);
  }

  function blockSameRunMutationIfBusy(runId?: UUID) {
    const error = isWorkPlanPlanningInFlight()
      ? "Planning next agent actions is already running."
      : isRunMutationInFlight(runId)
        ? "A run update is already in progress."
        : null;
    if (!error) {
      return false;
    }
    setState((current) => ({
      ...current,
      error
    }));
    return true;
  }

  function handleVoiceRunMutationStart(label: string): VoiceRunMutationSnapshot | undefined {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return undefined;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return undefined;
    }
    const token = beginRunAction(voiceSessionActionGateRef.current);
    if (token === undefined) {
      return undefined;
    }
    setState((current) => ({
      ...current,
      busyLabel: label,
      error: undefined
    }));
    return { runId, version: runVersion, token };
  }

  function handleVoiceRunMutationFinish(snapshot: VoiceRunMutationSnapshot) {
    finishRunAction(voiceSessionActionGateRef.current, snapshot.token);
    if (
      !isRunVersionedActionCurrent(
        snapshot,
        runVersionRef.current,
        voiceSessionActionGateRef.current.token
      ) ||
      !isActiveRunOwner(snapshot.runId, snapshot.version)
    ) {
      return;
    }
    clearBusyForRun(snapshot.runId, snapshot.version);
  }

  function handleVoiceProofMutationStart(label: string): VoiceRunMutationSnapshot | undefined {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return undefined;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return undefined;
    }
    const token = beginRunAction(voiceProofActionGateRef.current);
    if (token === undefined) {
      return undefined;
    }
    setState((current) => ({
      ...current,
      busyLabel: label,
      error: undefined
    }));
    return { runId, version: runVersion, token };
  }

  function handleVoiceProofMutationFinish(snapshot: VoiceRunMutationSnapshot) {
    finishRunAction(voiceProofActionGateRef.current, snapshot.token);
    if (
      !isRunVersionedActionCurrent(
        snapshot,
        runVersionRef.current,
        voiceProofActionGateRef.current.token
      ) ||
      !isActiveRunOwner(snapshot.runId, snapshot.version)
    ) {
      return;
    }
    clearBusyForRun(snapshot.runId, snapshot.version);
  }

  const refreshRun = useCallback(async (
    runId: UUID,
    summary?: string,
    expectedVersion?: number,
    options: RefreshRunOptions = {}
  ) => {
    const refreshVersion = expectedVersion ?? runVersionRef.current;
    const [context, workerProfiles] = await Promise.all([
      getRunContext(runId),
      listWorkerProfiles(runId)
    ]);
    if (!isRunVersionCurrent(refreshVersion, runVersionRef.current)) {
      if (!options.silent) {
        clearBusyForRun(runId, refreshVersion);
      }
      return;
    }
    latestRunEventIdRef.current = Math.max(
      latestRunEventIdRef.current,
      latestRunEventId(context.recent_events)
    );
    window.localStorage.setItem(RUN_STORAGE_KEY, runId);
    setState((current) => ({
      ...current,
      runId,
      context,
      workerProfiles,
      workPlan: current.workPlan?.run_id === runId ? current.workPlan : undefined,
      lastSummary: summary ?? current.lastSummary,
      busyLabel: options.silent ? current.busyLabel : undefined,
      error: options.silent ? current.error : undefined
    }));
  }, [clearBusyForRun]);

  useEffect(() => {
    const runId = state.runId;
    if (!runId) {
      latestRunEventIdRef.current = 0;
      return;
    }
    const streamVersion = runVersionRef.current;
    const controller = new AbortController();
    let stopped = false;
    let retryId: number | undefined;

    const connect = async () => {
      if (stopped || !isActiveRunOwner(runId, streamVersion)) {
        return;
      }
      setState((current) => current.runId === runId
        ? {
            ...current,
            runEventStreamStatus: "connecting",
            runEventStreamSummary: "Connecting live run events."
          }
        : current
      );
      try {
        await consumeRunEventStream({
          runId,
          afterEventId: latestRunEventIdRef.current || undefined,
          signal: controller.signal,
          onOpen: () => {
            if (!isActiveRunOwner(runId, streamVersion)) {
              return;
            }
            setState((current) => current.runId === runId
              ? {
                  ...current,
                  runEventStreamStatus: "live",
                  runEventStreamSummary: "Live run events connected."
                }
              : current
            );
          },
          onEvent: (event) => {
            if (!isActiveRunOwner(runId, streamVersion)) {
              return;
            }
            latestRunEventIdRef.current = Math.max(
              latestRunEventIdRef.current,
              event.event_id
            );
            setState((current) => {
              if (current.runId !== runId || !current.context) {
                return current;
              }
              return {
                ...current,
                context: {
                  ...current.context,
                  recent_events: mergeRecentRunEvents(
                    current.context.recent_events,
                    [event]
                  )
                },
                runEventStreamStatus: "live",
                runEventStreamSummary: buildRunEventStreamSummary(event)
              };
            });
            if (shouldRefreshRunForStreamEvent(event)) {
              liveRunRefreshEventRef.current = event;
              if (liveRunRefreshTimerRef.current) {
                window.clearTimeout(liveRunRefreshTimerRef.current);
              }
              liveRunRefreshTimerRef.current = window.setTimeout(() => {
                liveRunRefreshTimerRef.current = undefined;
                const refreshEvent = liveRunRefreshEventRef.current;
                if (!refreshEvent || !isActiveRunOwner(runId, streamVersion)) {
                  return;
                }
                void refreshRun(
                  runId,
                  buildStreamedRunRefreshSummary(refreshEvent),
                  streamVersion,
                  { silent: true }
                ).catch((error) => {
                  if (!isActiveRunOwner(runId, streamVersion)) {
                    return;
                  }
                  setState((current) => current.runId === runId
                    ? {
                        ...current,
                        runEventStreamStatus: "failed",
                        runEventStreamSummary: error instanceof Error
                          ? error.message
                          : "Live event context refresh failed."
                      }
                    : current
                  );
                });
              }, STREAMED_RUN_REFRESH_DEBOUNCE_MS);
            }
          }
        });
      } catch (error) {
        if (stopped || controller.signal.aborted || !isActiveRunOwner(runId, streamVersion)) {
          return;
        }
        setState((current) => current.runId === runId
          ? {
              ...current,
              runEventStreamStatus: "failed",
              runEventStreamSummary: error instanceof Error
                ? error.message
                : "Live run event stream disconnected."
            }
          : current
        );
      }
      if (!stopped && !controller.signal.aborted && isActiveRunOwner(runId, streamVersion)) {
        retryId = window.setTimeout(connect, 5_000);
      }
    };

    void connect();

    return () => {
      stopped = true;
      controller.abort();
      if (retryId) {
        window.clearTimeout(retryId);
      }
      if (liveRunRefreshTimerRef.current) {
        window.clearTimeout(liveRunRefreshTimerRef.current);
        liveRunRefreshTimerRef.current = undefined;
      }
    };
  }, [isActiveRunOwner, refreshRun, state.runId]);

  useEffect(() => {
    const runIdFromUrl = new URLSearchParams(window.location.search).get("runId");
    const savedRunId = runIdFromUrl ?? window.localStorage.getItem(RUN_STORAGE_KEY);
    if (!savedRunId) {
      return;
    }
    const restoreVersion = runVersionRef.current;
    setState((current) => ({ ...current, busyLabel: "Restoring last run" }));
    refreshRun(savedRunId, "Restored your last content run.", restoreVersion).catch((error) => {
      if (!isRunVersionCurrent(restoreVersion, runVersionRef.current)) {
        clearBusyForRun(savedRunId, restoreVersion);
        return;
      }
      window.localStorage.removeItem(RUN_STORAGE_KEY);
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not restore the last run."
      }));
    });
  }, [clearBusyForRun, refreshRun]);

  const runAgentCycleAndRefresh = useCallback(
    async (
      runId: UUID,
      reason = "Continued the specialist agent loop.",
      expectedVersion?: number,
      options: AgentContinuationOptions = {}
    ) => {
      const runVersion = expectedVersion ?? runVersionRef.current;
      const cycle = await runAgentWorkerCycle({
        runId,
        agentIds: options.agentIds,
        messageIds: options.messageIds,
        continueMessageLineage: options.continueMessageLineage,
        maxTasksPerAgent: options.maxTasksPerAgent ?? 3,
        maxRounds: options.maxRounds ?? 3,
        useGemma: options.useGemma ?? useGemmaAgentCycle
      });
      const activity =
        cycle.total_processed_tasks > 0
          ? `${reason} ${cycle.summary}`
          : `${reason} No pending agent tasks needed work.`;
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return cycle;
      }
      await refreshRun(runId, activity, runVersion);
      return cycle;
    },
    [clearBusyForRun, refreshRun, useGemmaAgentCycle]
  );

  const continueAgents = useCallback(
    async (
      runId: UUID,
      reason = "Continued the specialist agent loop.",
      expectedVersion?: number,
      options: AgentContinuationOptions = {}
    ) => {
      if (workPlanActionGateRef.current.inFlight) {
        throw new Error("Planning next agent actions is already running.");
      }
      if (agentCycleInFlightRef.current) {
        throw new Error("Agent continuation is already running.");
      }
      agentCycleInFlightRef.current = true;
      try {
        return await runAgentCycleAndRefresh(runId, reason, expectedVersion, options);
      } finally {
        agentCycleInFlightRef.current = false;
      }
    },
    [runAgentCycleAndRefresh]
  );

  async function handleCompose(input: ComposerSubmit) {
    if (blockSameRunMutationIfBusy(state.runId)) {
      return;
    }
    const composeToken = beginRunAction(composerSubmitGateRef.current);
    if (composeToken === undefined) {
      return;
    }
    const composeVersion = runVersionRef.current;
    const composeOwner = { version: composeVersion, token: composeToken };
    const isComposeOwnerCurrent = () => isRunVersionedActionCurrent(
      composeOwner,
      runVersionRef.current,
      composerSubmitGateRef.current.token
    );
    setState((current) => ({
      ...current,
      busyLabel: input.modality === "voice" ? "Routing voice turn" : "Generating source-backed drafts",
      error: undefined
    }));

    try {
      const result = await routeConversationTurn({
        run_id: state.runId ?? null,
        transcript: input.transcript,
        modality: input.modality,
        speaker: "user",
        topic: input.topic || null,
        target_artifact_ids: selectedArtifacts.map((artifact) => artifact.artifact_id),
        target_formats: input.targetFormats,
        intent: state.runId ? "auto" : "create_content",
        require_human_feedback: true,
        metadata: {
          frontend: "next-app",
          input_surface: input.modality === "voice" ? "browser_dictation_transcript" : "text_composer",
          provider_backed_realtime: false
        }
      });
      if (!isComposeOwnerCurrent()) {
        clearBusyForRun(state.runId, composeVersion);
        return;
      }
      if (result.task_message_ids.length > 0) {
        setState((current) => ({
          ...current,
          busyLabel: "Continuing specialist agents"
        }));
        try {
          await continueAgents(result.run_id, result.summary, composeVersion);
        } catch (cycleError) {
          await refreshRun(result.run_id, result.summary, composeVersion);
          if (!isComposeOwnerCurrent()) {
            clearBusyForRun(result.run_id, composeVersion);
            return;
          }
          setState((current) => ({
            ...current,
            busyLabel: undefined,
            error:
              cycleError instanceof Error
                ? cycleError.message
                : "The turn was saved, but the agent continuation failed."
          }));
        }
      } else {
        await refreshRun(result.run_id, result.summary, composeVersion);
      }
    } catch (error) {
      if (!isComposeOwnerCurrent()) {
        clearBusyForRun(state.runId, composeVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Request failed"
      }));
    } finally {
      finishRunAction(composerSubmitGateRef.current, composeToken);
    }
  }

  async function handleCreateVoiceRun(goal: string, options: VoiceRunCreateOptions) {
    if (voiceRunCreateInFlightRef.current) {
      return;
    }
    voiceRunCreateInFlightRef.current = true;
    invalidateRunAction(composerSubmitGateRef.current);
    invalidateRunAction(sourceRefreshActionGateRef.current);
    invalidateRunAction(productionActionGateRef.current);
    invalidateRunAction(feedbackActionGateRef.current);
    invalidateRunAction(voiceSessionActionGateRef.current);
    invalidateRunAction(voiceProofActionGateRef.current);
    invalidateRunAction(autopilotActionGateRef.current);
    invalidateRunAction(localSchedulerActionGateRef.current);
    invalidateRunAction(workPlanActionGateRef.current);
    const voiceRunVersion = runVersionRef.current + 1;
    runVersionRef.current = voiceRunVersion;
    activeRunIdRef.current = undefined;
    latestRunEventIdRef.current = 0;
    liveRunRefreshEventRef.current = undefined;
    if (liveRunRefreshTimerRef.current) {
      window.clearTimeout(liveRunRefreshTimerRef.current);
      liveRunRefreshTimerRef.current = undefined;
    }
    setState((current) => ({
      ...current,
      runId: undefined,
      context: undefined,
      workerProfiles: [],
      realtimeSession: undefined,
      realtimeSessionKey: undefined,
      productionStatus: undefined,
      workPlan: undefined,
      selectedArtifactIds: [],
      busyLabel: "Creating voice run",
      error: undefined
    }));

    try {
      const run = await createRun(buildVoiceRunCreateInput(goal, options.provider));
      if (!isRunVersionCurrent(voiceRunVersion, runVersionRef.current)) {
        clearBusyForRun(run.run_id, voiceRunVersion);
        return;
      }
      await refreshRun(
        run.run_id,
        "Created a voice-first run. Join Live Voice when setup is ready.",
        voiceRunVersion
      );
    } catch (error) {
      if (!isRunVersionCurrent(voiceRunVersion, runVersionRef.current)) {
        clearBusyForRun(undefined, voiceRunVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not create a voice run."
      }));
    } finally {
      voiceRunCreateInFlightRef.current = false;
    }
  }

  async function handleRefresh() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    setState((current) => ({
      ...current,
      busyLabel: "Refreshing run state",
      error: undefined
    }));
    try {
      await refreshRun(runId, "Run state refreshed.", runVersion);
    } catch (error) {
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Refresh failed"
      }));
    }
  }

  const handleVoiceFollowupReady = useCallback(
    async (followupTaskMessageId: UUID, options: AgentContinuationOptions = {}) => {
      const runId = state.runId;
      const runVersion = runVersionRef.current;
      if (!runId || !isActiveRunOwner(runId, runVersion)) {
        return;
      }
      if (blockSameRunMutationIfBusy(runId)) {
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: "Continuing live voice agents",
        error: undefined
      }));
      const isProviderRecovery =
        options.agentIds?.includes("inference-systems-engineer") &&
        options.agentIds?.includes("observability-agent") &&
        options.agentIds?.includes("agent-harness-engineer");
      try {
        await continueAgents(
          runId,
          isProviderRecovery
            ? `Continued provider-failure recovery ${followupTaskMessageId.slice(0, 8)}.`
            : `Continued live voice follow-up ${followupTaskMessageId.slice(0, 8)}.`,
          runVersion,
          options
        );
      } catch (error) {
        if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
          clearBusyForRun(runId, runVersion);
          return;
        }
        setState((current) => ({
          ...current,
          busyLabel: undefined,
          error:
            error instanceof Error
              ? error.message
              : "Live voice follow-up was saved, but the agent continuation failed."
        }));
      }
    },
    [clearBusyForRun, continueAgents, isActiveRunOwner, state.runId]
  );

  async function handleContinueAgents() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    setState((current) => ({
      ...current,
      busyLabel: "Continuing specialist agents",
      error: undefined
    }));
    try {
      await continueAgents(runId, "Continued the specialist agent loop.", runVersion);
    } catch (error) {
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not continue agent work"
      }));
    }
  }

  async function handleBuildWorkPlan() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    if (agentCycleInFlightRef.current) {
      setState((current) => ({
        ...current,
        error: "Agent continuation is already running."
      }));
      return;
    }
    const workPlanToken = beginRunAction(workPlanActionGateRef.current);
    if (workPlanToken === undefined) {
      return;
    }
    const workPlanOwner = { version: runVersion, token: workPlanToken };
    const isWorkPlanOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        workPlanOwner,
        runVersionRef.current,
        workPlanActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Planning next agent actions",
      error: undefined
    }));
    try {
      const result = await buildRunWorkPlan({
        runId,
        maxItems: 8,
        createFollowupTasks: false,
        refreshReason: "creator_app_next_actions"
      });
      if (!isWorkPlanOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(runId, result.summary, runVersion);
      if (!isWorkPlanOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        workPlan: current.runId === result.run_id ? result : current.workPlan,
        lastSummary: result.summary,
        busyLabel: undefined,
        error: undefined
      }));
    } catch (error) {
      if (!isWorkPlanOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not plan the next agent actions."
      }));
    } finally {
      finishRunAction(workPlanActionGateRef.current, workPlanToken);
    }
  }

  async function handleRunWorkPlan(workPlan: RunWorkPlanResult) {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (workPlan.run_id !== runId) {
      setState((current) => ({
        ...current,
        error: "The selected work plan belongs to a different run."
      }));
      return;
    }
    const agentIds = workPlanRunnableAgentIds(workPlan);
    if (agentIds.length === 0) {
      setState((current) => ({
        ...current,
        error: "The current work plan does not name any runnable agents."
      }));
      return;
    }
    if (workPlanActionGateRef.current.inFlight) {
      setState((current) => ({
        ...current,
        error: "Planning next agent actions is already running."
      }));
      return;
    }
    if (agentCycleInFlightRef.current) {
      setState((current) => ({
        ...current,
        error: "Agent continuation is already running."
      }));
      return;
    }
    setState((current) => ({
      ...current,
      busyLabel: "Materializing planned tasks",
      error: undefined
    }));
    agentCycleInFlightRef.current = true;
    let plannedAgentsCompleted = false;
    try {
      const materializedPlan = await buildRunWorkPlan(workPlanMaterializationInput(workPlan));
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      if (materializedPlan.run_id !== runId) {
        setState((current) => ({
          ...current,
          busyLabel: undefined,
          error: "The materialized work plan belongs to a different run."
        }));
        return;
      }
      const materializedAgentIds = workPlanRunnableAgentIds(materializedPlan);
      if (materializedAgentIds.length === 0) {
        setState((current) => ({
          ...current,
          busyLabel: undefined,
          error: "The materialized work plan does not name any runnable agents."
        }));
        return;
      }
      setState((current) => ({
        ...current,
        workPlan: current.runId === materializedPlan.run_id ? materializedPlan : current.workPlan,
        busyLabel: "Running planned agents"
      }));
      await runAgentCycleAndRefresh(
        runId,
        `Ran ${materializedAgentIds.length} planned specialist(s).`,
        runVersion,
        {
          agentIds: materializedAgentIds,
          maxTasksPerAgent: 3,
          maxRounds: 2
        }
      );
      plannedAgentsCompleted = true;
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: "Refreshing next agent actions"
      }));
      const nextPlan = await buildRunWorkPlan(workPlanPostRunRefreshInput(materializedPlan));
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(runId, nextPlan.summary, runVersion);
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        workPlan: current.runId === nextPlan.run_id ? nextPlan : current.workPlan,
        lastSummary: nextPlan.summary,
        busyLabel: undefined,
        error: undefined
      }));
    } catch (error) {
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error
          ? error.message
          : plannedAgentsCompleted
            ? "Planned agents ran, but next-action refresh failed."
            : "Could not run the planned agents."
      }));
    } finally {
      agentCycleInFlightRef.current = false;
    }
  }

  async function handleRefreshSources() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    if (agentCycleInFlightRef.current) {
      setState((current) => ({
        ...current,
        error: "Agent continuation is already running."
      }));
      return;
    }
    const sourceRefreshToken = beginRunAction(sourceRefreshActionGateRef.current);
    if (sourceRefreshToken === undefined) {
      return;
    }
    const sourceRefreshOwner = { version: runVersion, token: sourceRefreshToken };
    const isSourceRefreshOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        sourceRefreshOwner,
        runVersionRef.current,
        sourceRefreshActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Running web research",
      error: undefined
    }));
    agentCycleInFlightRef.current = true;
    try {
      if (!hasRunnableWebResearchTask(state.context?.agent_messages ?? [])) {
        const message = buildSourceRefreshMessage(
          runId,
          sources as SourceRecord[],
          state.context?.run.goal ?? "source-backed content"
        );
        if (!message) {
          if (isSourceRefreshOwnerCurrent()) {
            clearBusyForRun(runId, runVersion);
          }
          return;
        }
        await sendAgentMessage(message);
      }
      const cycle = await runAgentWorkerCycle(buildSourceRefreshCycleInput(runId));
      const activity = sourceRefreshActivitySummary(cycle);
      if (!isSourceRefreshOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(runId, activity, runVersion);
    } catch (error) {
      if (!isSourceRefreshOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not run web research"
      }));
    } finally {
      agentCycleInFlightRef.current = false;
      finishRunAction(sourceRefreshActionGateRef.current, sourceRefreshToken);
    }
  }

  function handleClearRun() {
    invalidateRunAction(composerSubmitGateRef.current);
    invalidateRunAction(sourceRefreshActionGateRef.current);
    invalidateRunAction(productionActionGateRef.current);
    invalidateRunAction(feedbackActionGateRef.current);
    invalidateRunAction(voiceSessionActionGateRef.current);
    invalidateRunAction(voiceProofActionGateRef.current);
    invalidateRunAction(autopilotActionGateRef.current);
    invalidateRunAction(localSchedulerActionGateRef.current);
    invalidateRunAction(workPlanActionGateRef.current);
    runVersionRef.current += 1;
    activeRunIdRef.current = undefined;
    latestRunEventIdRef.current = 0;
    liveRunRefreshEventRef.current = undefined;
    if (liveRunRefreshTimerRef.current) {
      window.clearTimeout(liveRunRefreshTimerRef.current);
      liveRunRefreshTimerRef.current = undefined;
    }
    window.localStorage.removeItem(RUN_STORAGE_KEY);
    setState((current) => ({
      runId: undefined,
      context: undefined,
      workerProfiles: [],
      realtimeSession: undefined,
      realtimeSessionKey: undefined,
      productionStatus: undefined,
      workPlan: undefined,
      busyLabel: undefined,
      error: undefined,
      selectedArtifactIds: [],
      useGemmaAgentCycle: current.useGemmaAgentCycle ?? false,
      autopilotAutoWakeEnabled: current.autopilotAutoWakeEnabled ?? true,
      autopilotAutoWakeSummary: undefined,
      runEventStreamStatus: "idle",
      runEventStreamSummary: undefined,
      lastSummary: "Started a clean local session."
    }));
  }

  async function handleLaunchAutopilot() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const autopilotToken = beginRunAction(autopilotActionGateRef.current);
    if (autopilotToken === undefined) {
      return;
    }
    const autopilotOwner = { version: runVersion, token: autopilotToken };
    const isAutopilotOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        autopilotOwner,
        runVersionRef.current,
        autopilotActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Starting always-on studio",
      error: undefined
    }));
    try {
      const result = await launchAutopilot({
        runId,
        useGemma: useGemmaAgentCycle
      });
      if (!isAutopilotOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(
        runId,
        appendCreatorStatusDetail("Always-on studio started.", result.summary),
        runVersion
      );
    } catch (error) {
      if (!isAutopilotOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error
          ? creatorStatusText(error.message)
          : "Could not start always-on studio."
      }));
    } finally {
      finishRunAction(autopilotActionGateRef.current, autopilotToken);
    }
  }

  async function handleStopAutopilot(profileId: UUID) {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const autopilotToken = beginRunAction(autopilotActionGateRef.current);
    if (autopilotToken === undefined) {
      return;
    }
    const autopilotOwner = { version: runVersion, token: autopilotToken };
    const isAutopilotOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        autopilotOwner,
        runVersionRef.current,
        autopilotActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Stopping always-on studio",
      error: undefined
    }));
    try {
      const profile = await stopWorkerProfile(profileId);
      if (!isAutopilotOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(
        runId,
        `Always-on studio stopped for ${creatorStatusText(profile.name)}.`,
        runVersion
      );
    } catch (error) {
      if (!isAutopilotOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error
          ? creatorStatusText(error.message)
          : "Could not stop always-on studio."
      }));
    } finally {
      finishRunAction(autopilotActionGateRef.current, autopilotToken);
    }
  }

  async function handleHeartbeatAutopilot(profileId: UUID) {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    if (autopilotHeartbeatInFlightRef.current) {
      setState((current) => ({
        ...current,
        busyLabel: "Running specialist pulse",
        error: "Specialist pulse is already running."
      }));
      return;
    }
    const profile = state.workerProfiles?.find((workerProfile) =>
      workerProfile.profile_id === profileId &&
      workerProfile.run_id === runId &&
      workerProfile.execution_mode === "autonomous_pass" &&
      ACTIVE_AUTOPILOT_STATUSES.has(workerProfile.status)
    );
    if (!profile) {
      setState((current) => ({
        ...current,
        error: "The selected always-on studio run is no longer active."
      }));
      return;
    }
    setState((current) => ({
      ...current,
      busyLabel: "Running specialist pulse",
      error: undefined
    }));
    autopilotHeartbeatInFlightRef.current = true;
    try {
      const result = await heartbeatWorkerProfile(profileId);
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(
        runId,
        appendCreatorStatusDetail("Specialist pulse finished.", result.summary),
        runVersion
      );
    } catch (error) {
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error
          ? creatorStatusText(error.message)
          : "Could not run specialist pulse."
      }));
    } finally {
      autopilotHeartbeatInFlightRef.current = false;
    }
  }

  const handleRunAutopilotScheduler = useCallback(async (
    options: { trigger?: "manual" | "auto"; wakeKey?: string | null } = {}
  ) => {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    const isAutoWake = options.trigger === "auto";
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (isAutoWake) {
      if (isWorkPlanPlanningInFlight() || isRunMutationInFlight(runId)) {
        return;
      }
    } else if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    if (autopilotSchedulerInFlightRunsRef.current.has(runId)) {
      if (!isAutoWake) {
        setState((current) => ({
          ...current,
          busyLabel: "Checking due always-on work",
          error: "Always-on studio check is already running."
        }));
      }
      return;
    }
    const activeProfile = selectedWorkerSchedulerProfile(
      state.workerProfiles ?? [],
      runId
    );
    if (!activeProfile) {
      if (!isAutoWake) {
        setState((current) => ({
          ...current,
          error: "No active always-on studio run is available for the background check."
        }));
      }
      return;
    }
    setState((current) => ({
      ...current,
      busyLabel: isAutoWake ? "Auto continue" : "Checking due always-on work",
      autopilotAutoWakeSummary: isAutoWake ? "Auto continue is checking due work." : current.autopilotAutoWakeSummary,
      error: undefined
    }));
    autopilotSchedulerInFlightRunsRef.current.add(runId);
    try {
      const result = await runWorkerScheduler({
        runId,
        executionMode: "autonomous_pass",
        maxProfiles: 10
      });
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      const resultSummary = creatorStatusText(result.summary);
      const summary =
        result.checked_profiles > 0
          ? `${isAutoWake ? "Auto continue checked this run." : "Always-on studio checked due work."} ${resultSummary}`
          : `${isAutoWake ? "Auto continue found no due profiles for this run." : "Always-on studio found no due profiles for this run."}`;
      if (isAutoWake) {
        setState((current) => ({
          ...current,
          autopilotAutoWakeSummary: summary
        }));
      }
      await refreshRun(runId, summary, runVersion);
    } catch (error) {
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        autopilotAutoWakeSummary: isAutoWake
          ? "Auto continue could not complete the background check."
          : current.autopilotAutoWakeSummary,
        error: error instanceof Error
          ? creatorStatusText(error.message)
          : "Could not run always-on studio check."
      }));
    } finally {
      autopilotSchedulerInFlightRunsRef.current.delete(runId);
    }
  }, [clearBusyForRun, isActiveRunOwner, refreshRun, state.runId, state.workerProfiles]);

  async function handleStartWorkerSchedulerProcess() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const localSchedulerToken = beginRunAction(localSchedulerActionGateRef.current);
    if (localSchedulerToken === undefined) {
      return;
    }
    const localSchedulerOwner = { version: runVersion, token: localSchedulerToken };
    const isLocalSchedulerOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        localSchedulerOwner,
        runVersionRef.current,
        localSchedulerActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    const activeProfile = selectedWorkerSchedulerProfile(
      state.workerProfiles ?? [],
      runId
    );
    if (!activeProfile) {
      setState((current) => ({
        ...current,
        error: "Start always-on studio before starting the background runner."
      }));
      finishRunAction(localSchedulerActionGateRef.current, localSchedulerToken);
      return;
    }
    setState((current) => ({
      ...current,
      busyLabel: "Starting background runner",
      error: undefined
    }));
    workerSchedulerStatusTokenRef.current = nextWorkerSchedulerStatusToken(
      workerSchedulerStatusTokenRef.current
    );
    try {
      const statusToken = workerSchedulerStatusTokenRef.current;
      const result = await startWorkerSchedulerProcess({
        runId,
        executionMode: "autonomous_pass",
        maxProfiles: 10,
        pollIntervalSeconds: activeProfile.poll_interval_seconds ?? 5
      });
      if (!isLocalSchedulerOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      const shouldCommit = shouldCommitWorkerSchedulerStatus(
        statusToken,
        workerSchedulerStatusTokenRef.current
      );
      if (shouldCommit) {
        const resultSummary = creatorStatusText(result.summary);
        setState((current) => ({
          ...current,
          workerSchedulerProcess: result,
          busyLabel: undefined,
          error: undefined,
          lastSummary: resultSummary
        }));
        await refreshRun(runId, resultSummary, runVersion);
      }
    } catch (error) {
      if (!isLocalSchedulerOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error
          ? creatorStatusText(error.message)
          : "Could not start background runner."
      }));
    } finally {
      finishRunAction(localSchedulerActionGateRef.current, localSchedulerToken);
    }
  }

  async function handleStopWorkerSchedulerProcess() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const localSchedulerToken = beginRunAction(localSchedulerActionGateRef.current);
    if (localSchedulerToken === undefined) {
      return;
    }
    const localSchedulerOwner = { version: runVersion, token: localSchedulerToken };
    const isLocalSchedulerOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        localSchedulerOwner,
        runVersionRef.current,
        localSchedulerActionGateRef.current.token
      ) && (!runId || isActiveRunOwner(runId, runVersion))
    );
    setState((current) => ({
      ...current,
      busyLabel: "Stopping background runner",
      error: undefined
    }));
    workerSchedulerStatusTokenRef.current = nextWorkerSchedulerStatusToken(
      workerSchedulerStatusTokenRef.current
    );
    try {
      const statusToken = workerSchedulerStatusTokenRef.current;
      const result = await stopWorkerSchedulerProcess();
      if (!isLocalSchedulerOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      const shouldCommit = shouldCommitWorkerSchedulerStatus(
        statusToken,
        workerSchedulerStatusTokenRef.current
      );
      if (shouldCommit) {
        const resultSummary = creatorStatusText(result.summary);
        setState((current) => ({
          ...current,
          workerSchedulerProcess: result,
          busyLabel: undefined,
          error: undefined,
          lastSummary: resultSummary
        }));
      }
      if (shouldCommit && runId && isActiveRunOwner(runId, runVersion)) {
        await refreshRun(runId, creatorStatusText(result.summary), runVersion);
      }
    } catch (error) {
      if (!isLocalSchedulerOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error
          ? creatorStatusText(error.message)
          : "Could not stop background runner."
      }));
    } finally {
      finishRunAction(localSchedulerActionGateRef.current, localSchedulerToken);
    }
  }

  useEffect(() => {
    const decision = buildAutopilotAutoWakeDecision({
      runId: state.runId,
      workerProfiles: state.workerProfiles ?? [],
      enabled: autopilotAutoWakeEnabled,
      busy: Boolean(state.busyLabel),
      now: autopilotAutoWakeNow,
      inFlightRunIds: autopilotSchedulerInFlightRunsRef.current,
      lastWakeKey: autopilotAutoWakeLastKeyRef.current
    });
    if (!decision.shouldRun || !state.runId) {
      return;
    }

    autopilotAutoWakeLastKeyRef.current = decision.wakeKey ?? null;
    void handleRunAutopilotScheduler({
      trigger: "auto",
      wakeKey: decision.wakeKey
    });
  }, [
    autopilotAutoWakeEnabled,
    autopilotAutoWakeNow,
    handleRunAutopilotScheduler,
    state.busyLabel,
    state.runId,
    state.workerProfiles
  ]);

  async function handleRevise(feedbackText: string) {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion) || selectedArtifacts.length === 0) {
      setState((current) => ({
        ...current,
        error: "Select at least one draft before requesting a revision."
      }));
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const feedbackToken = beginRunAction(feedbackActionGateRef.current);
    if (feedbackToken === undefined) {
      return;
    }
    const feedbackOwner = { version: runVersion, token: feedbackToken };
    const isFeedbackOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        feedbackOwner,
        runVersionRef.current,
        feedbackActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );

    setState((current) => ({
      ...current,
      busyLabel: "Sending revision feedback",
      error: undefined
    }));

    try {
      const result = await submitRevision({
        runId,
        feedbackText,
        artifactIds: selectedArtifacts.map((artifact) => artifact.artifact_id)
      });
      if (!isFeedbackOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(runId, result.summary, runVersion);
    } catch (error) {
      if (!isFeedbackOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Revision failed"
      }));
    } finally {
      finishRunAction(feedbackActionGateRef.current, feedbackToken);
    }
  }

  async function handleResolveFeedback(feedbackId: UUID) {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const feedbackToken = beginRunAction(feedbackActionGateRef.current);
    if (feedbackToken === undefined) {
      return;
    }
    const feedbackOwner = { version: runVersion, token: feedbackToken };
    const isFeedbackOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        feedbackOwner,
        runVersionRef.current,
        feedbackActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Resolving feedback gate",
      error: undefined
    }));
    try {
      const result = await resolveFeedback({
        feedbackId,
        notes: "Resolved from the creator app after review.",
        resolvedBy: "user"
      });
      if (!isFeedbackOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await refreshRun(result.feedback.run_id, result.summary, runVersion);
    } catch (error) {
      if (!isFeedbackOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not resolve feedback"
      }));
    } finally {
      finishRunAction(feedbackActionGateRef.current, feedbackToken);
    }
  }

  async function handleBuildGrowthPackage() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const productionToken = beginRunAction(productionActionGateRef.current);
    if (productionToken === undefined) {
      return;
    }
    const productionOwner = { version: runVersion, token: productionToken };
    const isProductionOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        productionOwner,
        runVersionRef.current,
        productionActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Building growth package",
      error: undefined
    }));
    try {
      const result = await buildGrowthPackage({
        runId,
        artifactIds: selectedArtifacts.map((artifact) => artifact.artifact_id)
      });
      await refreshRun(runId, result.summary, runVersion);
      if (!isProductionOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        productionStatus: {
          label: "Growth package",
          summary: result.summary,
          nextActions: [
            `Created ${result.strategy_artifact_ids.length} growth strategies across ${result.platforms.length} platform surfaces.`
          ]
        }
      }));
    } catch (error) {
      if (!isProductionOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not build growth package"
      }));
    } finally {
      finishRunAction(productionActionGateRef.current, productionToken);
    }
  }

  async function handleBuildMediaPlan() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const productionToken = beginRunAction(productionActionGateRef.current);
    if (productionToken === undefined) {
      return;
    }
    const productionOwner = { version: runVersion, token: productionToken };
    const isProductionOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        productionOwner,
        runVersionRef.current,
        productionActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Building media plan",
      error: undefined
    }));
    try {
      const result = await buildMediaProductionPlan({
        runId,
        artifactIds: selectedArtifacts.map((artifact) => artifact.artifact_id)
      });
      await refreshRun(runId, result.summary, runVersion);
      if (!isProductionOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        productionStatus: {
          label: "Media plan",
          summary: result.summary,
          nextActions: [`Created ${result.media_artifact_ids.length} media planning artifacts.`]
        }
      }));
    } catch (error) {
      if (!isProductionOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not build media plan"
      }));
    } finally {
      finishRunAction(productionActionGateRef.current, productionToken);
    }
  }

  async function handleCheckPublishReadiness() {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (!runId || !isActiveRunOwner(runId, runVersion)) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId)) {
      return;
    }
    const productionToken = beginRunAction(productionActionGateRef.current);
    if (productionToken === undefined) {
      return;
    }
    const productionOwner = { version: runVersion, token: productionToken };
    const isProductionOwnerCurrent = () => (
      isRunVersionedActionCurrent(
        productionOwner,
        runVersionRef.current,
        productionActionGateRef.current.token
      ) && isActiveRunOwner(runId, runVersion)
    );
    setState((current) => ({
      ...current,
      busyLabel: "Checking publish readiness",
      error: undefined
    }));
    try {
      const result = await checkPublishReadiness({
        runId,
        artifactIds: selectedArtifacts.map((artifact) => artifact.artifact_id)
      });
      await refreshRun(runId, result.summary, runVersion);
      if (!isProductionOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        productionStatus: {
          label: "Publish readiness",
          summary: result.summary,
          readinessStatus: result.status,
          blockingIssues: result.blocking_issues,
          nextActions: result.recommended_next_actions,
          publishChannelChecks: result.publish_channel_checks
        }
      }));
    } catch (error) {
      if (!isProductionOwnerCurrent()) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not check publish readiness"
      }));
    } finally {
      finishRunAction(productionActionGateRef.current, productionToken);
    }
  }

  async function handleRetryAgentMessage(message: AgentMessage) {
    const runId = state.runId;
    const runVersion = runVersionRef.current;
    if (
      !runId ||
      message.run_id !== runId ||
      !isActiveRunOwner(runId, runVersion) ||
      retryInFlightMessageIdsRef.current.has(message.message_id)
    ) {
      return;
    }
    if (blockSameRunMutationIfBusy(runId) || agentCycleInFlightRef.current) {
      return;
    }
    retryInFlightMessageIdsRef.current.add(message.message_id);
    agentCycleInFlightRef.current = true;
    setRetryingMessageIds((current) =>
      current.includes(message.message_id) ? current : [...current, message.message_id]
    );
    setState((current) => ({
      ...current,
      busyLabel: "Queueing and running retry",
      error: undefined
    }));
    try {
      const result = await authorizeAgentMessageRetry({
        messageId: message.message_id,
        reason: "Creator requested retry from the Activity rail."
      });
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      await runAgentCycleAndRefresh(
        runId,
        `Queued retry for ${result.message.recipient_agent_id}.`,
        runVersion,
        {
          agentIds: [result.message.recipient_agent_id],
          messageIds: [result.message.message_id],
          maxTasksPerAgent: 1,
          maxRounds: 1
        }
      );
    } catch (error) {
      if (!isRunVersionCurrent(runVersion, runVersionRef.current)) {
        clearBusyForRun(runId, runVersion);
        return;
      }
      setState((current) => ({
        ...current,
        busyLabel: undefined,
        error: error instanceof Error ? error.message : "Could not queue and run agent retry"
      }));
    } finally {
      agentCycleInFlightRef.current = false;
      retryInFlightMessageIdsRef.current.delete(message.message_id);
      setRetryingMessageIds((current) => current.filter((id) => id !== message.message_id));
    }
  }

  function toggleArtifact(artifactId: UUID) {
    const artifact = artifacts.find((item) => item.artifact_id === artifactId);
    if (!artifact || !isContentArtifact(artifact)) {
      return;
    }
    setState((current) => {
      const exists = current.selectedArtifactIds.includes(artifactId);
      return {
        ...current,
        selectedArtifactIds: exists
          ? current.selectedArtifactIds.filter((id) => id !== artifactId)
          : [...current.selectedArtifactIds, artifactId]
      };
    });
  }

  return (
    <AppShell
      run={state.context?.run}
      busyLabel={state.busyLabel}
      error={state.error}
      lastSummary={state.lastSummary}
      onClear={handleClearRun}
      onRefresh={handleRefresh}
    >
      <section className="workspace-grid" aria-label="Content generation workspace">
        <div className="primary-stack">
          <RealtimeVoicePanel
            key={state.runId ?? "new-voice-session"}
            runId={state.runId}
            busy={Boolean(state.busyLabel)}
            artifacts={artifacts}
            onCreateVoiceRun={handleCreateVoiceRun}
            onVoiceRunMutationStart={handleVoiceRunMutationStart}
            onVoiceRunMutationFinish={handleVoiceRunMutationFinish}
            onVoiceProofMutationStart={handleVoiceProofMutationStart}
            onVoiceProofMutationFinish={handleVoiceProofMutationFinish}
            onSessionReady={(realtimeSession, realtimeSessionKey) =>
              {
                if (activeRunIdRef.current !== realtimeSession.run_id) {
                  return;
                }
                setState((current) => ({ ...current, realtimeSession, realtimeSessionKey }));
              }
            }
            onRunUpdated={async (summary) => {
              const runId = state.runId;
              const runVersion = runVersionRef.current;
              if (runId && isActiveRunOwner(runId, runVersion)) {
                await refreshRun(runId, summary, runVersion);
              }
            }}
            onVoiceFollowupReady={handleVoiceFollowupReady}
          />
          <Composer busy={Boolean(state.busyLabel)} onSubmit={handleCompose} />
          <ConversationPanel turns={state.context?.conversation_turns ?? []} />
          <ProductionPanel
            disabled={!state.runId || Boolean(state.busyLabel)}
            selectedCount={selectedArtifacts.length}
            contentReadiness={contentReadiness}
            productionStatus={state.productionStatus}
            onBuildMedia={handleBuildMediaPlan}
            onBuildDistribution={handleBuildGrowthPackage}
            onCheckReadiness={handleCheckPublishReadiness}
          />
          <DraftBoard
            artifacts={artifacts as ArtifactRecord[]}
            claims={claims as ClaimRecord[]}
            feedback={feedback as FeedbackItem[]}
            selectedArtifactIds={selectedArtifacts.map((artifact) => artifact.artifact_id)}
            busy={Boolean(state.busyLabel)}
            onToggleArtifact={toggleArtifact}
            onRevise={handleRevise}
            onResolveFeedback={handleResolveFeedback}
          />
        </div>
        <aside className="side-stack" aria-label="Run evidence">
          <RunRail run={state.context?.run} context={state.context} />
          <ActivityPanel
            events={state.context?.recent_events ?? []}
            messages={state.context?.agent_messages ?? []}
            artifacts={artifacts as ArtifactRecord[]}
            workPlan={state.workPlan}
            workerProfiles={state.workerProfiles ?? []}
            disabled={!state.runId || Boolean(state.busyLabel)}
            retryingMessageIds={retryingMessageIds}
            onContinueAgents={handleContinueAgents}
            onBuildWorkPlan={handleBuildWorkPlan}
            onRunWorkPlan={handleRunWorkPlan}
            onRetryAgentMessage={handleRetryAgentMessage}
            onLaunchAutopilot={handleLaunchAutopilot}
            onRunAutopilotScheduler={handleRunAutopilotScheduler}
            onHeartbeatAutopilot={handleHeartbeatAutopilot}
            onStopAutopilot={handleStopAutopilot}
            workerSchedulerProcess={state.workerSchedulerProcess}
            onStartWorkerScheduler={handleStartWorkerSchedulerProcess}
            onStopWorkerScheduler={handleStopWorkerSchedulerProcess}
            autopilotAutoWakeEnabled={autopilotAutoWakeEnabled}
            autopilotAutoWakeDetail={state.autopilotAutoWakeSummary}
            onAutopilotAutoWakeChange={(enabled) =>
              setState((current) => ({
                ...current,
                autopilotAutoWakeEnabled: enabled,
                autopilotAutoWakeSummary: enabled
                  ? "Auto continue will run due studio work while this studio is open."
                  : "Auto continue is paused for this browser session."
              }))
            }
            eventStreamStatus={state.runEventStreamStatus ?? "idle"}
            eventStreamDetail={state.runEventStreamSummary}
            useGemma={useGemmaAgentCycle}
            onUseGemmaChange={(useGemma) =>
              setState((current) => ({ ...current, useGemmaAgentCycle: useGemma }))
            }
          />
          <SourcePanel
            sources={sources as SourceRecord[]}
            claims={claims as ClaimRecord[]}
            messages={state.context?.agent_messages ?? []}
            events={state.context?.recent_events ?? []}
            sourceEvidence={state.context?.source_evidence ?? []}
            disabled={!state.runId || Boolean(state.busyLabel)}
            onRefreshSources={handleRefreshSources}
          />
        </aside>
      </section>
    </AppShell>
  );
}
