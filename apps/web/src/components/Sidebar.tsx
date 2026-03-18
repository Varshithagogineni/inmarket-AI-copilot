import type { RunSummary } from "../types";

type SidebarProps = {
  runs: RunSummary[];
  activeRunId?: string;
  isOpen: boolean;
  onToggle: () => void;
  onSelect: (runId: string) => Promise<void>;
  onNewChat: () => void;
};

export function Sidebar({ runs, activeRunId, isOpen, onSelect, onNewChat }: SidebarProps) {
  if (!isOpen) return null;

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Campaigns</h2>
        <button className="new-chat-btn" onClick={onNewChat} type="button">
          + New
        </button>
      </div>
      <div className="sidebar-runs">
        {runs.length === 0 && <p className="sidebar-empty">No campaigns yet</p>}
        {runs.map((run) => (
          <button
            key={run.run_id}
            className={`sidebar-run ${activeRunId === run.run_id ? "sidebar-run-active" : ""}`}
            onClick={() => onSelect(run.run_id)}
            type="button"
          >
            <strong>{run.selected_event_name ?? "Pending"}</strong>
            <span className="sidebar-run-prompt">{run.prompt}</span>
            <span className="sidebar-run-meta">
              {run.status} | {run.event_count} events
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
