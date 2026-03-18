import type { CampaignRunResponse } from "../types";
import { WorkflowTimeline } from "./WorkflowTimeline";

type ResultPanelProps = {
  result: CampaignRunResponse | null;
};

export function ResultPanel({ result }: ResultPanelProps) {
  if (!result) {
    return (
      <section className="panel result-panel placeholder">
        <div className="eyebrow">Recommendation</div>
        <h2>Waiting for a campaign request</h2>
        <p>
          The selected event, rationale, brief, and creative outputs will appear here after
          the workflow runs.
        </p>
      </section>
    );
  }

  return (
    <section className="panel result-panel">
      <div className="eyebrow">Selected event</div>
      <h2>{result.selected_event.name}</h2>
      <p className="score-chip">Score {result.selected_event.score}</p>
      <p>{result.selected_event.rationale}</p>
      <p className="run-meta">
        Run {result.run_id} | Status {result.status} | Revision {result.revision_id}
      </p>

      <div className="result-grid">
        <WorkflowTimeline steps={result.steps} />

        <article>
          <h3>Campaign brief</h3>
          <p>{result.campaign_brief.campaign_angle}</p>
          <p>{result.campaign_brief.message_direction}</p>
          <p>
            <strong>CTA:</strong> {result.campaign_brief.cta_direction}
          </p>
        </article>

        <article>
          <h3>Copy outputs</h3>
          <p>
            <strong>Headline:</strong> {result.copy_assets.headline}
          </p>
          <p>
            <strong>Caption:</strong> {result.copy_assets.social_caption}
          </p>
          <p>
            <strong>Promo:</strong> {result.copy_assets.promo_text}
          </p>
        </article>

        <article className="image-card">
          <h3>Creative direction</h3>
          <p>{result.image_concept.prompt}</p>
          <p className="asset-meta">
            Provider {result.generated_asset.provider} | Status {result.generated_asset.status} |
            Prompt {result.image_concept.prompt_version}
          </p>
          <div className="style-notes">
            {result.image_concept.style_notes.map((note) => (
              <span key={note}>{note}</span>
            ))}
          </div>
          {result.generated_asset.asset_uri ? (
            <img
              src={result.generated_asset.asset_uri}
              alt={result.image_concept.alt_text || "Generated creative asset"}
              className="generated-image"
            />
          ) : null}
          {result.generated_asset.error ? (
            <p className="asset-error">{result.generated_asset.error}</p>
          ) : null}
        </article>

        <article>
          <h3>Alternative events</h3>
          {result.alternative_events.length === 0 ? (
            <p>No close alternatives were returned for this run.</p>
          ) : (
            result.alternative_events.map((event) => (
              <div className="alternative-card" key={event.name}>
                <p>
                  <strong>{event.name}</strong> | Score {event.score}
                </p>
                <p>{event.summary ?? event.rationale}</p>
              </div>
            ))
          )}
        </article>

        <article>
          <h3>Refinement history</h3>
          {result.refinement_history.length === 0 ? (
            <p>No refinements applied yet.</p>
          ) : (
            result.refinement_history.map((item) => (
              <div className="alternative-card" key={`${item.revision_id}-${item.target}`}>
                <p>
                  <strong>Revision {item.revision_id}</strong> | {item.target}
                </p>
                <p>{item.instruction}</p>
                <p className="asset-meta">{item.applied_at}</p>
              </div>
            ))
          )}
        </article>

        <article>
          <h3>Asset lineage</h3>
          {result.asset_versions.map((item) => (
            <div className="alternative-card" key={`${item.revision_id}-${item.prompt_version}`}>
              <p>
                <strong>Revision {item.revision_id}</strong> | {item.provider}
              </p>
              <p>
                Prompt {item.prompt_version} | Status {item.status}
              </p>
            </div>
          ))}
        </article>

        <article>
          <h3>Event log</h3>
          {result.events.map((item, index) => (
            <div className="alternative-card" key={`${item.timestamp}-${item.event_type}-${index}`}>
              <p>
                <strong>{item.event_type}</strong>
              </p>
              <p>{item.message}</p>
              <p className="asset-meta">{item.timestamp}</p>
            </div>
          ))}
        </article>
      </div>
    </section>
  );
}
