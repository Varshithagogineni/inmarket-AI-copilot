"""Image-generation provider implementations."""

import json
import os
from typing import Optional
from urllib.request import Request, urlopen

from app.application.services.creative_service import CreativeProvider, MockCreativeProvider
from app.domain.models import GeneratedAsset, ImageConcept


class GeminiCreativeProvider(CreativeProvider):
    """Gemini image-generation adapter.

    The HTTP request is intentionally conservative and may require adjustment once
    real credentials and the target endpoint are finalized.
    """

    BASE_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-image:generateContent"
    )

    def __init__(self, api_key: Optional[str] = None, opener=urlopen):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.opener = opener

    def generate_asset(self, image_concept: ImageConcept) -> GeneratedAsset:
        if not self.api_key:
            return GeneratedAsset(
                provider="gemini",
                status="not_configured",
                prompt_version=image_concept.prompt_version,
                error="GEMINI_API_KEY is not configured.",
            )

        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": image_concept.prompt}],
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        request = Request(
            "{0}?key={1}".format(self.BASE_URL, self.api_key),
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return GeneratedAsset(
                provider="gemini",
                status="submitted",
                prompt_version=image_concept.prompt_version,
                asset_uri=_extract_asset_uri(payload),
                error=None,
            )
        except Exception as exc:
            return GeneratedAsset(
                provider="gemini",
                status="generation_failed",
                prompt_version=image_concept.prompt_version,
                error=str(exc),
            )


def default_creative_provider() -> CreativeProvider:
    return MockCreativeProvider()


def _extract_asset_uri(payload):
    if not isinstance(payload, dict):
        return None
    candidates = payload.get("candidates", [])
    if not candidates:
        return None
    candidate = candidates[0]
    content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    for part in parts:
        if not isinstance(part, dict):
            continue
        # Check for fileData (uploaded file URI)
        if "fileData" in part:
            file_data = part["fileData"]
            if isinstance(file_data, dict):
                uri = file_data.get("fileUri")
                if uri:
                    return uri
        # Check for inline base64 image data
        if "inlineData" in part:
            inline = part["inlineData"]
            if isinstance(inline, dict) and "data" in inline:
                mime = inline.get("mimeType", "image/png")
                return "data:{0};base64,{1}".format(mime, inline["data"])
    return None
