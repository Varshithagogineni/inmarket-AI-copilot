"""Workflow route helpers.

The actual FastAPI router can import these pure functions when dependencies are installed.
"""

from typing import Dict

from app.application.serializers import serialize_run, serialize_run_summary
from app.application.services.run_service import RunService
from app.config.settings import AppSettings
from app.domain.models import CampaignRequest
from app.infra.factories import (
    build_creative_provider,
    build_event_provider,
    build_run_repository,
)


_repository = None
_service = None


def _get_service():
    global _service, _repository
    if _service is None:
        settings = AppSettings.from_env()
        _repository = build_run_repository(settings)
        _service = RunService(
            _repository,
            build_event_provider(settings),
            build_creative_provider(settings),
            prompt_version=settings.prompt_version,
        )
    return _service


def create_run(payload: Dict[str, object]):
    request = CampaignRequest(
        prompt=str(payload.get("prompt", "")),
        city=payload.get("city"),
        timeframe=payload.get("timeframe"),
        brand_category=payload.get("brand_category"),
        audience=payload.get("audience"),
        campaign_goal=payload.get("campaign_goal"),
        requested_outputs=list(payload.get("requested_outputs", [])),
    )
    record = _get_service().create_run(request)
    return serialize_run(record)


def get_run(run_id: str):
    record = _get_service().get_run(run_id)
    if record is None:
        return {"error": "run_not_found", "run_id": run_id}
    return serialize_run(record)


def list_runs():
    records = _get_service().list_runs()
    return {"runs": [serialize_run_summary(record) for record in records]}


def refine_run(run_id: str, payload: Dict[str, object]):
    instruction = str(payload.get("instruction", ""))
    target = str(payload.get("target", "copy"))
    try:
        record = _get_service().refine_run(run_id, instruction=instruction, target=target)
    except ValueError as exc:
        return {"error": "refine_failed", "run_id": run_id, "detail": str(exc)}
    return serialize_run(record)
