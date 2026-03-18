"""Factories for environment-driven provider selection."""

from app.application.services.creative_service import MockCreativeProvider
from app.config.settings import AppSettings
from app.infra.providers.creative_provider import GeminiCreativeProvider
from app.infra.providers.mock_event_provider import MockEventProvider
from app.infra.providers.ticketmaster_provider import TicketmasterEventProvider
from app.infra.repositories.file_repository import FileRunRepository
from app.infra.repositories.in_memory import InMemoryRunRepository


def build_run_repository(settings: AppSettings):
    if settings.run_repository == "file":
        return FileRunRepository(settings.run_storage_path)
    return InMemoryRunRepository()


def build_event_provider(settings: AppSettings):
    if settings.event_provider == "ticketmaster":
        return TicketmasterEventProvider(api_key=settings.ticketmaster_api_key)
    return MockEventProvider()


def build_creative_provider(settings: AppSettings):
    if settings.creative_provider == "gemini":
        return GeminiCreativeProvider(api_key=settings.gemini_api_key)
    return MockCreativeProvider()
