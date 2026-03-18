"""Mock provider used until Ticketmaster is wired in."""

from typing import Iterable, List

from app.domain.models import EventCandidate


class MockEventProvider:
    """Static demo data that mirrors the Ticketmaster integration contract."""

    def search(self, city: str, timeframe: str) -> Iterable[EventCandidate]:
        events = _sample_events()
        return [event for event in events if event.city.lower() == city.lower()]


def _sample_events() -> List[EventCandidate]:
    return [
        EventCandidate(
            event_id="evt-dallas-family-festival",
            name="Dallas Family Festival",
            city="Dallas",
            date_label="this weekend",
            category="family",
            venue_name="Fair Park",
            family_friendly=True,
            visibility_hint="high",
            audience_tags=["family", "general audience"],
            brand_tags=["cold beverage", "beverage", "outdoor"],
            summary="Weekend family festival with high foot traffic and broad local appeal.",
        ),
        EventCandidate(
            event_id="evt-dallas-rock-show",
            name="Downtown Dallas Rock Night",
            city="Dallas",
            date_label="this weekend",
            category="music",
            venue_name="Victory Hall",
            family_friendly=False,
            visibility_hint="medium",
            audience_tags=["music fans", "general audience"],
            brand_tags=["snack", "beverage"],
            summary="Popular live music show with a younger audience mix.",
        ),
        EventCandidate(
            event_id="evt-austin-food-truck-rally",
            name="Austin Food Truck Rally",
            city="Austin",
            date_label="this weekend",
            category="community",
            venue_name="Waterfront Square",
            family_friendly=True,
            visibility_hint="high",
            audience_tags=["family", "general audience"],
            brand_tags=["restaurant", "quick-service restaurant", "beverage"],
            summary="Community dining event with strong sampling and activation potential.",
        ),
        EventCandidate(
            event_id="evt-houston-home-opener",
            name="Houston Home Opener",
            city="Houston",
            date_label="this weekend",
            category="sports",
            venue_name="Metro Stadium",
            family_friendly=True,
            visibility_hint="high",
            audience_tags=["sports fans", "family", "general audience"],
            brand_tags=["snack", "beverage", "restaurant"],
            summary="Large crowd sports event with strong local buzz.",
        ),
    ]

