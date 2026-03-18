"""Strategy and scoring tools for MCP."""

from app.schemas import MCPToolResponse


def score_event_fit(intent: dict, event: dict):
    audience = str(intent.get("audience", "general audience")).lower()
    brand_category = str(intent.get("brand_category", "brand")).lower()
    city = str(intent.get("city", "")).lower()
    constraints = [str(item).lower() for item in intent.get("constraints", [])]

    event_city = str(event.get("city", "")).lower()
    event_category = str(event.get("category", "community")).lower()
    audience_tags = [str(item).lower() for item in event.get("audience_tags", [])]
    brand_tags = [str(item).lower() for item in event.get("brand_tags", [])]
    family_friendly = bool(event.get("family_friendly", False))
    visibility = str(event.get("visibility_hint", "medium")).lower()

    score_breakdown = {
        "city_fit": 25 if city and city == event_city else 0,
        "audience_fit": _audience_score(audience, audience_tags, family_friendly),
        "brand_fit": _brand_score(brand_category, brand_tags, event_category),
        "category_fit": _category_score(constraints, event_category, family_friendly),
        "visibility_fit": 10 if visibility == "high" else 7 if visibility == "medium" else 4,
    }
    total_score = sum(score_breakdown.values())
    rationale = _build_rationale(event, brand_category, city, constraints, score_breakdown)
    return MCPToolResponse(
        status="ok",
        payload={
            "event": event,
            "score": total_score,
            "score_breakdown": score_breakdown,
            "rationale": rationale,
        },
    ).to_dict()


def rank_event_candidates(intent: dict, events: list):
    scored = [score_event_fit(intent, event)["payload"] for event in events]
    scored.sort(
        key=lambda item: (
            item["score"],
            item["score_breakdown"]["audience_fit"],
            item["score_breakdown"]["brand_fit"],
        ),
        reverse=True,
    )
    return MCPToolResponse(status="ok", payload={"ranked_events": scored}).to_dict()


def _audience_score(audience, audience_tags, family_friendly):
    if audience in audience_tags:
        return 20
    if audience == "family" and family_friendly:
        return 18
    if audience == "general audience":
        return 12
    return 6


def _brand_score(brand_category, brand_tags, event_category):
    if brand_category in brand_tags:
        return 20
    if "beverage" in brand_category and "outdoor" in brand_tags:
        return 16
    if "snack" in brand_category and event_category in ("sports", "music"):
        return 15
    if "restaurant" in brand_category and event_category in ("family", "sports", "community"):
        return 15
    return 8


def _category_score(constraints, event_category, family_friendly):
    if "family_friendly" in constraints and not family_friendly:
        return 0
    if "music" in constraints and event_category == "music":
        return 15
    if "sports" in constraints and event_category == "sports":
        return 15
    if not constraints:
        return 10
    if event_category in constraints:
        return 12
    return 6


def _build_rationale(event, brand_category, city, constraints, score_breakdown):
    event_name = event.get("name", "This event")
    parts = [
        "{0} is a strong match for {1} in {2}".format(
            event_name, brand_category or "the brand", city or "the target city"
        )
    ]
    if "family_friendly" in constraints and event.get("family_friendly"):
        parts.append("family-friendly positioning matches the request")
    if score_breakdown["visibility_fit"] >= 10:
        parts.append("high visibility improves activation potential")
    if score_breakdown["brand_fit"] >= 15:
        parts.append("event format supports the brand category naturally")
    return "; ".join(parts)
