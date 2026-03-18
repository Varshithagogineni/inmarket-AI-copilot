"""FastMCP server entrypoint."""

from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[2] / ".env"
    if not _env_path.exists():
        _env_path = Path(__file__).resolve().parents[3] / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - dependency is not installed in this environment.
    FastMCP = None

from app.tools.creative import (
    generate_campaign_brief,
    generate_copy_variants,
    generate_draft_poster,
    generate_image_prompt,
)
from app.tools.events import get_event_details, search_events
from app.tools.strategy import rank_event_candidates, score_event_fit


def create_server():
    if FastMCP is None:
        raise RuntimeError("FastMCP is not installed. Install project dependencies to run the MCP server.")

    server = FastMCP("event-surge-mcp")
    server.tool(search_events)
    server.tool(get_event_details)
    server.tool(score_event_fit)
    server.tool(rank_event_candidates)
    server.tool(generate_campaign_brief)
    server.tool(generate_copy_variants)
    server.tool(generate_image_prompt)
    server.tool(generate_draft_poster)
    return server


server = create_server() if FastMCP is not None else None
