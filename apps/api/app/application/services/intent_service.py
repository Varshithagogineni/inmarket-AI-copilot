"""Prompt normalization helpers."""

import re
from typing import List

from app.domain.models import CampaignRequest, NormalizedIntent


CITY_HINTS = ("dallas", "austin", "houston", "san antonio", "fort worth")
BRAND_HINTS = (
    "beverage",
    "cold beverage",
    "snack",
    "restaurant",
    "quick-service restaurant",
    "qsr",
)
AUDIENCE_HINTS = ("family", "students", "sports fans", "music fans")
GOAL_HINTS = ("awareness", "store visits", "product launch", "localized campaign")


def _extract_known_hint(prompt: str, known_values: List[str], default_value: str) -> str:
    lowered = prompt.lower()
    for value in known_values:
        if value in lowered:
            return value
    return default_value


def normalize_request(request: CampaignRequest) -> NormalizedIntent:
    """Convert plain-language input into a predictable intent object."""

    prompt = request.prompt.strip()
    city = request.city or _extract_known_hint(prompt, list(CITY_HINTS), "Dallas")
    timeframe = request.timeframe or _extract_timeframe(prompt)
    brand_category = request.brand_category or _extract_known_hint(
        prompt, list(BRAND_HINTS), "consumer brand"
    )
    audience = request.audience or _extract_known_hint(prompt, list(AUDIENCE_HINTS), "general audience")
    campaign_goal = request.campaign_goal or _extract_known_hint(
        prompt, list(GOAL_HINTS), "awareness"
    )
    requested_outputs = request.requested_outputs or _extract_outputs(prompt)
    constraints = _extract_constraints(prompt)
    return NormalizedIntent(
        city=city.title(),
        timeframe=timeframe,
        brand_category=brand_category,
        audience=audience,
        campaign_goal=campaign_goal,
        requested_outputs=requested_outputs,
        constraints=constraints,
    )


def _extract_timeframe(prompt: str) -> str:
    lowered = prompt.lower()
    if "this weekend" in lowered:
        return "this weekend"
    if "today" in lowered:
        return "today"
    if "this week" in lowered:
        return "this week"
    if "next week" in lowered:
        return "next week"
    return "this weekend"


def _extract_outputs(prompt: str) -> List[str]:
    lowered = prompt.lower()
    outputs = []
    if "poster" in lowered:
        outputs.append("poster")
    if "caption" in lowered or "social" in lowered:
        outputs.append("social_caption")
    if "headline" in lowered:
        outputs.append("headline")
    if not outputs:
        outputs.extend(["poster", "social_caption", "headline"])
    return outputs


def _extract_constraints(prompt: str) -> List[str]:
    lowered = prompt.lower()
    constraints = []
    if re.search(r"\bfamily[- ]friendly\b", lowered):
        constraints.append("family_friendly")
    if "music" in lowered:
        constraints.append("music")
    if "sports" in lowered:
        constraints.append("sports")
    return constraints

