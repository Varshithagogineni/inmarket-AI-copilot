"""Provider contract for real Ticketmaster-backed event discovery."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from app.domain.models import EventCandidate


class TicketmasterEventProvider:
    BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

    def __init__(self, api_key: Optional[str] = None, opener=urlopen):
        self.api_key = api_key or os.getenv("TICKETMASTER_API_KEY")
        self.opener = opener

    def search(self, city: str, timeframe: str) -> Iterable[EventCandidate]:
        if not self.api_key:
            raise ValueError("TICKETMASTER_API_KEY is not configured.")

        start_dt, end_dt = _date_range_for_timeframe(timeframe)
        query = {
            "apikey": self.api_key,
            "city": city,
            "size": 20,
            "sort": "relevance,desc",
            "startDateTime": start_dt,
            "endDateTime": end_dt,
        }
        url = "{0}?{1}".format(self.BASE_URL, urlencode(query))
        with self.opener(url) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return normalize_ticketmaster_events(payload, city)


def normalize_ticketmaster_events(payload: Dict[str, object], city: str) -> List[EventCandidate]:
    embedded = payload.get("_embedded", {}) if isinstance(payload, dict) else {}
    raw_events = embedded.get("events", []) if isinstance(embedded, dict) else []
    normalized = []
    for item in raw_events:
        candidate = _normalize_ticketmaster_event(item, city)
        if candidate is not None:
            normalized.append(candidate)
    return normalized


def _normalize_ticketmaster_event(item: Dict[str, object], default_city: str) -> Optional[EventCandidate]:
    if not isinstance(item, dict):
        return None

    classifications = item.get("classifications", [])
    classification = classifications[0] if classifications else {}
    segment = classification.get("segment", {}) if isinstance(classification, dict) else {}
    category_name = str(segment.get("name", "community")).lower()

    embedded = item.get("_embedded", {})
    venues = embedded.get("venues", []) if isinstance(embedded, dict) else []
    venue = venues[0] if venues else {}
    city_info = venue.get("city", {}) if isinstance(venue, dict) else {}

    name = str(item.get("name", "Unnamed Event"))
    event_id = str(item.get("id", name.lower().replace(" ", "-")))
    city = str(city_info.get("name", default_city))
    venue_name = str(venue.get("name", "Unknown Venue"))
    dates = item.get("dates", {})
    start = dates.get("start", {}) if isinstance(dates, dict) else {}
    local_date = str(start.get("localDate", "this weekend"))
    summary = str(item.get("info", "")) or str(item.get("pleaseNote", "")) or name

    audience_tags = _audience_tags(category_name, name)
    brand_tags = _brand_tags(category_name, name)
    family_friendly = "family" in name.lower() or category_name in ("family", "arts & theatre")
    visibility_hint = "high" if item.get("promoter") or item.get("priceRanges") else "medium"

    return EventCandidate(
        event_id=event_id,
        name=name,
        city=city,
        date_label=local_date,
        category=_normalize_category(category_name),
        venue_name=venue_name,
        family_friendly=family_friendly,
        visibility_hint=visibility_hint,
        audience_tags=audience_tags,
        brand_tags=brand_tags,
        summary=summary,
    )


def _normalize_category(category_name: str) -> str:
    normalized = category_name.lower()
    if normalized == "sports":
        return "sports"
    if normalized == "music":
        return "music"
    if normalized in ("arts & theatre", "family"):
        return "family"
    return "community"


def _audience_tags(category_name: str, event_name: str) -> List[str]:
    tags = ["general audience"]
    lowered_name = event_name.lower()
    if "family" in lowered_name or category_name in ("family", "arts & theatre"):
        tags.append("family")
    if category_name == "sports":
        tags.append("sports fans")
    if category_name == "music":
        tags.append("music fans")
    return tags


def _brand_tags(category_name: str, event_name: str) -> List[str]:
    tags = ["beverage"]
    normalized = category_name.lower()
    if normalized == "sports":
        tags.extend(["snack", "restaurant"])
    elif normalized == "music":
        tags.extend(["snack"])
    else:
        tags.extend(["cold beverage", "restaurant", "outdoor"])
    if "festival" in event_name.lower():
        tags.append("outdoor")
    return tags


def _date_range_for_timeframe(timeframe: str) -> tuple:
    """Return (startDateTime, endDateTime) in Ticketmaster ISO format."""
    now = datetime.utcnow()
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    lower = timeframe.lower().strip()

    if "weekend" in lower:
        # Find next Saturday
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0 and now.hour >= 18:
            days_until_saturday = 7
        saturday = now + timedelta(days=max(days_until_saturday, 0))
        start = saturday.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=2, hours=23, minutes=59, seconds=59)
    elif "month" in lower or "30" in lower:
        start = now
        end = now + timedelta(days=30)
    elif "next week" in lower:
        days_until_monday = (7 - now.weekday()) % 7 or 7
        start = now + timedelta(days=days_until_monday)
        start = start.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif "today" in lower or "tonight" in lower:
        start = now
        end = now.replace(hour=23, minute=59, second=59)
    else:
        # Default: next 7 days
        start = now
        end = now + timedelta(days=7)

    return start.strftime(fmt), end.strftime(fmt)
