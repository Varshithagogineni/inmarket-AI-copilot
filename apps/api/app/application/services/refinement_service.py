"""Helpers for refining an existing workflow result."""

from app.application.services.brief_service import (
    build_copy_assets,
    build_image_concept,
)
from app.domain.models import (
    AssetVersion,
    CampaignBrief,
    CopyAssetSet,
    ImageConcept,
    RefinementRecord,
    WorkflowResult,
)


def refine_workflow_result(
    result: WorkflowResult,
    instruction: str,
    target: str,
    prompt_version: str,
    creative_provider,
    applied_at: str,
) -> WorkflowResult:
    target = target.lower().strip()
    instruction = instruction.strip()

    if not instruction:
        raise ValueError("A refinement instruction is required.")

    brief = result.campaign_brief
    copy_assets = result.copy_assets
    image_concept = result.image_concept
    generated_asset = result.generated_asset
    revision_id = result.revision_id + 1
    refinement_history = list(result.refinement_history)
    asset_versions = list(result.asset_versions)

    if target == "brief":
        brief = _refine_brief(brief, instruction)
        copy_assets = build_copy_assets(result.normalized_intent, brief)
        image_concept = build_image_concept(
            result.normalized_intent, brief, prompt_version=prompt_version
        )
        generated_asset = creative_provider.generate_asset(image_concept)
        asset_versions.append(_asset_version(revision_id, generated_asset))
    elif target == "copy":
        copy_assets = _refine_copy(copy_assets, instruction)
    elif target == "image":
        image_concept = _refine_image_concept(image_concept, instruction, prompt_version)
        generated_asset = creative_provider.generate_asset(image_concept)
        asset_versions.append(_asset_version(revision_id, generated_asset))
    else:
        raise ValueError("Unsupported refinement target: {0}".format(target))

    refinement_history.append(
        RefinementRecord(
            revision_id=revision_id,
            target=target,
            instruction=instruction,
            applied_at=applied_at,
        )
    )

    return WorkflowResult(
        normalized_intent=result.normalized_intent,
        candidate_evaluations=result.candidate_evaluations,
        selected_event=result.selected_event,
        campaign_brief=brief,
        copy_assets=copy_assets,
        image_concept=image_concept,
        generated_asset=generated_asset,
        revision_id=revision_id,
        refinement_history=refinement_history,
        asset_versions=asset_versions,
    )


def _refine_brief(brief: CampaignBrief, instruction: str) -> CampaignBrief:
    return CampaignBrief(
        event_name=brief.event_name,
        target_audience=brief.target_audience,
        campaign_angle="{0} Refined direction: {1}".format(brief.campaign_angle, instruction),
        message_direction="{0} Prioritize this feedback: {1}".format(
            brief.message_direction, instruction
        ),
        cta_direction=brief.cta_direction,
        activation_use_case=brief.activation_use_case,
        reason_selected=brief.reason_selected,
    )


def _refine_copy(copy_assets: CopyAssetSet, instruction: str) -> CopyAssetSet:
    return CopyAssetSet(
        headline="{0} [{1}]".format(copy_assets.headline, instruction),
        social_caption="{0} Refinement note: {1}".format(copy_assets.social_caption, instruction),
        cta=copy_assets.cta,
        promo_text="{0} Refinement note: {1}".format(copy_assets.promo_text, instruction),
    )


def _refine_image_concept(
    image_concept: ImageConcept, instruction: str, prompt_version: str
) -> ImageConcept:
    next_notes = list(image_concept.style_notes)
    next_notes.append(instruction)
    return ImageConcept(
        prompt="{0} Additional direction: {1}".format(image_concept.prompt, instruction),
        alt_text=image_concept.alt_text,
        style_notes=next_notes,
        prompt_version=prompt_version,
    )


def _asset_version(revision_id: int, generated_asset) -> AssetVersion:
    return AssetVersion(
        revision_id=revision_id,
        prompt_version=generated_asset.prompt_version,
        provider=generated_asset.provider,
        status=generated_asset.status,
        asset_uri=generated_asset.asset_uri,
    )
