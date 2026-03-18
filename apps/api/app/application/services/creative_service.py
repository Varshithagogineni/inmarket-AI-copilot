"""Creative generation provider abstractions."""

from typing import Protocol

from app.domain.models import GeneratedAsset, ImageConcept


class CreativeProvider(Protocol):
    def generate_asset(self, image_concept: ImageConcept) -> GeneratedAsset:
        """Generate or register a creative asset for the workflow."""


class MockCreativeProvider:
    def generate_asset(self, image_concept: ImageConcept) -> GeneratedAsset:
        return GeneratedAsset(
            provider="mock",
            status="preview_ready",
            prompt_version=image_concept.prompt_version,
            asset_uri=None,
            error=None,
        )
