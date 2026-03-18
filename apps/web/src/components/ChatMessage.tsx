import Markdown from "react-markdown";
import type { CampaignRunResponse } from "../types";

export type MessageType = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isThinking?: boolean;
  runData?: CampaignRunResponse;
  showSection?: "copy" | "image" | "brief";
};

type ChatMessageProps = {
  message: MessageType;
};

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.isThinking) {
    return (
      <div className="chat-bubble assistant">
        <div className="bubble-content">
          <div className="thinking-dots">
            <span /><span /><span />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`chat-bubble ${message.role}`}>
      <div className="bubble-content">
        <div className="bubble-text">
          <Markdown>{message.content}</Markdown>
        </div>
        {message.runData && <RunCard run={message.runData} section={message.showSection} />}
      </div>
    </div>
  );
}

function RunCard({ run, section }: { run: CampaignRunResponse; section?: string }) {
  const showAll = !section;
  const recs = run.recommendations ?? [];
  const hasRecs = showAll && recs.length > 0;

  return (
    <div className="run-card">
      {/* Workflow Steps */}
      {showAll && (
        <div className="rc-steps">
          {run.steps.map((step) => (
            <div className={`rc-step rc-step-${step.status}`} key={step.key}>
              <div className={`rc-dot rc-dot-${step.status}`} />
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations (top 2 events with full details) */}
      {hasRecs ? (
        recs.map((rec, idx) => (
          <RecommendationCard key={rec.event.name} rec={rec} index={idx + 1} />
        ))
      ) : (
        <>
          {/* Fallback: single event view */}
          {showAll && run.selected_event && <EventCard event={run.selected_event} />}
          {(showAll || section === "brief") && run.campaign_brief && (
            <BriefSection brief={run.campaign_brief} />
          )}
          {(showAll || section === "copy") && run.copy_assets && (
            <CopySection copy={run.copy_assets} />
          )}
          {(showAll || section === "image") && run.image_concept && (
            <CreativeSection concept={run.image_concept} asset={run.generated_asset} />
          )}
        </>
      )}

      {/* Alternative Events */}
      {showAll && run.alternative_events.length > 0 && (
        <div className="rc-section">
          <div className="rc-section-label">Other Events Considered</div>
          <div className="rc-alts">
            {run.alternative_events.map((alt) => (
              <div className="rc-alt" key={alt.name}>
                <div className="rc-alt-header">
                  <strong>{alt.name}</strong>
                  <span className="rc-alt-score">{alt.score}</span>
                </div>
                <p>{alt.summary ?? alt.rationale}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RecommendationCard({ rec, index }: { rec: import("../types").FullRecommendation; index: number }) {
  return (
    <div className="rc-recommendation">
      <div className="rc-rec-header">
        <span className="rc-rec-number">{index}</span>
        <span className="rc-rec-title">Recommendation {index}</span>
      </div>
      <EventCard event={rec.event} />
      <BriefSection brief={rec.campaign_brief} />
      <CopySection copy={rec.copy_assets} />
      <CreativeSection concept={rec.image_concept} asset={rec.generated_asset} />
    </div>
  );
}

function EventCard({ event }: { event: import("../types").EventRecommendation }) {
  return (
    <div className="rc-section rc-event">
      <div className="rc-section-header">
        <div className="rc-section-label">Event</div>
        <div className="rc-score">{event.score}</div>
      </div>
      <h3 className="rc-event-name">{event.name}</h3>
      <div className="rc-event-meta">
        {event.venue_name && (
          <span className="rc-meta-chip">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            {event.venue_name}
          </span>
        )}
        {event.city && <span className="rc-meta-chip">{event.city}</span>}
        {event.date_label && (
          <span className="rc-meta-chip">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            {event.date_label}
          </span>
        )}
        {event.category && (
          <span className="rc-meta-chip rc-meta-category">{event.category}</span>
        )}
      </div>
      <p className="rc-rationale">{event.rationale}</p>
      {event.score_breakdown && (
        <div className="rc-breakdown">
          {Object.entries(event.score_breakdown).map(([k, v]) => (
            <div className="rc-breakdown-item" key={k}>
              <span className="rc-breakdown-label">{k.replace(/_/g, " ")}</span>
              <div className="rc-breakdown-bar">
                <div className="rc-breakdown-fill" style={{ width: `${(v / 25) * 100}%` }} />
              </div>
              <span className="rc-breakdown-val">{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function BriefSection({ brief }: { brief: CampaignRunResponse["campaign_brief"] }) {
  return (
    <div className="rc-section">
      <div className="rc-section-label">Campaign Brief</div>
      <div className="rc-brief-grid">
        <BriefItem label="Angle" value={brief.campaign_angle} />
        <BriefItem label="Message" value={brief.message_direction} />
        <BriefItem label="CTA" value={brief.cta_direction} />
        <BriefItem label="Activation" value={brief.activation_use_case} />
      </div>
    </div>
  );
}

function CopySection({ copy }: { copy: CampaignRunResponse["copy_assets"] }) {
  return (
    <div className="rc-section">
      <div className="rc-section-label">Copy Assets</div>
      <div className="rc-copy">
        <div className="rc-copy-headline">{copy.headline}</div>
        <div className="rc-copy-grid">
          <CopyItem label="Social Caption" value={copy.social_caption} />
          <CopyItem label="CTA" value={copy.cta} />
          <CopyItem label="Promo" value={copy.promo_text} />
        </div>
      </div>
    </div>
  );
}

function CreativeSection({ concept, asset }: { concept: CampaignRunResponse["image_concept"]; asset: CampaignRunResponse["generated_asset"] }) {
  return (
    <div className="rc-section">
      <div className="rc-section-label">Creative</div>
      {asset?.asset_uri ? (
        <img src={asset.asset_uri} alt={concept.alt_text || "Generated poster"} className="rc-generated-image" />
      ) : asset?.error ? (
        <div className="rc-error-box"><span>Image generation failed:</span> {asset.error}</div>
      ) : null}
      <p className="rc-image-prompt">{concept.prompt}</p>
      <div className="rc-style-tags">
        {concept.style_notes.map((note) => (
          <span key={note} className="rc-tag">{note}</span>
        ))}
      </div>
      <div className="rc-provider-badge">
        {asset?.provider} &middot; {asset?.status} &middot; v{concept.prompt_version}
      </div>
    </div>
  );
}

function BriefItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rc-brief-item">
      <span className="rc-label">{label}</span>
      <p>{value}</p>
    </div>
  );
}

function CopyItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rc-copy-item">
      <span className="rc-label">{label}</span>
      <p>{value}</p>
    </div>
  );
}
