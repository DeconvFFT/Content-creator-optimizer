import { Loader2, Plus, RotateCcw, Sparkles } from "lucide-react";
import type { RunState } from "@/lib/api/types";
import { compactId, statusLabel } from "../../lib/state/format";

type AppShellProps = {
  run?: RunState;
  busyLabel?: string;
  error?: string;
  lastSummary?: string;
  onClear: () => void;
  onRefresh: () => void;
  children: React.ReactNode;
};

export function AppShell({
  run,
  busyLabel,
  error,
  lastSummary,
  onClear,
  onRefresh,
  children
}: AppShellProps) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Content Studio</p>
          <h1>Source-backed drafts from voice or text</h1>
          <p className="topbar-copy">
            Talk through an idea, inspect the sources, then steer revisions without leaving the run.
          </p>
        </div>
        <div className="shell-actions">
          <div className="run-chip" aria-live="polite">
            <Sparkles size={18} aria-hidden="true" />
            <span>{run ? `${compactId(run.run_id)} - ${statusLabel(run.status)}` : "New run"}</span>
          </div>
          <button className="icon-button" type="button" onClick={onRefresh} disabled={!run || Boolean(busyLabel)} title="Refresh run">
            <RotateCcw size={17} aria-hidden="true" />
            <span>Refresh</span>
          </button>
          <button
            className="icon-button"
            type="button"
            onClick={onClear}
            disabled={Boolean(busyLabel)}
            title="Start a clean session"
          >
            <Plus size={17} aria-hidden="true" />
            <span>New</span>
          </button>
        </div>
      </header>

      {(busyLabel || error || lastSummary) && (
        <section className="status-strip" aria-live="polite">
          {busyLabel && (
            <span className="status-item">
              <Loader2 className="spin" size={16} aria-hidden="true" />
              {busyLabel}
            </span>
          )}
          {error && <span className="status-item error-text" role="alert">{error}</span>}
          {!busyLabel && !error && lastSummary && <span className="status-item">{lastSummary}</span>}
        </section>
      )}

      {children}
    </main>
  );
}
