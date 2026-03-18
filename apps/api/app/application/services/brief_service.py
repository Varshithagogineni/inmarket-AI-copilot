"""Campaign brief and creative helper builders."""

from app.domain.models import CampaignBrief, CopyAssetSet, EventEvaluation, ImageConcept, NormalizedIntent


def build_campaign_brief(intent: NormalizedIntent, selected: EventEvaluation) -> CampaignBrief:
    event_name = selected.event.name
    audience = _humanize_audience(intent.audience)
    campaign_angle = "Show up where {0} already are and connect the brand to the event moment.".format(
        audience
    )
    message_direction = (
        "Keep the message local, timely, and tied to the energy of {0}.".format(event_name)
    )
    cta_direction = "Drive a simple nearby action before or during the event."
    activation_use_case = "Use geo-targeted social and local OOH-style creative around the event window."
    reason_selected = selected.rationale
    return CampaignBrief(
        event_name=event_name,
        target_audience=audience,
        campaign_angle=campaign_angle,
        message_direction=message_direction,
        cta_direction=cta_direction,
        activation_use_case=activation_use_case,
        reason_selected=reason_selected,
    )


def build_copy_assets(intent: NormalizedIntent, brief: CampaignBrief) -> CopyAssetSet:
    headline = "{0} meets the moment at {1}".format(
        _brand_lead(intent.brand_category), brief.event_name
    )
    social_caption = (
        "Heading to {0}? Make the day better with {1}. Catch the energy, stay on-theme, and act nearby."
    ).format(brief.event_name, _brand_lead(intent.brand_category))
    cta = "Find it nearby before the event starts"
    promo_text = (
        "Built for {0} in {1}, this activation turns local event energy into a campaign moment."
    ).format(intent.city, brief.event_name)
    return CopyAssetSet(
        headline=headline,
        social_caption=social_caption,
        cta=cta,
        promo_text=promo_text,
    )


def build_image_concept(
    intent: NormalizedIntent, brief: CampaignBrief, prompt_version: str = "v1"
) -> ImageConcept:
    prompt = (
        "Design a localized marketing poster for {0} tied to {1} in {2}. "
        "Feature energetic crowd context, clean brand-safe composition, bold headline space, "
        "and a polished modern advertising style."
    ).format(intent.brand_category, brief.event_name, intent.city)
    alt_text = "Draft event activation poster for {0} around {1}".format(
        intent.brand_category, brief.event_name
    )
    style_notes = ["clean layout", "event energy", "brand-safe colors", "clear CTA area"]
    return ImageConcept(
        prompt=prompt,
        alt_text=alt_text,
        style_notes=style_notes,
        prompt_version=prompt_version,
    )


def _brand_lead(brand_category: str) -> str:
    normalized = brand_category.strip()
    if normalized.lower() == "qsr":
        return "your quick-service brand"
    return normalized


def _humanize_audience(audience: str) -> str:
    if audience.lower() == "family":
        return "families"
    return audience
