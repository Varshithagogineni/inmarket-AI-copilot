import type { WorkflowStep } from "../types";

type WorkflowTimelineProps = {
  steps: WorkflowStep[];
};

export function WorkflowTimeline({ steps }: WorkflowTimelineProps) {
  return (
    <article className="timeline-card">
      <h3>Workflow progress</h3>
      <div className="timeline-list">
        {steps.map((step) => (
          <div className="timeline-step" key={step.key}>
            <div className={`timeline-dot timeline-dot-${step.status}`} />
            <div>
              <p className="timeline-label">{step.label}</p>
              <p className="timeline-detail">{step.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
