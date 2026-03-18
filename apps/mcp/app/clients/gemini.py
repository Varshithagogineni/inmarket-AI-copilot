"""Gemini image generation client – real HTTP implementation."""

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.request import Request, urlopen


@dataclass
class ImageGenerationRequest:
    prompt: str
    style_notes: List[str]


class GeminiImageClient:
    BASE_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-image:generateContent"
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def generate_image(self, request: ImageGenerationRequest) -> Dict[str, object]:
        """Return metadata for a generated image asset."""
        if not self.api_key:
            return {
                "status": "not_configured",
                "provider": "gemini",
                "prompt": request.prompt,
                "style_notes": request.style_notes,
                "asset_uri": None,
                "error": "GEMINI_API_KEY is not configured.",
            }

        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": request.prompt}],
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }

        http_request = Request(
            "{0}?key={1}".format(self.BASE_URL, self.api_key),
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(http_request) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {
                "status": "submitted",
                "provider": "gemini",
                "prompt": request.prompt,
                "style_notes": request.style_notes,
                "asset_uri": _extract_asset_uri(payload),
                "error": None,
            }
        except Exception as exc:
            return {
                "status": "generation_failed",
                "provider": "gemini",
                "prompt": request.prompt,
                "style_notes": request.style_notes,
                "asset_uri": None,
                "error": str(exc),
            }


def _extract_asset_uri(payload: Dict) -> Optional[str]:
    """Pull the image data URI from Gemini's response."""
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
        if "fileData" in part:
            file_data = part["fileData"]
            if isinstance(file_data, dict):
                uri = file_data.get("fileUri")
                if uri:
                    return uri
        if "inlineData" in part:
            inline = part["inlineData"]
            if isinstance(inline, dict) and "data" in inline:
                mime = inline.get("mimeType", "image/png")
                return "data:{0};base64,{1}".format(mime, inline["data"])
    return None
