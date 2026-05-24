import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CircleCheck,
  ClipboardCheck,
  GitBranch,
  Link2,
  ListChecks,
  PauseCircle,
  Play,
  RadioTower,
  RotateCw,
  Rocket
} from "lucide-react";
import type {
  AgentMessage,
  ArtifactRecord,
  RunEvent,
  RunWorkPlanItem,
  RunWorkPlanResult,
  UUID,
  WorkerProfile,
  WorkerSchedulerProcessStatusResult
} from "../../lib/api/types";
import { buildAutopilotEvidence } from "../../lib/state/autopilotEvidence";
import {
  latestActiveAutopilotProfile,
  latestAutopilotProfile
} from "../../lib/state/autopilotProfile";
import {
  buildAutopilotScheduleStatus,
  type AutopilotScheduleStatus
} from "../../lib/state/autopilotSchedule";
import { artifactHref, dispatchArtifactJump } from "../../lib/state/artifactAnchors";
import { compactId, formatDateTime, statusLabel } from "../../lib/state/format";
import { creatorRunEventLabel } from "../../lib/state/runEventRefresh";
import type { RunEventStreamStatus } from "../../lib/state/runEventStream";

type ActivityPanelProps = {
  events: RunEvent[];
  messages: AgentMessage[];
  artifacts?: ArtifactRecord[];
  workPlan?: RunWorkPlanResult | null;
  workerProfiles?: WorkerProfile[];
  disabled?: boolean;
  onContinueAgents?: () => Promise<void>;
  onBuildWorkPlan?: () => Promise<void>;
  onRunWorkPlan?: (workPlan: RunWorkPlanResult) => Promise<void>;
  onRetryAgentMessage?: (message: AgentMessage) => Promise<void>;
  retryingMessageIds?: UUID[];
  onLaunchAutopilot?: () => Promise<void>;
  onRunAutopilotScheduler?: () => Promise<void>;
  onHeartbeatAutopilot?: (profileId: string) => Promise<void>;
  onStopAutopilot?: (profileId: string) => Promise<void>;
  workerSchedulerProcess?: WorkerSchedulerProcessStatusResult | null;
  onStartWorkerScheduler?: () => Promise<void>;
  onStopWorkerScheduler?: () => Promise<void>;
  autopilotAutoWakeEnabled?: boolean;
  autopilotAutoWakeDetail?: string;
  onAutopilotAutoWakeChange?: (enabled: boolean) => void;
  eventStreamStatus?: RunEventStreamStatus;
  eventStreamDetail?: string;
  useGemma?: boolean;
  onUseGemmaChange?: (useGemma: boolean) => void;
  now?: Date;
};

const AUTOPILOT_CLOCK_INTERVAL_MS = 5_000;

export function ActivityPanel({
  events,
  messages,
  artifacts = [],
  workPlan,
  workerProfiles = [],
  disabled = false,
  onContinueAgents,
  onBuildWorkPlan,
  onRunWorkPlan,
  onRetryAgentMessage,
  retryingMessageIds = [],
  onLaunchAutopilot,
  onRunAutopilotScheduler,
  onHeartbeatAutopilot,
  onStopAutopilot,
  workerSchedulerProcess,
  onStartWorkerScheduler,
  onStopWorkerScheduler,
  autopilotAutoWakeEnabled = true,
  autopilotAutoWakeDetail,
  onAutopilotAutoWakeChange,
  eventStreamStatus = "idle",
  eventStreamDetail,
  useGemma = true,
  onUseGemmaChange,
  now
}: ActivityPanelProps) {
  const activityNow = useActivityClock(now);
  const recentEvents = events.slice(-5).reverse();
  const artifactWorkPlan = useMemo(
    () => latestWorkPlanFromArtifacts(artifacts),
    [artifacts]
  );
  const currentWorkPlan = useMemo(
    () => latestDurableOrLiveWorkPlan(workPlan, artifactWorkPlan, artifacts),
    [artifactWorkPlan, artifacts, workPlan]
  );
  const workPlanItems = currentWorkPlan?.plan_items.slice(0, 4) ?? [];
  const activeMessages = messages
    .filter((message) => !["completed", "canceled", "failed", "blocked"].includes(message.status))
    .slice(0, 5);
  const attentionMessages = messages
    .filter((message) => ["failed", "blocked", "canceled"].includes(message.status))
    .sort((left, right) => messageUpdatedMs(right) - messageUpdatedMs(left))
    .slice(0, 4);
  const retryingMessageIdSet = useMemo(
    () => new Set(retryingMessageIds),
    [retryingMessageIds]
  );
  const completedOutcomes = useMemo(
    () => recentCompletedOutcomes(messages),
    [messages]
  );
  const artifactsById = useMemo(
    () => new Map(artifacts.map((artifact) => [artifact.artifact_id, artifact])),
    [artifacts]
  );
  const autopilotProfiles = workerProfiles.filter(
    (profile) => profile.execution_mode === "autonomous_pass"
  );
  const activeAutopilot = latestActiveAutopilotProfile(autopilotProfiles);
  const latestAutopilot = activeAutopilot ?? latestAutopilotProfile(autopilotProfiles);
  const latestAutopilotProfileId = latestAutopilot?.profile_id;
  const latestAutopilotRunId = latestAutopilot?.run_id;
  const latestAutopilotExecutionMode = latestAutopilot?.execution_mode;
  const latestAutopilotCreatedAt = latestAutopilot?.created_at;
  const latestSchedulerEvent = useMemo(() => {
    if (!latestAutopilotProfileId || !latestAutopilotRunId || !latestAutopilotCreatedAt) {
      return null;
    }
    return [...events].reverse().find((event) => {
      if (event.event_type !== "worker_scheduler_pass_completed") {
        return false;
      }
      const profileIds = event.payload.profile_ids;
      if (
        Array.isArray(profileIds) &&
        profileIds.some((profileId) => profileId === latestAutopilotProfileId)
      ) {
        return true;
      }
      const requestedExecutionMode = event.payload.requested_execution_mode;
      return (
        isEventAtOrAfterProfileCreation(event.created_at, latestAutopilotCreatedAt) &&
        event.payload.requested_run_id === latestAutopilotRunId &&
        event.payload.idle_reason === "no_due_profiles" &&
        (
          requestedExecutionMode === undefined ||
          requestedExecutionMode === null ||
          requestedExecutionMode === latestAutopilotExecutionMode
        )
      );
    }) ?? null;
  }, [
    events,
    latestAutopilotCreatedAt,
    latestAutopilotExecutionMode,
    latestAutopilotProfileId,
    latestAutopilotRunId
  ]);
  const autopilotEvidence = useMemo(
    () => buildAutopilotEvidence({ workerProfiles, artifacts, events }),
    [artifacts, events, workerProfiles]
  );
  const autopilotSchedule = useMemo(
    () => buildAutopilotScheduleStatus(latestAutopilot, activityNow),
    [latestAutopilot, activityNow]
  );
  const schedulerPayload = latestSchedulerEvent?.payload ?? {};
  const schedulerCheckedProfiles = Number(
    schedulerPayload.checked_profiles ?? schedulerPayload.scheduler_checked_profiles ?? 0
  );
  const schedulerHeartbeats = Number(schedulerPayload.heartbeat_count ?? 0);
  const schedulerProcessedTasks = Number(schedulerPayload.total_processed_tasks ?? 0);
  const schedulerRiskCount = [
    "retrieval_quality_blocked_profile_count",
    "retrieval_quality_gate_blocked_profile_count",
    "retrieval_quality_recall_gap_count",
    "retrieval_quality_coverage_gap_count",
    "project_memory_retrieval_precision_risk_profile_count",
    "project_memory_retrieval_recall_gap_profile_count"
  ].reduce((total, key) => total + Number(schedulerPayload[key] ?? 0), 0);
  const autopilotDetail = latestAutopilot?.last_heartbeat_at
    ? `Last pulse ${formatDateTime(latestAutopilot.last_heartbeat_at)}`
    : latestAutopilot
      ? `${latestAutopilot.max_rounds} round(s), ${latestAutopilot.max_tasks_per_agent} task(s) per specialist`
      : "No always-on profile yet";
  const autopilotTechnicalDetail = latestAutopilot?.last_heartbeat_at
    ? `Last heartbeat ${formatDateTime(latestAutopilot.last_heartbeat_at)}`
    : latestAutopilot
      ? `Profile ${compactId(latestAutopilot.profile_id)}`
      : null;
  const autopilotScheduleCreator = autopilotSchedule
    ? creatorScheduleSummary(autopilotSchedule)
    : null;
  const autopilotScheduleTechnical = autopilotSchedule
    ? technicalScheduleSummary(autopilotSchedule)
    : null;
  const workerSchedulerRunning =
    workerSchedulerProcess?.running === true ||
    workerSchedulerProcess?.status === "running" ||
    workerSchedulerProcess?.status === "starting";
  const workerSchedulerStatus = workerSchedulerProcess
    ? workerSchedulerProcess.status
    : "not checked";
  const workerSchedulerDetail = workerSchedulerProcess
    ? [
        workerSchedulerProcess.pid ? `pid ${workerSchedulerProcess.pid}` : null,
        workerSchedulerProcess.run_id ? `run ${compactId(workerSchedulerProcess.run_id)}` : null,
        `${statusLabel(workerSchedulerProcess.execution_mode)} mode`,
        `${workerSchedulerProcess.poll_interval_seconds}s cadence`,
        `${workerSchedulerProcess.max_profiles} profile cap`
      ].filter(Boolean).join(" · ")
    : "Background runner status has not been loaded.";
  const workerSchedulerCreatorDetail = workerSchedulerProcess
    ? workerSchedulerRunning
      ? `Checks due work every ${workerSchedulerProcess.poll_interval_seconds}s`
      : "Ready to check due work when always-on studio is active."
    : "Background runner status has not been loaded.";

  return (
    <section className="rail-panel activity-panel" aria-label="Studio activity">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Studio</p>
          <h2>Studio flow</h2>
        </div>
        <RadioTower size={18} aria-hidden="true" />
      </div>

      {(onContinueAgents || onBuildWorkPlan || onUseGemmaChange) && (
        <div className="activity-actions">
          {onContinueAgents && (
            <button className="secondary-button" type="button" disabled={disabled} onClick={onContinueAgents}>
              <Play size={15} aria-hidden="true" />
              Continue specialists
            </button>
          )}
          {onBuildWorkPlan && (
            <button className="secondary-button" type="button" disabled={disabled} onClick={onBuildWorkPlan}>
              <ClipboardCheck size={15} aria-hidden="true" />
              Suggest next step
            </button>
          )}
          {onUseGemmaChange && (
            <label className="agent-cycle-toggle">
              <input
                type="checkbox"
                checked={useGemma}
                disabled={disabled}
                onChange={(event) => onUseGemmaChange(event.target.checked)}
              />
              <span>Gemma experts</span>
            </label>
          )}
          <span>
            {activeMessages.length > 0
              ? `${activeMessages.length} specialist cue(s)`
              : "No specialist cues shown"}
          </span>
        </div>
      )}

      {currentWorkPlan && (
        <div className="work-plan-strip" aria-label="Next studio steps">
          <ClipboardCheck size={16} aria-hidden="true" />
          <div className="work-plan-summary">
            <span>Next studio steps</span>
            <strong>
              {currentWorkPlan.plan_items.length} item(s) ·{" "}
              {currentWorkPlan.blocked_item_count} blocker(s)
            </strong>
            <small>
              {currentWorkPlan.pending_task_count} specialist cue(s)
              {currentWorkPlan.artifact_id
                ? ` · plan ${workPlanArtifactLabel(currentWorkPlan.artifact_id)}`
                : ""}
            </small>
            {workPlanProofDetails(currentWorkPlan).map((detail) => (
              <small key={detail}>{detail}</small>
            ))}
          </div>
          {onRunWorkPlan && (
            <div className="work-plan-controls">
              <button
                className="secondary-button"
                type="button"
                disabled={disabled || currentWorkPlan.plan_items.length === 0}
                onClick={() => onRunWorkPlan(currentWorkPlan)}
              >
                <Play size={15} aria-hidden="true" />
                Run next steps
              </button>
            </div>
          )}
          {workPlanItems.length > 0 && (
            <div className="work-plan-items">
              {workPlanItems.map((item) => (
                <article key={item.item_id}>
                  <div>
                    <p>{item.title}</p>
                    <span>
                      {statusLabel(item.owner_agent_id)} · {statusLabel(item.item_type)} ·{" "}
                      {statusLabel(item.priority)}
                      {item.blocking ? " · blocking" : ""}
                    </span>
                  </div>
                  <small>{item.recommended_action}</small>
                </article>
              ))}
            </div>
          )}
        </div>
      )}

      {eventStreamStatus !== "idle" && (
        <div className={`run-event-stream-status ${eventStreamStatus}`} aria-label="Live studio updates">
          <span>Live updates</span>
          <strong>{statusLabel(eventStreamStatus)}</strong>
          {eventStreamDetail && <small>{eventStreamDetail}</small>}
        </div>
      )}

      {(onLaunchAutopilot ||
        onRunAutopilotScheduler ||
        onHeartbeatAutopilot ||
        onStopAutopilot ||
        onStartWorkerScheduler ||
        onStopWorkerScheduler ||
        workerSchedulerProcess ||
        latestAutopilot) && (
        <div className="autopilot-strip">
          <Rocket size={16} aria-hidden="true" />
          <div className="autopilot-summary">
            <span>Always-on studio</span>
            <strong>
              {activeAutopilot
                ? "active"
                : latestAutopilot
                  ? statusLabel(latestAutopilot.status)
                  : "off"}
            </strong>
            <small>{autopilotDetail}</small>
            {autopilotScheduleCreator && (
              <small>
                {autopilotScheduleCreator.label}
                {autopilotScheduleCreator.detail ? ` · ${autopilotScheduleCreator.detail}` : ""}
              </small>
            )}
            {autopilotAutoWakeDetail && <small>{autopilotAutoWakeDetail}</small>}
            {(autopilotTechnicalDetail || autopilotScheduleTechnical) && (
              <details className="technical-proof-disclosure">
                <summary>Technical proof</summary>
                {autopilotTechnicalDetail && <small>{autopilotTechnicalDetail}</small>}
                {autopilotScheduleTechnical && <small>{autopilotScheduleTechnical}</small>}
              </details>
            )}
          </div>
          <div className="autopilot-controls">
            {onAutopilotAutoWakeChange && latestAutopilot && (
              <label className="agent-cycle-toggle">
                <input
                  type="checkbox"
                  checked={autopilotAutoWakeEnabled}
                  disabled={disabled}
                  onChange={(event) => onAutopilotAutoWakeChange(event.target.checked)}
                />
                <span>Auto continue</span>
              </label>
            )}
            {onLaunchAutopilot && (
              <button
                className="secondary-button"
                type="button"
                disabled={disabled || Boolean(activeAutopilot)}
                onClick={onLaunchAutopilot}
              >
                <Play size={15} aria-hidden="true" />
                Start always-on
              </button>
            )}
            {onRunAutopilotScheduler && activeAutopilot && (
              <button
                className="secondary-button"
                type="button"
                disabled={disabled}
                onClick={onRunAutopilotScheduler}
              >
                <RadioTower size={15} aria-hidden="true" />
                Check due work
              </button>
            )}
            {onHeartbeatAutopilot && activeAutopilot && (
              <button
                className="secondary-button"
                type="button"
                disabled={disabled}
                onClick={() => onHeartbeatAutopilot(activeAutopilot.profile_id)}
              >
                <RotateCw size={15} aria-hidden="true" />
                Run pulse
              </button>
            )}
            {onStopAutopilot && activeAutopilot && (
              <button
                className="secondary-button"
                type="button"
                disabled={disabled}
                onClick={() => onStopAutopilot(activeAutopilot.profile_id)}
              >
                <PauseCircle size={15} aria-hidden="true" />
                Stop
              </button>
              )}
            </div>
          {latestSchedulerEvent && (
            <div className="autopilot-evidence" aria-label="Background check">
              <span>Background check</span>
              <strong>{schedulerPayload.idle === true ? "idle" : "ran"}</strong>
              <small>{schedulerProcessedTasks > 0
                ? `${schedulerProcessedTasks} specialist update(s) this pass`
                : "No specialist updates this pass"}</small>
              {schedulerHeartbeats > 0 && <small>{schedulerHeartbeats} pulse(s) completed</small>}
              {schedulerRiskCount > 0 && (
                <small>{schedulerRiskCount} retrieval or memory risk signal(s)</small>
              )}
              <details className="technical-proof-disclosure">
                <summary>Technical proof</summary>
                <small>
                  {schedulerCheckedProfiles} profile(s) · {schedulerHeartbeats} heartbeat(s) ·{" "}
                  {schedulerProcessedTasks} task(s) · event #{latestSchedulerEvent.event_id}
                </small>
              </details>
            </div>
          )}
          {autopilotEvidence && (
            <div className="autopilot-evidence" aria-label="Specialist pulse">
              <span>Specialist pulse</span>
              <strong>{statusLabel(autopilotEvidence.heartbeatState)}</strong>
              <small>
                {autopilotEvidence.processedTasks ?? 0} specialist update(s)
                {autopilotEvidence.idle ? " · idle" : ""}
                {autopilotEvidence.skipped ? " · skipped" : ""}
              </small>
              {autopilotEvidence.blockedReasons.length > 0 && (
                <small>
                  Blocked: {autopilotEvidence.blockedReasons.map(statusLabel).join(", ")}
                </small>
              )}
              {(autopilotEvidence.workPlanArtifactId ||
                autopilotEvidence.contextPacketArtifactId ||
                autopilotEvidence.realtimeDialogueStatus ||
                autopilotEvidence.feedbackResolutionStatus) && (
                <small>
                  {autopilotEvidence.workPlanArtifactId
                    ? `work plan ${compactId(autopilotEvidence.workPlanArtifactId)}`
                    : "work plan pending"}
                  {" · "}
                  realtime {statusLabel(autopilotEvidence.realtimeDialogueStatus ?? "not recorded")}
                  {" · "}
                  feedback {statusLabel(autopilotEvidence.feedbackResolutionStatus ?? "not recorded")}
                </small>
              )}
              <details className="technical-proof-disclosure">
                <summary>Technical proof</summary>
                <small>
                  {autopilotEvidence.ledgerArtifactId
                    ? `ledger ${compactId(autopilotEvidence.ledgerArtifactId)}`
                    : "event evidence"}
                </small>
                {autopilotEvidence.workPlanArtifactId && (
                  <small>work plan {compactId(autopilotEvidence.workPlanArtifactId)}</small>
                )}
                {autopilotEvidence.contextPacketArtifactId && (
                  <small>context packet {compactId(autopilotEvidence.contextPacketArtifactId)}</small>
                )}
              </details>
            </div>
          )}
          {(workerSchedulerProcess || onStartWorkerScheduler || onStopWorkerScheduler) && (
            <div className="autopilot-evidence" aria-label="Background runner process">
              <span>Background runner</span>
              <strong>{statusLabel(workerSchedulerStatus)}</strong>
              <small>{workerSchedulerCreatorDetail}</small>
              {workerSchedulerProcess?.last_error && (
                <small>{redactSensitiveText(workerSchedulerProcess.last_error)}</small>
              )}
              {!latestAutopilot && <small>Start always-on studio before starting the background runner.</small>}
              {workerSchedulerProcess && (
                <details className="technical-proof-disclosure">
                  <summary>Technical proof</summary>
                  <small>{workerSchedulerDetail}</small>
                </details>
              )}
              <div className="autopilot-inline-controls">
                {onStartWorkerScheduler && !workerSchedulerRunning && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={disabled || !activeAutopilot}
                    onClick={onStartWorkerScheduler}
                  >
                    <RadioTower size={15} aria-hidden="true" />
                    Start runner
                  </button>
                )}
                {onStopWorkerScheduler && workerSchedulerRunning && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={disabled}
                    onClick={onStopWorkerScheduler}
                  >
                    <PauseCircle size={15} aria-hidden="true" />
                    Stop runner
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeMessages.length > 0 && (
        <div className="agent-task-list">
          {activeMessages.map((message) => (
            <article key={message.message_id}>
              <GitBranch size={15} aria-hidden="true" />
              <div>
                <p>{statusLabel(message.task_type)}</p>
                <span>
                  {statusLabel(message.sender_agent_id)} to {statusLabel(message.recipient_agent_id)} ·{" "}
                  {statusLabel(message.status)}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}

      {attentionMessages.length > 0 && (
        <div className="agent-attention-list" aria-label="Specialist tasks needing attention">
          <div className="agent-attention-heading">
            <AlertTriangle size={15} aria-hidden="true" />
            <span>Needs attention</span>
          </div>
          {attentionMessages.map((message) => {
            const retrying = retryingMessageIdSet.has(message.message_id);
            return (
              <article key={message.message_id}>
                <AlertTriangle size={15} aria-hidden="true" />
                <div>
                  <p>{statusLabel(message.task_type)}</p>
                  <span>
                    {statusLabel(message.recipient_agent_id)} · {statusLabel(message.status)} ·{" "}
                    {message.attempt_count}/{message.max_attempts} attempts
                  </span>
                  <small>{agentAttentionSummary(message)}</small>
                </div>
                {onRetryAgentMessage && (
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={disabled || retrying}
                    onClick={() => onRetryAgentMessage(message)}
                  >
                    <RotateCw size={14} aria-hidden="true" />
                    {retrying ? "Running" : "Queue and run"}
                  </button>
                )}
              </article>
            );
          })}
        </div>
      )}

      {completedOutcomes.length > 0 && (
        <div className="agent-outcome-list" aria-label="Recent specialist outputs">
          <div className="agent-outcome-heading">
            <CircleCheck size={15} aria-hidden="true" />
            <span>Recent specialist outputs</span>
          </div>
          {completedOutcomes.map((message) => {
            const producedArtifacts = agentOutcomeArtifacts(message, artifactsById);
            return (
              <article key={message.message_id}>
                <CircleCheck size={15} aria-hidden="true" />
                <div>
                  <p>{statusLabel(message.task_type)}</p>
                  <span>
                    {statusLabel(message.recipient_agent_id)} · {formatDateTime(message.updated_at)}
                  </span>
                  <small>{agentOutcomeSummary(message)}</small>
                  {producedArtifacts.length > 0 && (
                    <div className="agent-outcome-artifacts" aria-label="Produced artifacts">
                      {producedArtifacts.map((artifact) => (
                        <a
                          key={artifact.artifact_id}
                          href={artifactHref(artifact.artifact_id)}
                          onClick={() => dispatchArtifactJump(artifact.artifact_id)}
                        >
                          <Link2 size={13} aria-hidden="true" />
                          <span>{artifact.title}</span>
                          <small>{statusLabel(artifact.artifact_type)}</small>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      {recentEvents.length === 0 ? (
        <p className="muted">Studio updates will appear after generation starts.</p>
      ) : (
        <div className="timeline-list">
          {recentEvents.map((event) => (
            <article key={event.event_id}>
              <ListChecks size={15} aria-hidden="true" />
              <div>
                <p>{creatorRunEventLabel(event.event_type)}</p>
                <span>{statusLabel(event.actor)} · {formatDateTime(event.created_at)}</span>
                <details className="technical-proof-disclosure">
                  <summary>Technical proof</summary>
                  <small>event #{event.event_id}</small>
                </details>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function creatorScheduleSummary(schedule: AutopilotScheduleStatus) {
  if (schedule.state === "running") {
    return {
      label: "Pulse running",
      detail: "A specialist pulse is already in progress."
    };
  }
  if (schedule.state === "due") {
    return {
      label: "Due now",
      detail: "Ready to check due work."
    };
  }
  if (schedule.state === "scheduled") {
    return {
      label: "Scheduled",
      detail: schedule.nextDueAt ? `Next check ${formatDateTime(schedule.nextDueAt)}` : ""
    };
  }
  return {
    label: "Not running",
    detail: "Always-on studio is not active."
  };
}

function technicalScheduleSummary(schedule: AutopilotScheduleStatus) {
  return [
    schedule.label,
    schedule.nextDueAt ? `next due ${formatDateTime(schedule.nextDueAt)}` : null,
    schedule.leaseUntil ? `lease until ${formatDateTime(schedule.leaseUntil)}` : null,
    schedule.claimedBy ? `claimed by ${schedule.claimedBy}` : null,
    schedule.detail
  ].filter(Boolean).join(" · ");
}

function agentAttentionSummary(message: AgentMessage) {
  const resultReason = stringValue(message.result.reason);
  const retryPolicy = recordValue(message.result.retry_policy);
  const retryReason = stringValue(retryPolicy?.reason);
  const summary = resultReason ?? retryReason ?? message.error;
  return summary
    ? redactSensitiveText(summary).slice(0, 300)
    : "This specialist task needs operator attention.";
}

function redactSensitiveText(value: string) {
  return value
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/g, "Bearer [redacted]")
    .replace(/hf_[A-Za-z0-9]{20,}/g, "hf_[redacted]")
    .replace(/tvly-[A-Za-z0-9-]{20,}/g, "tvly-[redacted]");
}

function recentCompletedOutcomes(messages: AgentMessage[]) {
  return messages
    .filter((message) => message.status === "completed")
    .sort((left, right) => messageUpdatedMs(right) - messageUpdatedMs(left))
    .slice(0, 4);
}

function messageUpdatedMs(message: AgentMessage) {
  const timestamp = Date.parse(message.updated_at || message.created_at);
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function agentOutcomeSummary(message: AgentMessage) {
  const directSummary = stringValue(message.result.summary)?.trim();
  if (directSummary) {
    return directSummary;
  }

  const artifactCount = resultArtifactCount(message.result);
  const generationMode = stringValue(message.result.generation_mode);
  if (artifactCount > 0 && generationMode) {
    return `Created ${artifactCount} artifact${artifactCount === 1 ? "" : "s"} via ${statusLabel(generationMode)}.`;
  }
  if (artifactCount > 0) {
    return `Created ${artifactCount} artifact${artifactCount === 1 ? "" : "s"}.`;
  }
  if (generationMode) {
    return `Completed via ${statusLabel(generationMode)}.`;
  }
  if (message.error) {
    return message.error;
  }
  return "Completed without a recorded summary.";
}

function resultArtifactCount(result: Record<string, unknown>) {
  return artifactIdsFromResult(result).length;
}

function agentOutcomeArtifacts(
  message: AgentMessage,
  artifactsById: Map<string, ArtifactRecord>
) {
  return artifactIdsFromResult(message.result)
    .map((artifactId) => artifactsById.get(artifactId))
    .filter((artifact): artifact is ArtifactRecord => Boolean(artifact));
}

function artifactIdsFromResult(result: Record<string, unknown>) {
  const artifactKeys = [
    "artifact_ids",
    "created_artifact_ids",
    "content_artifact_ids",
    "media_artifact_ids",
    "strategy_artifact_ids",
    "revised_artifact_ids",
    "strategy_artifact_id"
  ];
  const artifactIds = new Set<string>();
  artifactKeys.forEach((key) => {
    const value = result[key];
    if (typeof value === "string" && value.trim().length > 0) {
      artifactIds.add(value);
      return;
    }
    if (!Array.isArray(value)) {
      return;
    }
    value.forEach((item) => {
      if (typeof item === "string" && item.trim().length > 0) {
        artifactIds.add(item);
      }
    });
  });
  return [...artifactIds];
}

function latestWorkPlanFromArtifacts(artifacts: ArtifactRecord[]): RunWorkPlanResult | null {
  const workPlanArtifact = [...artifacts]
    .filter((artifact) => (
      artifact.provenance.workflow === "run_work_plan_v1" &&
      Array.isArray(artifact.content.plan_items)
    ))
    .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at))[0];
  if (!workPlanArtifact) {
    return null;
  }
  const planItems = workPlanArtifact.content.plan_items;
  if (!Array.isArray(planItems)) {
    return null;
  }
  const parsedItems = planItems
    .map(parseRunWorkPlanItem)
    .filter((item): item is RunWorkPlanItem => item !== null);
  if (parsedItems.length === 0) {
    return null;
  }
  return {
    run_id: workPlanArtifact.run_id,
    plan_items: parsedItems,
    recommended_agent_ids: stringList(workPlanArtifact.content.recommended_agent_ids),
    open_feedback_count: numberValue(workPlanArtifact.content.open_feedback_count),
    routed_feedback_count: numberValue(workPlanArtifact.content.routed_feedback_count),
    pending_task_count: numberValue(workPlanArtifact.content.pending_task_count, parsedItems.length),
    blocked_item_count: numberValue(
      workPlanArtifact.content.blocked_item_count,
      parsedItems.filter((item) => item.blocking).length
    ),
    created_task_message_ids: stringList(workPlanArtifact.content.created_task_message_ids),
    skipped_duplicate_task_count: numberValue(workPlanArtifact.content.skipped_duplicate_task_count),
    artifact_id: workPlanArtifact.artifact_id,
    event_id: null,
    refresh_reason: stringValue(workPlanArtifact.content.refresh_reason),
    summary: `${parsedItems.length} next action(s) restored from work-plan artifact.`
  };
}

function workPlanProofDetails(workPlan: RunWorkPlanResult) {
  const details: string[] = [workPlanRefreshLabel(workPlan.refresh_reason)];
  if (workPlan.created_task_message_ids.length > 0) {
    details.push(`${workPlan.created_task_message_ids.length} task(s) created`);
  }
  if (workPlan.skipped_duplicate_task_count > 0) {
    details.push(`${workPlan.skipped_duplicate_task_count} duplicate task(s) skipped`);
  }
  if (workPlan.open_feedback_count > 0) {
    details.push(`${workPlan.open_feedback_count} open feedback`);
  }
  if (workPlan.routed_feedback_count > 0) {
    details.push(`${workPlan.routed_feedback_count} routed feedback`);
  }
  return details.filter(Boolean);
}

function workPlanRefreshLabel(refreshReason?: string | null) {
  if (refreshReason === "creator_app_run_plan") {
    return "execution plan";
  }
  if (refreshReason === "creator_app_after_run_plan") {
    return "post-run refresh";
  }
  if (refreshReason === "creator_app_next_actions") {
    return "manual plan";
  }
  return refreshReason ? statusLabel(refreshReason) : "work-plan proof";
}

function latestDurableOrLiveWorkPlan(
  liveWorkPlan: RunWorkPlanResult | null | undefined,
  artifactWorkPlan: RunWorkPlanResult | null,
  artifacts: ArtifactRecord[]
) {
  if (!liveWorkPlan) {
    return artifactWorkPlan;
  }
  if (!artifactWorkPlan) {
    return liveWorkPlan;
  }
  if (artifactWorkPlan.artifact_id && artifactWorkPlan.artifact_id !== liveWorkPlan.artifact_id) {
    if (
      liveWorkPlan.artifact_id &&
      !artifacts.some((artifact) => artifact.artifact_id === liveWorkPlan.artifact_id)
    ) {
      return liveWorkPlan;
    }
    return artifactWorkPlan;
  }
  return liveWorkPlan;
}

function parseRunWorkPlanItem(value: unknown): RunWorkPlanItem | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  const itemId = stringValue(record.item_id);
  const itemType = stringValue(record.item_type);
  const title = stringValue(record.title);
  const ownerAgentId = stringValue(record.owner_agent_id);
  const status = stringValue(record.status);
  const recommendedAction = stringValue(record.recommended_action);
  const reason = stringValue(record.reason);
  if (
    !itemId ||
    !itemType ||
    !title ||
    !ownerAgentId ||
    !status ||
    !recommendedAction ||
    !reason
  ) {
    return null;
  }
  const metadata =
    record.metadata && typeof record.metadata === "object" && !Array.isArray(record.metadata)
      ? record.metadata as Record<string, unknown>
      : {};
  return {
    item_id: itemId,
    item_type: itemType,
    title,
    owner_agent_id: ownerAgentId,
    status,
    priority: typeof record.priority === "string" ? record.priority : "normal",
    blocking: record.blocking === true,
    source_message_id: nullableString(record.source_message_id),
    source_feedback_id: nullableString(record.source_feedback_id),
    recommended_action: recommendedAction,
    reason,
    metadata
  };
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value : null;
}

function recordValue(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function numberValue(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stringList(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function nullableString(value: unknown) {
  return typeof value === "string" ? value : null;
}

function workPlanArtifactLabel(artifactId: string) {
  const parts = artifactId.split("-");
  if (parts.length >= 2 && parts[0] === "work" && parts[1] === "plan") {
    return "work-plan";
  }
  return compactId(artifactId);
}

function useActivityClock(nowOverride?: Date) {
  const [currentTime, setCurrentTime] = useState(() => nowOverride ?? new Date());

  useEffect(() => {
    if (nowOverride) {
      setCurrentTime(nowOverride);
      return undefined;
    }

    const intervalId = window.setInterval(
      () => setCurrentTime(new Date()),
      AUTOPILOT_CLOCK_INTERVAL_MS
    );
    return () => window.clearInterval(intervalId);
  }, [nowOverride]);

  return nowOverride ?? currentTime;
}

function isEventAtOrAfterProfileCreation(eventCreatedAt: string, profileCreatedAt: string) {
  const eventCreatedMs = Date.parse(eventCreatedAt);
  const profileCreatedMs = Date.parse(profileCreatedAt);
  return (
    Number.isFinite(eventCreatedMs) &&
    Number.isFinite(profileCreatedMs) &&
    eventCreatedMs >= profileCreatedMs
  );
}
