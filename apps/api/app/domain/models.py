"""Core domain models for the activation copilot.

These dataclasses intentionally avoid framework dependencies so the business
logic can be tested in isolation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CampaignRequest:
    prompt: str
    city: Optional[str] = None
    timeframe: Optional[str] = None
    brand_category: Optional[str] = None
    audience: Optional[str] = None
    campaign_goal: Optional[str] = None
    requested_outputs: List[str] = field(default_factory=list)


@dataclass
class NormalizedIntent:
    city: str
    timeframe: str
    brand_category: str
    audience: str
    campaign_goal: str
    requested_outputs: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class EventCandidate:
    event_id: str
    name: str
    city: str
    date_label: str
    category: str
    venue_name: str
    family_friendly: bool
    visibility_hint: str
    audience_tags: List[str] = field(default_factory=list)
    brand_tags: List[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class EventEvaluation:
    event: EventCandidate
    total_score: int
    score_breakdown: Dict[str, int]
    rationale: str


@dataclass
class CampaignBrief:
    event_name: str
    target_audience: str
    campaign_angle: str
    message_direction: str
    cta_direction: str
    activation_use_case: str
    reason_selected: str


@dataclass
class CopyAssetSet:
    headline: str
    social_caption: str
    cta: str
    promo_text: str


@dataclass
class ImageConcept:
    prompt: str
    alt_text: str
    style_notes: List[str] = field(default_factory=list)
    prompt_version: str = "v1"


@dataclass
class GeneratedAsset:
    provider: str
    status: str
    prompt_version: str
    asset_uri: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RefinementRecord:
    revision_id: int
    target: str
    instruction: str
    applied_at: str


@dataclass
class AssetVersion:
    revision_id: int
    prompt_version: str
    provider: str
    status: str
    asset_uri: Optional[str] = None


@dataclass
class EventRecommendation:
    """Full recommendation for a single event: brief + copy + creative."""
    evaluation: EventEvaluation
    campaign_brief: CampaignBrief
    copy_assets: CopyAssetSet
    image_concept: ImageConcept
    generated_asset: GeneratedAsset


@dataclass
class WorkflowResult:
    normalized_intent: NormalizedIntent
    candidate_evaluations: List[EventEvaluation]
    selected_event: EventEvaluation
    campaign_brief: CampaignBrief
    copy_assets: CopyAssetSet
    image_concept: ImageConcept
    generated_asset: GeneratedAsset
    recommendations: List[EventRecommendation] = field(default_factory=list)
    revision_id: int = 1
    refinement_history: List[RefinementRecord] = field(default_factory=list)
    asset_versions: List[AssetVersion] = field(default_factory=list)


@dataclass
class WorkflowStep:
    key: str
    label: str
    status: str
    detail: str


@dataclass
class WorkflowEvent:
    timestamp: str
    event_type: str
    message: str


@dataclass
class WorkflowRunRecord:
    run_id: str
    status: str
    request: CampaignRequest
    created_at: str
    updated_at: str
    steps: List[WorkflowStep] = field(default_factory=list)
    events: List[WorkflowEvent] = field(default_factory=list)
    result: Optional[WorkflowResult] = None
    error: Optional[str] = None
