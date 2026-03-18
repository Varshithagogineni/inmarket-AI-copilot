"""Event discovery tools."""

from app.clients.ticketmaster import TicketmasterClient, TicketmasterSearchParams
from app.schemas import MCPToolResponse


def search_events(city: str, timeframe: str, keyword: str = "", classification: str = ""):
    client = TicketmasterClient()
    payload = client.search_events(
        TicketmasterSearchParams(
            city=city,
            timeframe=timeframe,
            keyword=keyword or None,
            classification=classification or None,
        )
    )
    return MCPToolResponse(status="ok", payload={"events": payload}).to_dict()


def get_event_details(event_id: str):
    return MCPToolResponse(
        status="not_implemented",
        payload={"event_id": event_id, "message": "Ticketmaster detail lookup not wired yet."},
    ).to_dict()

