import type { RunSummary } from "../types";

type RunHistoryPanelProps = {
  isLoading: boolean;
  runs: RunSummary[];
  activeRunId?: string;
  onSelect: (runId: string) => Promise<void>;
};

export function RunHistoryPanel({
  isLoading,
  runs,
  activeRunId,
  onSelect,
}: RunHistoryPanelProps) {
  return (
    <section className="panel history-panel">
      <div className="eyebrow">Run history</div>
      <h2>Previous workflows</h2>
      {isLoading ? <p>Loading history...</p> : null}
      {!isLoading && runs.length === 0 ? <p>No previous runs yet.</p> : null}
      <div className="history-list">
        {runs.map((run) => (
          <button
            className={`history-item ${activeRunId === run.run_id ? "history-item-active" : ""}`}
            key={run.run_id}
            onClick={() => onSelect(run.run_id)}
            type="button"
          >
            <strong>{run.selected_event_name ?? "Pending selection"}</strong>
            <span>{run.prompt}</span>
            <span>
              {run.status} | {run.event_count} events
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
