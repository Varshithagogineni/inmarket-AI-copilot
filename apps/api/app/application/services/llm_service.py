"""LLM-powered content generation using Google Gemini.

Replaces template-based string formatting with actual AI-generated
marketing copy, campaign briefs, and refinements.
"""

import json
import os
from typing import Optional

from app.domain.models import (
    CampaignBrief,
    CopyAssetSet,
    ImageConcept,
    NormalizedIntent,
    EventEvaluation,
)


def _get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


def _call_gemini(prompt: str, api_key: str = "") -> str:
    """Call Gemini 2.5 Flash for text generation."""
    from urllib.request import Request, urlopen

    key = api_key or _get_gemini_api_key()
    if not key:
        return ""

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={0}".format(key)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }
    req = Request(url, data=json.dumps(body).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
    except Exception:
        pass
    return ""


def generate_brief_with_llm(
    intent: NormalizedIntent,
    selected: EventEvaluation,
    api_key: str = "",
) -> Optional[CampaignBrief]:
    """Generate a campaign brief using Gemini LLM instead of templates."""
    prompt = """You are a senior marketing strategist. Generate a campaign activation brief.

Event: {event_name}
Venue: {venue}
City: {city}
Category: {category}
Brand Category: {brand_category}
Target Audience: {audience}
Campaign Goal: {campaign_goal}

Return ONLY valid JSON with these exact keys:
{{
  "campaign_angle": "A compelling 1-2 sentence campaign angle connecting the brand to this event",
  "message_direction": "A 1-2 sentence message direction for the creative team",
  "cta_direction": "A specific call-to-action direction",
  "activation_use_case": "How this activation would work in practice (geo-targeting, timing, placement)"
}}""".format(
        event_name=selected.event.name,
        venue=selected.event.venue_name,
        city=intent.city,
        category=selected.event.category,
        brand_category=intent.brand_category,
        audience=intent.audience,
        campaign_goal=intent.campaign_goal,
    )

    raw = _call_gemini(prompt, api_key)
    if not raw:
        return None

    try:
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

        data = json.loads(cleaned)
        return CampaignBrief(
            event_name=selected.event.name,
            target_audience=intent.audience,
            campaign_angle=data.get("campaign_angle", ""),
            message_direction=data.get("message_direction", ""),
            cta_direction=data.get("cta_direction", ""),
            activation_use_case=data.get("activation_use_case", ""),
            reason_selected=selected.rationale,
        )
    except (json.JSONDecodeError, KeyError):
        return None


def generate_copy_with_llm(
    intent: NormalizedIntent,
    brief: CampaignBrief,
    api_key: str = "",
) -> Optional[CopyAssetSet]:
    """Generate marketing copy using Gemini LLM instead of templates."""
    prompt = """You are an expert copywriter for brand activations. Generate marketing copy for this campaign.

Event: {event_name}
Brand Category: {brand_category}
Target Audience: {audience}
Campaign Angle: {angle}
CTA Direction: {cta}
City: {city}

Return ONLY valid JSON with these exact keys:
{{
  "headline": "A punchy, memorable headline under 10 words",
  "social_caption": "An engaging social media caption (1-2 sentences, include a subtle call-to-action)",
  "cta": "A short, action-oriented call-to-action (under 8 words)",
  "promo_text": "A promotional paragraph (2-3 sentences) for ad copy or email"
}}""".format(
        event_name=brief.event_name,
        brand_category=intent.brand_category,
        audience=intent.audience,
        angle=brief.campaign_angle,
        cta=brief.cta_direction,
        city=intent.city,
    )

    raw = _call_gemini(prompt, api_key)
    if not raw:
        return None

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

        data = json.loads(cleaned)
        return CopyAssetSet(
            headline=data.get("headline", ""),
            social_caption=data.get("social_caption", ""),
            cta=data.get("cta", ""),
            promo_text=data.get("promo_text", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return None


def refine_with_llm(
    target: str,
    instruction: str,
    brief: Optional[CampaignBrief] = None,
    copy_assets: Optional[CopyAssetSet] = None,
    image_concept: Optional[ImageConcept] = None,
    api_key: str = "",
) -> dict:
    """Use Gemini to refine existing content based on user instruction.

    Returns a dict with the refined object, or empty dict on failure.
    """
    if target == "brief" and brief:
        prompt = """You are a marketing strategist. Refine this campaign brief based on the feedback.

Current brief:
- Campaign Angle: {angle}
- Message Direction: {message}
- CTA Direction: {cta}
- Activation Use Case: {use_case}
- Event: {event}

Feedback: {instruction}

Return ONLY valid JSON with these exact keys (apply the feedback to improve them):
{{
  "campaign_angle": "refined campaign angle",
  "message_direction": "refined message direction",
  "cta_direction": "refined CTA direction",
  "activation_use_case": "refined activation use case"
}}""".format(
            angle=brief.campaign_angle,
            message=brief.message_direction,
            cta=brief.cta_direction,
            use_case=brief.activation_use_case,
            event=brief.event_name,
            instruction=instruction,
        )

        raw = _call_gemini(prompt, api_key)
        if raw:
            try:
                cleaned = _clean_json(raw)
                data = json.loads(cleaned)
                return {"brief": CampaignBrief(
                    event_name=brief.event_name,
                    target_audience=brief.target_audience,
                    campaign_angle=data.get("campaign_angle", brief.campaign_angle),
                    message_direction=data.get("message_direction", brief.message_direction),
                    cta_direction=data.get("cta_direction", brief.cta_direction),
                    activation_use_case=data.get("activation_use_case", brief.activation_use_case),
                    reason_selected=brief.reason_selected,
                )}
            except (json.JSONDecodeError, KeyError):
                pass

    elif target == "copy" and copy_assets:
        prompt = """You are an expert copywriter. Refine this marketing copy based on the feedback.

Current copy:
- Headline: {headline}
- Social Caption: {caption}
- CTA: {cta}
- Promo Text: {promo}

Feedback: {instruction}

Return ONLY valid JSON with these exact keys (apply the feedback to improve them):
{{
  "headline": "refined headline",
  "social_caption": "refined social caption",
  "cta": "refined CTA",
  "promo_text": "refined promo text"
}}""".format(
            headline=copy_assets.headline,
            caption=copy_assets.social_caption,
            cta=copy_assets.cta,
            promo=copy_assets.promo_text,
            instruction=instruction,
        )

        raw = _call_gemini(prompt, api_key)
        if raw:
            try:
                cleaned = _clean_json(raw)
                data = json.loads(cleaned)
                return {"copy_assets": CopyAssetSet(
                    headline=data.get("headline", copy_assets.headline),
                    social_caption=data.get("social_caption", copy_assets.social_caption),
                    cta=data.get("cta", copy_assets.cta),
                    promo_text=data.get("promo_text", copy_assets.promo_text),
                )}
            except (json.JSONDecodeError, KeyError):
                pass

    elif target == "image" and image_concept:
        prompt = """You are a creative director. Refine this image generation prompt based on the feedback.

Current prompt: {current_prompt}
Style notes: {style_notes}

Feedback: {instruction}

Return ONLY valid JSON:
{{
  "prompt": "refined detailed image generation prompt incorporating the feedback",
  "style_notes": ["note1", "note2", "note3"]
}}""".format(
            current_prompt=image_concept.prompt,
            style_notes=", ".join(image_concept.style_notes),
            instruction=instruction,
        )

        raw = _call_gemini(prompt, api_key)
        if raw:
            try:
                cleaned = _clean_json(raw)
                data = json.loads(cleaned)
                return {"image_concept": ImageConcept(
                    prompt=data.get("prompt", image_concept.prompt),
                    alt_text=image_concept.alt_text,
                    style_notes=data.get("style_notes", image_concept.style_notes),
                    prompt_version=image_concept.prompt_version,
                )}
            except (json.JSONDecodeError, KeyError):
                pass

    return {}


def _clean_json(raw: str) -> str:
    """Strip markdown code fences from LLM response."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    return cleaned
