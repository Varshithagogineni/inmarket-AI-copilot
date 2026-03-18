"""Environment-backed application settings."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    run_repository: str = "memory"
    run_storage_path: str = "data/runs.json"
    event_provider: str = "mock"
    creative_provider: str = "mock"
    prompt_version: str = "v1"
    ticketmaster_api_key: str = ""
    gemini_api_key: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            run_repository=os.getenv("RUN_REPOSITORY", "memory").strip().lower(),
            run_storage_path=os.getenv("RUN_STORAGE_PATH", "data/runs.json").strip()
            or "data/runs.json",
            event_provider=os.getenv("EVENT_PROVIDER", "mock").strip().lower(),
            creative_provider=os.getenv("CREATIVE_PROVIDER", "mock").strip().lower(),
            prompt_version=os.getenv("PROMPT_VERSION", "v1").strip() or "v1",
            ticketmaster_api_key=os.getenv("TICKETMASTER_API_KEY", "").strip(),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        )
