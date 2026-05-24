import { Film, Megaphone, ShieldCheck } from "lucide-react";
import type { PublishChannelCheck, PublishReadinessStatus } from "../../lib/api/types";
import type { ContentReadinessSnapshot } from "../../lib/state/contentReadiness";
import { statusLabel } from "../../lib/state/format";

export type ProductionStatus = {
  label: string;
  summary: string;
  readinessStatus?: PublishReadinessStatus;
  blockingIssues?: string[];
  nextActions?: string[];
  publishChannelChecks?: PublishChannelCheck[];
};

type ProductionPanelProps = {
  disabled: boolean;
  selectedCount: number;
  contentReadiness?: ContentReadinessSnapshot;
  productionStatus?: ProductionStatus;
  onBuildMedia: () => Promise<void>;
  onBuildDistribution: () => Promise<void>;
  onCheckReadiness: () => Promise<void>;
};

export function ProductionPanel({
  disabled,
  selectedCount,
  contentReadiness,
  productionStatus,
  onBuildMedia,
  onBuildDistribution,
  onCheckReadiness
}: ProductionPanelProps) {
  const noPublishableContent = contentReadiness?.status === "no_content";
  const blockedContent = contentReadiness?.status === "blocked";
  const productionDisabled = disabled || noPublishableContent;
  const packageDisabled = productionDisabled || blockedContent;

  return (
    <section className="production-panel" aria-label="Production controls">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Production</p>
          <h2>Package growth, plan media, and check readiness</h2>
        </div>
        <span>{selectedCount > 0 ? `${selectedCount} selected` : "All drafts"}</span>
      </div>

      {contentReadiness && (
        <div className="content-readiness-card" aria-label="Content readiness preflight">
          <div className="content-readiness-summary">
            <span>Content readiness</span>
            <strong className={`status-${contentReadiness.status}`}>
              {contentReadiness.label}
            </strong>
            <small>{contentReadiness.summary}</small>
          </div>
          <div className="content-readiness-metrics" aria-label="Content readiness metrics">
            <span>{contentReadiness.metrics.publishableArtifactCount} content</span>
            <span>{contentReadiness.metrics.sourceBackedArtifactCount} source-backed</span>
            <span>{contentReadiness.metrics.claimLinkedArtifactCount} claim-linked</span>
            <span>{contentReadiness.metrics.acceptedContextEvidenceCount} accepted sources</span>
          </div>
          {contentReadiness.blockers.length > 0 && (
            <ul>
              {contentReadiness.blockers.slice(0, 3).map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          )}
          {contentReadiness.nextActions.length > 0 && (
            <p className="muted">{contentReadiness.nextActions[0]}</p>
          )}
        </div>
      )}

      <div className="production-actions">
        <button type="button" disabled={packageDisabled} onClick={onBuildDistribution}>
          <Megaphone size={17} aria-hidden="true" />
          Growth package
        </button>
        <button type="button" disabled={packageDisabled} onClick={onBuildMedia}>
          <Film size={17} aria-hidden="true" />
          Media plan
        </button>
        <button type="button" disabled={productionDisabled} onClick={onCheckReadiness}>
          <ShieldCheck size={17} aria-hidden="true" />
          Publish check
        </button>
      </div>

      {productionStatus ? (
        <div className="production-status">
          <div>
            <strong>{productionStatus.label}</strong>
            {productionStatus.readinessStatus && (
              <span>{statusLabel(productionStatus.readinessStatus)}</span>
            )}
          </div>
          <p>{productionStatus.summary}</p>
          {productionStatus.blockingIssues && productionStatus.blockingIssues.length > 0 && (
            <ul>
              {productionStatus.blockingIssues.slice(0, 4).map((issue) => (
                <li key={issue}>{statusLabel(issue)}</li>
              ))}
            </ul>
          )}
          {productionStatus.publishChannelChecks && productionStatus.publishChannelChecks.length > 0 && (
            <ul aria-label="Publish channel checks">
              {productionStatus.publishChannelChecks.map((check) => {
                const envs =
                  check.credential_envs.length > 0
                    ? ` (${check.credential_envs.join(" or ")})`
                    : "";
                const nextAction = check.recommended_next_actions[0];

                return (
                  <li key={check.platform}>
                    {statusLabel(check.platform)}: credentials{" "}
                    {statusLabel(check.credential_status)}
                    {envs}, policy {statusLabel(check.policy_status)}
                    {nextAction && <span> {nextAction}</span>}
                  </li>
                );
              })}
            </ul>
          )}
          {productionStatus.nextActions && productionStatus.nextActions.length > 0 && (
            <p className="muted">{productionStatus.nextActions[0]}</p>
          )}
        </div>
      ) : (
        <p className="muted">
          Use selected drafts when checked; otherwise the system packages the latest leaf drafts.
        </p>
      )}
    </section>
  );
}
