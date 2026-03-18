"""LangChain agent that orchestrates the activation workflow via tool calling.

The agent uses Google Gemini as the LLM and exposes MCP-aligned tools
(event search, scoring, brief/copy/image generation) so the model decides
which tools to invoke and in what order.

Tool calls are routed through the MCP Bridge when available, ensuring
the LangChain agent interacts with the MCP Server's standardized tools.
Copy and brief generation uses LLM-powered generation via Gemini for
contextual, creative output instead of string templates.
"""

import json
import os
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from app.application.services.creative_service import CreativeProvider
from app.application.orchestrators.activation_run import EventProvider
from app.application.services.scoring_service import rank_events, explain_top_choice
from app.application.services.brief_service import (
    build_campaign_brief,
    build_copy_assets,
    build_image_concept,
)
from app.application.services.intent_service import normalize_request
from app.domain.models import (
    CampaignBrief,
    CampaignRequest,
    CopyAssetSet,
    EventCandidate,
    EventEvaluation,
    EventRecommendation,
    ImageConcept,
    NormalizedIntent,
)

# ---------------------------------------------------------------------------
# Module-level references set by AgentOrchestrator.configure()
# ---------------------------------------------------------------------------
_event_provider: Optional[EventProvider] = None
_creative_provider: Optional[CreativeProvider] = None
_prompt_version: str = "v1"
_gemini_api_key: str = ""
_mcp_bridge = None  # MCP Bridge instance for routing tool calls

# Cache for inter-tool state within a single agent run
_run_cache: dict = {}


def _reset_cache():
    global _run_cache
    _run_cache = {}


def _try_llm_brief(intent, selected):
    """Attempt LLM-generated brief; fall back to template."""
    try:
        from app.application.services.llm_service import generate_brief_with_llm
        result = generate_brief_with_llm(intent, selected, api_key=_gemini_api_key)
        if result:
            return result
    except Exception:
        pass
    return build_campaign_brief(intent, selected)


def _try_llm_copy(intent, brief):
    """Attempt LLM-generated copy; fall back to template."""
    try:
        from app.application.services.llm_service import generate_copy_with_llm
        result = generate_copy_with_llm(intent, brief, api_key=_gemini_api_key)
        if result:
            return result
    except Exception:
        pass
    return build_copy_assets(intent, brief)


# ---------------------------------------------------------------------------
# LangChain Tools — routed through MCP Bridge when available
# ---------------------------------------------------------------------------

@tool
def search_events(city: str, timeframe: str) -> str:
    """Search for upcoming events in a city within a timeframe.

    Use this tool to discover candidate events for a marketing activation campaign.
    Returns a list of events with details like name, venue, category, and date.
    This tool calls the MCP Server's search_events function via the MCP Bridge.
    """
    # Try MCP Bridge first (routes through MCP server protocol)
    if _mcp_bridge is not None:
        try:
            mcp_result = _mcp_bridge.call_tool("search_events", {
                "city": city, "timeframe": timeframe
            })
            mcp_events = mcp_result.get("payload", {}).get("events", [])
            if mcp_events:
                # Convert MCP dicts to EventCandidate objects for cache
                candidates = []
                for e in mcp_events:
                    candidates.append(EventCandidate(
                        event_id=e.get("event_id", ""),
                        name=e.get("name", ""),
                        city=e.get("city", city),
                        date_label=e.get("date_label", ""),
                        category=e.get("category", "community"),
                        venue_name=e.get("venue_name", ""),
                        family_friendly=e.get("family_friendly", False),
                        visibility_hint=e.get("visibility_hint", "medium"),
                        audience_tags=e.get("audience_tags", []),
                        brand_tags=e.get("brand_tags", []),
                        summary=e.get("summary", ""),
                    ))
                _run_cache["candidates"] = candidates
                _run_cache["mcp_routed"] = True
                return json.dumps({
                    "status": "ok",
                    "source": "mcp_server",
                    "event_count": len(candidates),
                    "events": mcp_events,
                })
        except Exception:
            pass  # Fall through to direct provider call

    # Fallback: direct provider call
    if _event_provider is None:
        return json.dumps({"error": "Event provider not configured"})

    candidates = list(_event_provider.search(city, timeframe))
    _run_cache["candidates"] = candidates

    events_out = []
    for c in candidates:
        events_out.append({
            "event_id": c.event_id,
            "name": c.name,
            "city": c.city,
            "date_label": c.date_label,
            "category": c.category,
            "venue_name": c.venue_name,
            "family_friendly": c.family_friendly,
            "visibility_hint": c.visibility_hint,
        })
    return json.dumps({"status": "ok", "source": "direct_provider", "event_count": len(events_out), "events": events_out})


@tool
def rank_event_candidates(intent_json: str) -> str:
    """Rank previously discovered events against the campaign intent.

    Scores each event on city fit, audience fit, brand fit, category fit, and visibility.
    Pass the normalized intent as a JSON string with keys: city, timeframe,
    brand_category, audience, campaign_goal, constraints.
    This tool mirrors the MCP Server's rank_event_candidates function.
    """
    candidates = _run_cache.get("candidates", [])
    if not candidates:
        return json.dumps({"error": "No candidates found. Call search_events first."})

    intent_data = json.loads(intent_json)
    intent = NormalizedIntent(
        city=intent_data.get("city", ""),
        timeframe=intent_data.get("timeframe", ""),
        brand_category=intent_data.get("brand_category", ""),
        audience=intent_data.get("audience", ""),
        campaign_goal=intent_data.get("campaign_goal", ""),
        constraints=intent_data.get("constraints", []),
    )

    evaluations = rank_events(intent, candidates)
    _run_cache["evaluations"] = evaluations
    _run_cache["intent"] = intent

    ranked = []
    for ev in evaluations[:5]:
        ranked.append({
            "name": ev.event.name,
            "total_score": ev.total_score,
            "score_breakdown": ev.score_breakdown,
            "rationale": ev.rationale,
        })
    return json.dumps({"status": "ok", "ranked_events": ranked})


@tool
def generate_campaign_brief(event_index: int) -> str:
    """Generate a campaign brief for a ranked event using LLM.

    Pass event_index (0-based) into the ranked list to select which event.
    Returns campaign angle, message direction, CTA, and activation use case.
    Uses Gemini LLM for contextual, creative brief generation.
    """
    evaluations = _run_cache.get("evaluations", [])
    intent = _run_cache.get("intent")
    if not evaluations or intent is None:
        return json.dumps({"error": "Rank events first."})
    if event_index >= len(evaluations):
        event_index = 0

    selected = evaluations[event_index]

    # Use LLM-powered brief generation (falls back to template)
    brief = _try_llm_brief(intent, selected)

    # Store in cache for downstream tools
    _run_cache.setdefault("briefs", {})[event_index] = brief
    _run_cache.setdefault("selected_evals", {})[event_index] = selected

    return json.dumps({
        "status": "ok",
        "event_name": brief.event_name,
        "campaign_angle": brief.campaign_angle,
        "message_direction": brief.message_direction,
        "cta_direction": brief.cta_direction,
        "activation_use_case": brief.activation_use_case,
    })


@tool
def generate_copy_assets(event_index: int) -> str:
    """Generate marketing copy (headline, social caption, CTA, promo text) for a ranked event.

    Call generate_campaign_brief for this event_index first.
    Uses Gemini LLM for contextual, creative copy generation.
    """
    intent = _run_cache.get("intent")
    brief = _run_cache.get("briefs", {}).get(event_index)
    if not brief or not intent:
        return json.dumps({"error": "Generate campaign brief first for event_index={0}".format(event_index)})

    # Use LLM-powered copy generation (falls back to template)
    copy = _try_llm_copy(intent, brief)
    _run_cache.setdefault("copies", {})[event_index] = copy

    return json.dumps({
        "status": "ok",
        "headline": copy.headline,
        "social_caption": copy.social_caption,
        "cta": copy.cta,
        "promo_text": copy.promo_text,
    })


@tool
def generate_image_concept(event_index: int) -> str:
    """Generate an image prompt and style notes for a poster creative.

    Call generate_campaign_brief for this event_index first.
    """
    intent = _run_cache.get("intent")
    brief = _run_cache.get("briefs", {}).get(event_index)
    if not brief or not intent:
        return json.dumps({"error": "Generate campaign brief first for event_index={0}".format(event_index)})

    concept = build_image_concept(intent, brief, prompt_version=_prompt_version)
    _run_cache.setdefault("image_concepts", {})[event_index] = concept

    return json.dumps({
        "status": "ok",
        "prompt": concept.prompt,
        "alt_text": concept.alt_text,
        "style_notes": concept.style_notes,
        "prompt_version": concept.prompt_version,
    })


@tool
def generate_draft_poster(event_index: int) -> str:
    """Generate a draft poster image using the AI image provider.

    Call generate_image_concept for this event_index first.
    Returns an asset URI (base64 data URI or URL).
    This tool calls the creative provider (Gemini image generation).
    """
    concept = _run_cache.get("image_concepts", {}).get(event_index)
    if not concept:
        return json.dumps({"error": "Generate image concept first for event_index={0}".format(event_index)})
    if _creative_provider is None:
        return json.dumps({"error": "Creative provider not configured"})

    asset = _creative_provider.generate_asset(concept)
    _run_cache.setdefault("assets", {})[event_index] = asset

    return json.dumps({
        "status": "ok",
        "provider": asset.provider,
        "status_detail": asset.status,
        "asset_uri_length": len(asset.asset_uri) if asset.asset_uri else 0,
        "error": asset.error,
    })


# ---------------------------------------------------------------------------
# All tools available to the agent
# ---------------------------------------------------------------------------
AGENT_TOOLS = [
    search_events,
    rank_event_candidates,
    generate_campaign_brief,
    generate_copy_assets,
    generate_image_concept,
    generate_draft_poster,
]

# ---------------------------------------------------------------------------
# System prompt — instructs the agent on its role and tool-calling strategy
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an Event Surge Activation Copilot — an AI marketing strategist that helps brands create localized campaign activations tied to real upcoming events.

Your job is to take a marketer's campaign request and execute a multi-step workflow using the tools available to you:

1. **Search Events** — Use `search_events` to find upcoming events in the target city and timeframe.
2. **Rank Events** — Use `rank_event_candidates` to score and rank the events against the campaign intent (audience, brand, constraints).
3. **Generate Recommendations** — For the TOP 2 ranked events (index 0 and 1), call these tools in order:
   a. `generate_campaign_brief` — create the campaign strategy
   b. `generate_copy_assets` — create headline, caption, CTA, promo text
   c. `generate_image_concept` — create the image prompt and style notes
   d. `generate_draft_poster` — generate the actual poster image

IMPORTANT RULES:
- Always search for events FIRST before ranking.
- Always generate briefs/copy/image for the TOP 2 events (indices 0 and 1).
- Call tools in the correct dependency order: search → rank → brief → copy → image → poster.
- After completing all tool calls, provide a brief summary of what you found and recommended.
- Be concise in your final summary. The detailed data is in the tool results.
"""


# ---------------------------------------------------------------------------
# AgentOrchestrator — creates and runs the LangChain agent
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """Wraps the LangChain agent with Gemini LLM and MCP-aligned tools.

    Tool calls are routed through the MCP Bridge when available, ensuring
    the agent interacts with MCP Server tools via the MCP protocol.
    """

    def __init__(
        self,
        event_provider: EventProvider,
        creative_provider: CreativeProvider,
        prompt_version: str = "v1",
        gemini_api_key: str = "",
    ):
        self.event_provider = event_provider
        self.creative_provider = creative_provider
        self.prompt_version = prompt_version
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.gemini_api_key,
            temperature=0.3,
        )
        self.llm_with_tools = self.llm.bind_tools(AGENT_TOOLS)

        # Initialize MCP Bridge for routing tool calls through MCP server
        self._mcp_bridge = None
        try:
            from app.infra.mcp_bridge import get_mcp_bridge
            self._mcp_bridge = get_mcp_bridge()
        except Exception:
            pass  # MCP bridge unavailable; tools will call providers directly

    def configure_tools(self):
        """Set module-level provider references so tools can access them."""
        global _event_provider, _creative_provider, _prompt_version, _gemini_api_key, _mcp_bridge
        _event_provider = self.event_provider
        _creative_provider = self.creative_provider
        _prompt_version = self.prompt_version
        _gemini_api_key = self.gemini_api_key
        _mcp_bridge = self._mcp_bridge

    def run(self, request: CampaignRequest) -> dict:
        """Execute the full activation workflow via the LangChain agent.

        Returns a dict with normalized_intent, evaluations, and recommendations
        ready to be assembled into a WorkflowResult.
        """
        self.configure_tools()
        _reset_cache()

        # Normalize intent first (fast, deterministic)
        intent = normalize_request(request)
        _run_cache["intent"] = intent

        # Build the user message for the agent
        user_msg = (
            "I need an event-based marketing activation campaign.\n\n"
            "Campaign request: {prompt}\n"
            "City: {city}\n"
            "Timeframe: {timeframe}\n"
            "Brand category: {brand_category}\n"
            "Target audience: {audience}\n"
            "Campaign goal: {campaign_goal}\n"
            "Constraints: {constraints}\n\n"
            "Please search for events, rank them, and generate full creative "
            "recommendations for the top 2 events."
        ).format(
            prompt=request.prompt,
            city=intent.city,
            timeframe=intent.timeframe,
            brand_category=intent.brand_category,
            audience=intent.audience,
            campaign_goal=intent.campaign_goal,
            constraints=", ".join(intent.constraints) if intent.constraints else "none",
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ]

        # Agentic loop: keep calling tools until the LLM is done
        max_iterations = 20
        for _ in range(max_iterations):
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            # Execute each tool call
            from langchain_core.messages import ToolMessage
            for tc in response.tool_calls:
                tool_fn = _get_tool_by_name(tc["name"])
                if tool_fn:
                    result = tool_fn.invoke(tc["args"])
                else:
                    result = json.dumps({"error": "Unknown tool: {0}".format(tc["name"])})
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        # Assemble results from cache
        return {
            "intent": _run_cache.get("intent", intent),
            "candidates": _run_cache.get("candidates", []),
            "evaluations": _run_cache.get("evaluations", []),
            "briefs": _run_cache.get("briefs", {}),
            "copies": _run_cache.get("copies", {}),
            "image_concepts": _run_cache.get("image_concepts", {}),
            "assets": _run_cache.get("assets", {}),
            "agent_summary": response.content if response else "",
            "mcp_routed": _run_cache.get("mcp_routed", False),
        }


def _get_tool_by_name(name: str):
    for t in AGENT_TOOLS:
        if t.name == name:
            return t
    return None
