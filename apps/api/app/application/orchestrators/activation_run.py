"""Synchronous orchestration for the activation workflow."""

from typing import Protocol

from app.application.services.creative_service import MockCreativeProvider
from app.application.services.brief_service import (
    build_campaign_brief,
    build_copy_assets,
    build_image_concept,
)
from app.application.services.intent_service import normalize_request
from app.application.services.scoring_service import explain_top_choice, rank_events
from app.domain.models import AssetVersion, CampaignRequest, WorkflowResult


class EventProvider(Protocol):
    def search(self, city: str, timeframe: str):
        """Return event candidates for a location and time window."""


def run_activation_workflow(
    request: CampaignRequest, provider: EventProvider
) -> WorkflowResult:
    intent = normalize_request(request)
    candidate_events = list(provider.search(intent.city, intent.timeframe))
    if not candidate_events:
        raise ValueError("No candidate events found for the given request.")

    evaluations = rank_events(intent, candidate_events)
    selected, _alternatives = explain_top_choice(evaluations)
    brief = build_campaign_brief(intent, selected)
    copy_assets = build_copy_assets(intent, brief)
    image_concept = build_image_concept(intent, brief)
    generated_asset = MockCreativeProvider().generate_asset(image_concept)

    return WorkflowResult(
        normalized_intent=intent,
        candidate_evaluations=evaluations,
        selected_event=selected,
        campaign_brief=brief,
        copy_assets=copy_assets,
        image_concept=image_concept,
        generated_asset=generated_asset,
        asset_versions=[
            AssetVersion(
                revision_id=1,
                prompt_version=generated_asset.prompt_version,
                provider=generated_asset.provider,
                status=generated_asset.status,
                asset_uri=generated_asset.asset_uri,
            )
        ],
    )
