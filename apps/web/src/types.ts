export type CampaignRunRequest = {
  prompt: string;
  city?: string;
  timeframe?: string;
  brand_category?: string;
  audience?: string;
  campaign_goal?: string;
  requested_outputs?: string[];
};

export type RefineRunRequest = {
  instruction: string;
  target: "brief" | "copy" | "image";
};

export type RunSummary = {
  run_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  prompt: string;
  selected_event_name?: string | null;
  event_count: number;
};

export type WorkflowStep = {
  key: string;
  label: string;
  status: string;
  detail: string;
};

export type EventRecommendation = {
  event_id?: string;
  name: string;
  city?: string;
  date_label?: string;
  category?: string;
  venue_name?: string;
  score: number;
  rationale: string;
  score_breakdown?: Record<string, number>;
  summary?: string;
};

export type FullRecommendation = {
  event: EventRecommendation;
  campaign_brief: {
    event_name: string;
    target_audience: string;
    campaign_angle: string;
    message_direction: string;
    cta_direction: string;
    activation_use_case: string;
    reason_selected: string;
  };
  copy_assets: {
    headline: string;
    social_caption: string;
    cta: string;
    promo_text: string;
  };
  image_concept: {
    prompt: string;
    alt_text: string;
    style_notes: string[];
    prompt_version: string;
  };
  generated_asset: {
    provider: string;
    status: string;
    prompt_version: string;
    asset_uri?: string | null;
    error?: string | null;
  };
};

export type CampaignRunResponse = {
  run_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  request: {
    prompt: string;
    city?: string;
    timeframe?: string;
    brand_category?: string;
    audience?: string;
    campaign_goal?: string;
    requested_outputs?: string[];
  };
  steps: WorkflowStep[];
  events: Array<{
    timestamp: string;
    event_type: string;
    message: string;
  }>;
  error?: string | null;
  normalized_intent: {
    city: string;
    timeframe: string;
    brand_category: string;
    audience: string;
    campaign_goal: string;
    requested_outputs: string[];
    constraints: string[];
  };
  selected_event: EventRecommendation;
  alternative_events: EventRecommendation[];
  recommendations?: FullRecommendation[];
  campaign_brief: {
    event_name: string;
    target_audience: string;
    campaign_angle: string;
    message_direction: string;
    cta_direction: string;
    activation_use_case: string;
    reason_selected: string;
  };
  copy_assets: {
    headline: string;
    social_caption: string;
    cta: string;
    promo_text: string;
  };
  image_concept: {
    prompt: string;
    alt_text: string;
    style_notes: string[];
    prompt_version: string;
  };
  generated_asset: {
    provider: string;
    status: string;
    prompt_version: string;
    asset_uri?: string | null;
    error?: string | null;
  };
  revision_id: number;
  refinement_history: Array<{
    revision_id: number;
    target: string;
    instruction: string;
    applied_at: string;
  }>;
  asset_versions: Array<{
    revision_id: number;
    prompt_version: string;
    provider: string;
    status: string;
    asset_uri?: string | null;
  }>;
};
