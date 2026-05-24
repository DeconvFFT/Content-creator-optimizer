import { Activity, AlertTriangle, FileText, MessageSquareText } from "lucide-react";
import type { RunContextPacket, RunState } from "@/lib/api/types";
import { formatDateTime, statusLabel } from "@/lib/state/format";

type RunRailProps = {
  run?: RunState;
  context?: RunContextPacket;
};

function riskLabel(risk: NonNullable<RunContextPacket["context_risks"]>[number]) {
  if (typeof risk === "string") {
    return risk;
  }
  return risk.reason ?? risk.risk_type ?? "Review the latest run risk.";
}

export function RunRail({ run, context }: RunRailProps) {
  if (!run) {
    return (
      <section className="rail-panel">
        <div className="section-heading compact">
          <h2>Progress</h2>
        </div>
        <p className="muted">Start with a text or voice prompt to create a run.</p>
      </section>
    );
  }

  return (
    <section className="rail-panel">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Progress</p>
          <h2>{statusLabel(run.status)}</h2>
        </div>
        <Activity size={18} aria-hidden="true" />
      </div>
      <dl className="metric-grid">
        <div>
          <dt>Drafts</dt>
          <dd>{context?.artifacts.length ?? run.artifact_ids.length}</dd>
        </div>
        <div>
          <dt>Sources</dt>
          <dd>{context?.sources.length ?? run.source_record_ids.length}</dd>
        </div>
        <div>
          <dt>Feedback</dt>
          <dd>{context?.feedback_items.length ?? run.feedback_item_ids.length}</dd>
        </div>
        <div>
          <dt>Turns</dt>
          <dd>{context?.conversation_turns.length ?? 0}</dd>
        </div>
      </dl>
      <p className="muted">Updated {formatDateTime(run.updated_at)}</p>
      {context?.context_risks && context.context_risks.length > 0 && (
        <div className="risk-list">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{riskLabel(context.context_risks[0])}</span>
        </div>
      )}
      <div className="event-list">
        {context?.conversation_turns.slice(-3).map((turn) => (
          <p key={turn.turn_id}>
            <MessageSquareText size={14} aria-hidden="true" />
            {turn.transcript}
          </p>
        ))}
        {context?.recommended_fetches?.slice(0, 2).map((item) => (
          <p key={item}>
            <FileText size={14} aria-hidden="true" />
            {item}
          </p>
        ))}
      </div>
    </section>
  );
}
