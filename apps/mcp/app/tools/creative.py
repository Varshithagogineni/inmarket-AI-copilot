"""Creative generation tools."""

from app.clients.gemini import GeminiImageClient, ImageGenerationRequest
from app.schemas import MCPToolResponse


def generate_campaign_brief(selected_event: dict, intent: dict):
    event_name = selected_event.get("name", "Selected Event")
    city = intent.get("city", "target city")
    brand_category = intent.get("brand_category", "brand")
    payload = {
        "event_name": event_name,
        "campaign_angle": "Connect {0} to the momentum around {1} in {2}.".format(
            brand_category, event_name, city
        ),
        "cta_direction": "Convert event attention into a nearby action.",
    }
    return MCPToolResponse(status="ok", payload=payload).to_dict()


def generate_copy_variants(brief: dict):
    event_name = brief.get("event_name", "the event")
    return MCPToolResponse(
        status="ok",
        payload={
            "headline": "Own the moment at {0}".format(event_name),
            "caption": "Show up around {0} with creative built for the local crowd.".format(
                event_name
            ),
            "cta": "Act nearby today",
        },
    ).to_dict()


def generate_image_prompt(brief: dict):
    event_name = brief.get("event_name", "the event")
    prompt = "Create a polished local activation poster tied to {0} with bold headline space and brand-safe styling.".format(
        event_name
    )
    return MCPToolResponse(status="ok", payload={"prompt": prompt}).to_dict()


def generate_draft_poster(prompt: str, style_notes=None):
    client = GeminiImageClient()
    payload = client.generate_image(
        ImageGenerationRequest(prompt=prompt, style_notes=style_notes or [])
    )
    return MCPToolResponse(status="ok", payload=payload).to_dict()

