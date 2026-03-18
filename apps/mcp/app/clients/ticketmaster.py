"""Ticketmaster client – real HTTP implementation."""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass
class TicketmasterSearchParams:
    city: str
    timeframe: str
    keyword: Optional[str] = None
    classification: Optional[str] = None


class TicketmasterClient:
    BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TICKETMASTER_API_KEY")

    def search_events(self, params: TicketmasterSearchParams) -> List[Dict[str, object]]:
        """Return normalized Ticketmaster event payloads."""
        if not self.api_key:
            return []

        start_dt, end_dt = _compute_date_range(params.timeframe)

        query: Dict[str, str] = {
            "apikey": self.api_key,
            "city": params.city,
            "size": "10",
            "sort": "date,asc",
        }
        if start_dt:
            query["startDateTime"] = start_dt
        if end_dt:
            query["endDateTime"] = end_dt
        if params.keyword:
            query["keyword"] = params.keyword
        if params.classification:
            query["classificationName"] = params.classification

        url = "{0}?{1}".format(self.BASE_URL, urlencode(query))
        try:
            with urlopen(url) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []

        return _normalize_events(payload, params.city)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_date_range(timeframe: str):
    """Return (startDateTime, endDateTime) in Ticketmaster ISO format or (None, None)."""
    now = datetime.utcnow()
    tf = timeframe.lower().strip()

    if tf == "this weekend":
        # Saturday of this week
        days_until_sat = (5 - now.weekday()) % 7
        if days_until_sat == 0 and now.weekday() != 5:
            days_until_sat = 7
        saturday = (now + timedelta(days=days_until_sat)).replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = saturday + timedelta(days=1, hours=23, minutes=59, seconds=59)
        return _tm_dt(saturday), _tm_dt(sunday)

    if tf in ("this week", "next 7 days"):
        end = now + timedelta(days=7)
        return _tm_dt(now), _tm_dt(end)

    if tf in ("next week",):
        days_until_monday = (7 - now.weekday()) % 7 or 7
        monday = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return _tm_dt(monday), _tm_dt(sunday)

    if tf in ("this month", "next 30 days"):
        end = now + timedelta(days=30)
        return _tm_dt(now), _tm_dt(end)

    # Fallback: next 7 days
    return _tm_dt(now), _tm_dt(now + timedelta(days=7))


def _tm_dt(dt: datetime) -> str:
    """Format a datetime in Ticketmaster's expected ISO format."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_events(payload: Dict, default_city: str) -> List[Dict[str, object]]:
    embedded = payload.get("_embedded", {}) if isinstance(payload, dict) else {}
    raw_events = embedded.get("events", []) if isinstance(embedded, dict) else []
    results: List[Dict[str, object]] = []
    for item in raw_events:
        normalized = _normalize_event(item, default_city)
        if normalized is not None:
            results.append(normalized)
    return results


def _normalize_event(item: Dict, default_city: str) -> Optional[Dict[str, object]]:
    if not isinstance(item, dict):
        return None

    # Classification / category
    classifications = item.get("classifications", [])
    classification = classifications[0] if classifications else {}
    segment = classification.get("segment", {}) if isinstance(classification, dict) else {}
    category_name = str(segment.get("name", "community")).lower()

    # Venue / city
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
    date_label = str(start.get("localDate", "this weekend"))

    summary = str(item.get("info", "")) or str(item.get("pleaseNote", "")) or name

    audience_tags = _audience_tags(category_name, name)
    brand_tags = _brand_tags(category_name, name)
    family_friendly = "family" in name.lower() or category_name in ("family", "arts & theatre")
    visibility_hint = "high" if item.get("promoter") or item.get("priceRanges") else "medium"

    return {
        "event_id": event_id,
        "name": name,
        "city": city,
        "date_label": date_label,
        "category": _normalize_category(category_name),
        "venue_name": venue_name,
        "summary": summary,
        "audience_tags": audience_tags,
        "brand_tags": brand_tags,
        "family_friendly": family_friendly,
        "visibility_hint": visibility_hint,
    }


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
    lowered = event_name.lower()
    if "family" in lowered or category_name in ("family", "arts & theatre"):
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
