import type {
  CampaignRunRequest,
  CampaignRunResponse,
  RefineRunRequest,
  RunSummary,
} from "../../types";

const FALLBACK_RESPONSE: CampaignRunResponse = {
  run_id: "demo-run-001",
  status: "completed",
  created_at: "2026-03-17T22:00:00Z",
  updated_at: "2026-03-17T22:00:00Z",
  request: {
    prompt:
      "Find the best family-friendly event in Dallas this weekend for promoting a cold beverage brand.",
    requested_outputs: ["poster", "social_caption", "headline"],
  },
  steps: [
    {
      key: "intent",
      label: "Understand request",
      status: "completed",
      detail: "Campaign intent normalized.",
    },
    {
      key: "discovery",
      label: "Find events",
      status: "completed",
      detail: "Event candidates discovered.",
    },
    {
      key: "evaluation",
      label: "Choose event",
      status: "completed",
      detail: "Candidates scored and ranked.",
    },
    {
      key: "brief",
      label: "Generate assets",
      status: "completed",
      detail: "Campaign brief, copy, and image concept generated.",
    },
  ],
  events: [
    {
      timestamp: "2026-03-17T22:00:00Z",
      event_type: "run_created",
      message: "Workflow run created.",
    },
    {
      timestamp: "2026-03-17T22:00:00Z",
      event_type: "intent_normalized",
      message: "Campaign intent normalized.",
    },
    {
      timestamp: "2026-03-17T22:00:00Z",
      event_type: "event_selected",
      message: "Selected event: Dallas Family Festival.",
    },
  ],
  error: null,
  normalized_intent: {
    city: "Dallas",
    timeframe: "this weekend",
    brand_category: "cold beverage",
    audience: "family",
    campaign_goal: "awareness",
    requested_outputs: ["poster", "social_caption", "headline"],
    constraints: ["family_friendly"],
  },
  selected_event: {
    event_id: "evt-dallas-family-festival",
    name: "Dallas Family Festival",
    city: "Dallas",
    date_label: "this weekend",
    category: "family",
    venue_name: "Fair Park",
    score: 93,
    rationale:
      "Dallas Family Festival is a strong match for cold beverage in Dallas; family-friendly positioning matches the user request; high visibility improves local activation potential",
    score_breakdown: {
      city_fit: 25,
      audience_fit: 18,
      brand_fit: 20,
      category_fit: 10,
      timing_fit: 10,
      visibility_fit: 10,
    },
    summary: "Weekend family festival with high foot traffic and broad local appeal.",
  },
  alternative_events: [
    {
      event_id: "evt-dallas-rock-show",
      name: "Downtown Dallas Rock Night",
      city: "Dallas",
      date_label: "this weekend",
      category: "music",
      venue_name: "Victory Hall",
      score: 69,
      rationale:
        "Downtown Dallas Rock Night is a strong match for cold beverage in Dallas; event format supports the brand category naturally",
      summary: "Popular live music show with a younger audience mix.",
    },
  ],
  campaign_brief: {
    event_name: "Dallas Family Festival",
    target_audience: "families",
    campaign_angle:
      "Show up where families already are and connect the brand to the event moment.",
    message_direction:
      "Keep the message local, timely, and tied to the energy of Dallas Family Festival.",
    cta_direction: "Drive a simple nearby action before or during the event.",
    activation_use_case:
      "Use geo-targeted social and local OOH-style creative around the event window.",
    reason_selected:
      "Dallas Family Festival is a strong match for cold beverage in Dallas; family-friendly positioning matches the user request; high visibility improves local activation potential",
  },
  copy_assets: {
    headline: "cold beverage meets the moment at Dallas Family Festival",
    social_caption:
      "Heading to Dallas Family Festival? Make the day better with cold beverage. Catch the energy, stay on-theme, and act nearby.",
    cta: "Find it nearby before the event starts",
    promo_text:
      "Built for Dallas in Dallas Family Festival, this activation turns local event energy into a campaign moment.",
  },
  image_concept: {
    prompt:
      "Design a localized marketing poster for cold beverage tied to Dallas Family Festival in Dallas. Feature energetic crowd context, clean brand-safe composition, bold headline space, and a polished modern advertising style.",
    alt_text: "Draft event activation poster for cold beverage around Dallas Family Festival",
    style_notes: ["clean layout", "event energy", "brand-safe colors", "clear CTA area"],
    prompt_version: "v1",
  },
  generated_asset: {
    provider: "mock",
    status: "preview_ready",
    prompt_version: "v1",
    asset_uri: null,
    error: null,
  },
  revision_id: 1,
  refinement_history: [],
  asset_versions: [
    {
      revision_id: 1,
      prompt_version: "v1",
      provider: "mock",
      status: "preview_ready",
      asset_uri: null,
    },
  ],
};

export async function createCampaignRun(
  payload: CampaignRunRequest,
): Promise<CampaignRunResponse> {
  try {
    const response = await fetch("/api/v1/runs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("API request failed");
    }

    return (await response.json()) as CampaignRunResponse;
  } catch (_error) {
    return FALLBACK_RESPONSE;
  }
}

export async function refineCampaignRun(
  runId: string,
  payload: RefineRunRequest,
): Promise<CampaignRunResponse> {
  try {
    const response = await fetch(`/api/v1/runs/${runId}/refine`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("API request failed");
    }

    return (await response.json()) as CampaignRunResponse;
  } catch (_error) {
    return buildFallbackRefinement(FALLBACK_RESPONSE, payload);
  }
}

export async function listCampaignRuns(): Promise<RunSummary[]> {
  try {
    const response = await fetch("/api/v1/runs");
    if (!response.ok) {
      throw new Error("API request failed");
    }

    const payload = (await response.json()) as { runs: RunSummary[] };
    return payload.runs;
  } catch (_error) {
    return [
      {
        run_id: FALLBACK_RESPONSE.run_id,
        status: FALLBACK_RESPONSE.status,
        created_at: FALLBACK_RESPONSE.created_at,
        updated_at: FALLBACK_RESPONSE.updated_at,
        prompt: FALLBACK_RESPONSE.request.prompt,
        selected_event_name: FALLBACK_RESPONSE.selected_event.name,
        event_count: FALLBACK_RESPONSE.events.length,
      },
    ];
  }
}

export async function getCampaignRun(runId: string): Promise<CampaignRunResponse> {
  try {
    const response = await fetch(`/api/v1/runs/${runId}`);
    if (!response.ok) {
      throw new Error("API request failed");
    }

    return (await response.json()) as CampaignRunResponse;
  } catch (_error) {
    return FALLBACK_RESPONSE;
  }
}

function buildFallbackRefinement(
  current: CampaignRunResponse,
  payload: RefineRunRequest,
): CampaignRunResponse {
  if (payload.target === "copy") {
    return {
      ...current,
      updated_at: "2026-03-17T22:05:00Z",
      copy_assets: {
        ...current.copy_assets,
        headline: `${current.copy_assets.headline} [${payload.instruction}]`,
        social_caption: `${current.copy_assets.social_caption} Refinement note: ${payload.instruction}`,
        promo_text: `${current.copy_assets.promo_text} Refinement note: ${payload.instruction}`,
      },
      revision_id: current.revision_id + 1,
      refinement_history: [
        ...current.refinement_history,
        {
          revision_id: current.revision_id + 1,
          target: payload.target,
          instruction: payload.instruction,
          applied_at: "2026-03-17T22:05:00Z",
        },
      ],
      events: [
        ...current.events,
        {
          timestamp: "2026-03-17T22:05:00Z",
          event_type: "run_refined",
          message: `Applied refinement to ${payload.target}: ${payload.instruction}`,
        },
      ],
      steps: current.steps.map((step) =>
        step.key === "brief"
          ? { ...step, detail: `Assets refined for target '${payload.target}'.` }
          : step,
      ),
    };
  }

  if (payload.target === "image") {
    return {
      ...current,
      updated_at: "2026-03-17T22:05:00Z",
      image_concept: {
        ...current.image_concept,
        prompt: `${current.image_concept.prompt} Additional direction: ${payload.instruction}`,
        style_notes: [...current.image_concept.style_notes, payload.instruction],
      },
      generated_asset: {
        ...current.generated_asset,
        status: "preview_ready",
      },
      revision_id: current.revision_id + 1,
      refinement_history: [
        ...current.refinement_history,
        {
          revision_id: current.revision_id + 1,
          target: payload.target,
          instruction: payload.instruction,
          applied_at: "2026-03-17T22:05:00Z",
        },
      ],
      asset_versions: [
        ...current.asset_versions,
        {
          revision_id: current.revision_id + 1,
          prompt_version: current.image_concept.prompt_version,
          provider: current.generated_asset.provider,
          status: "preview_ready",
          asset_uri: null,
        },
      ],
      events: [
        ...current.events,
        {
          timestamp: "2026-03-17T22:05:00Z",
          event_type: "run_refined",
          message: `Applied refinement to ${payload.target}: ${payload.instruction}`,
        },
      ],
      steps: current.steps.map((step) =>
        step.key === "brief"
          ? { ...step, detail: `Assets refined for target '${payload.target}'.` }
          : step,
      ),
    };
  }

  return {
    ...current,
    updated_at: "2026-03-17T22:05:00Z",
    campaign_brief: {
      ...current.campaign_brief,
      campaign_angle: `${current.campaign_brief.campaign_angle} Refined direction: ${payload.instruction}`,
      message_direction: `${current.campaign_brief.message_direction} Prioritize this feedback: ${payload.instruction}`,
    },
    revision_id: current.revision_id + 1,
    refinement_history: [
      ...current.refinement_history,
      {
        revision_id: current.revision_id + 1,
        target: payload.target,
        instruction: payload.instruction,
        applied_at: "2026-03-17T22:05:00Z",
      },
    ],
    asset_versions: [
      ...current.asset_versions,
      {
        revision_id: current.revision_id + 1,
        prompt_version: current.image_concept.prompt_version,
        provider: current.generated_asset.provider,
        status: current.generated_asset.status,
        asset_uri: current.generated_asset.asset_uri ?? null,
      },
    ],
    events: [
      ...current.events,
      {
        timestamp: "2026-03-17T22:05:00Z",
        event_type: "run_refined",
        message: `Applied refinement to ${payload.target}: ${payload.instruction}`,
      },
    ],
    steps: current.steps.map((step) =>
      step.key === "brief"
        ? { ...step, detail: `Assets refined for target '${payload.target}'.` }
        : step,
    ),
  };
}
