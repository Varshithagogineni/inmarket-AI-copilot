"""Deterministic scoring for event selection."""

from typing import Dict, List, Tuple

from app.domain.models import EventCandidate, EventEvaluation, NormalizedIntent


def score_event_fit(intent: NormalizedIntent, event: EventCandidate) -> EventEvaluation:
    score_breakdown = {
        "city_fit": _score_city_fit(intent, event),
        "audience_fit": _score_audience_fit(intent, event),
        "brand_fit": _score_brand_fit(intent, event),
        "category_fit": _score_category_fit(intent, event),
        "timing_fit": _score_timing_fit(intent, event),
        "visibility_fit": _score_visibility_fit(event),
    }
    total_score = sum(score_breakdown.values())
    rationale = _build_rationale(intent, event, score_breakdown)
    return EventEvaluation(
        event=event,
        total_score=total_score,
        score_breakdown=score_breakdown,
        rationale=rationale,
    )


def rank_events(intent: NormalizedIntent, events: List[EventCandidate]) -> List[EventEvaluation]:
    evaluated = [score_event_fit(intent, event) for event in events]
    return sorted(
        evaluated,
        key=lambda item: (
            item.total_score,
            item.score_breakdown["audience_fit"],
            item.score_breakdown["brand_fit"],
            item.event.family_friendly,
        ),
        reverse=True,
    )


def _score_city_fit(intent: NormalizedIntent, event: EventCandidate) -> int:
    return 25 if event.city.lower() == intent.city.lower() else 0


def _score_audience_fit(intent: NormalizedIntent, event: EventCandidate) -> int:
    audience = intent.audience.lower()
    tags = [tag.lower() for tag in event.audience_tags]
    if audience in tags:
        return 20
    if audience == "family" and event.family_friendly:
        return 18
    if audience == "general audience":
        return 12
    return 6


def _score_brand_fit(intent: NormalizedIntent, event: EventCandidate) -> int:
    brand = intent.brand_category.lower()
    tags = [tag.lower() for tag in event.brand_tags]
    if brand in tags:
        return 20
    if "beverage" in brand and "outdoor" in tags:
        return 16
    if "snack" in brand and event.category.lower() in ("sports", "music"):
        return 15
    if "restaurant" in brand and event.category.lower() in ("family", "sports", "community"):
        return 15
    return 8


def _score_category_fit(intent: NormalizedIntent, event: EventCandidate) -> int:
    constraints = set(intent.constraints)
    category = event.category.lower()
    if "family_friendly" in constraints and not event.family_friendly:
        return 0
    if "music" in constraints and category == "music":
        return 15
    if "sports" in constraints and category == "sports":
        return 15
    if not constraints:
        return 10
    if category in constraints:
        return 12
    return 6


def _score_timing_fit(intent: NormalizedIntent, event: EventCandidate) -> int:
    if intent.timeframe.lower() == event.date_label.lower():
        return 10
    if intent.timeframe.lower() == "this weekend" and "weekend" in event.date_label.lower():
        return 10
    return 4


def _score_visibility_fit(event: EventCandidate) -> int:
    visibility = event.visibility_hint.lower()
    if visibility == "high":
        return 10
    if visibility == "medium":
        return 7
    return 4


def _build_rationale(
    intent: NormalizedIntent, event: EventCandidate, score_breakdown: Dict[str, int]
) -> str:
    highlights = _collect_highlights(intent, event, score_breakdown)
    return "; ".join(highlights)


def _collect_highlights(
    intent: NormalizedIntent, event: EventCandidate, score_breakdown: Dict[str, int]
) -> List[str]:
    highlights = [
        "{0} is a strong match for {1} in {2}".format(
            event.name, intent.brand_category, intent.city
        )
    ]
    if event.family_friendly and "family_friendly" in intent.constraints:
        highlights.append("family-friendly positioning matches the user request")
    if score_breakdown["visibility_fit"] >= 10:
        highlights.append("high visibility improves local activation potential")
    if score_breakdown["brand_fit"] >= 15:
        highlights.append("event format supports the brand category naturally")
    return highlights


def explain_top_choice(evaluations: List[EventEvaluation]) -> Tuple[EventEvaluation, List[EventEvaluation]]:
    if not evaluations:
        raise ValueError("At least one event evaluation is required.")
    best = evaluations[0]
    alternatives = evaluations[1:3]
    return best, alternatives

