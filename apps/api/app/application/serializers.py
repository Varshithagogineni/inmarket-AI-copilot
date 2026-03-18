"""Serialization helpers for API responses."""

from typing import Dict, List

from app.domain.models import EventEvaluation, WorkflowRunRecord, WorkflowStep


def serialize_run(record: WorkflowRunRecord) -> Dict[str, object]:
    payload = {
        "run_id": record.run_id,
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "request": _serialize_request(record),
        "steps": [serialize_step(step) for step in record.steps],
        "events": [item.__dict__ for item in record.events],
        "error": record.error,
    }
    if record.result is not None:
        payload.update(serialize_result(record.result))
    return payload


def serialize_run_summary(record: WorkflowRunRecord) -> Dict[str, object]:
    selected_event_name = None
    if record.result is not None:
        selected_event_name = record.result.selected_event.event.name
    return {
        "run_id": record.run_id,
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "prompt": record.request.prompt,
        "selected_event_name": selected_event_name,
        "event_count": len(record.events),
    }


def serialize_step(step: WorkflowStep) -> Dict[str, str]:
    return {
        "key": step.key,
        "label": step.label,
        "status": step.status,
        "detail": step.detail,
    }


def serialize_result(result) -> Dict[str, object]:
    alternatives = result.candidate_evaluations[2:5]
    recommendations = getattr(result, "recommendations", [])
    return {
        "normalized_intent": result.normalized_intent.__dict__,
        "selected_event": serialize_evaluation(result.selected_event),
        "alternative_events": [serialize_evaluation(item) for item in alternatives],
        "recommendations": [_serialize_recommendation(r) for r in recommendations],
        "campaign_brief": result.campaign_brief.__dict__,
        "copy_assets": result.copy_assets.__dict__,
        "image_concept": result.image_concept.__dict__,
        "generated_asset": result.generated_asset.__dict__,
        "revision_id": result.revision_id,
        "refinement_history": [item.__dict__ for item in result.refinement_history],
        "asset_versions": [item.__dict__ for item in result.asset_versions],
    }


def _serialize_recommendation(rec) -> Dict[str, object]:
    return {
        "event": serialize_evaluation(rec.evaluation),
        "campaign_brief": rec.campaign_brief.__dict__,
        "copy_assets": rec.copy_assets.__dict__,
        "image_concept": rec.image_concept.__dict__,
        "generated_asset": rec.generated_asset.__dict__,
    }


def serialize_evaluation(evaluation: EventEvaluation) -> Dict[str, object]:
    return {
        "event_id": evaluation.event.event_id,
        "name": evaluation.event.name,
        "city": evaluation.event.city,
        "date_label": evaluation.event.date_label,
        "category": evaluation.event.category,
        "venue_name": evaluation.event.venue_name,
        "score": evaluation.total_score,
        "rationale": evaluation.rationale,
        "score_breakdown": evaluation.score_breakdown,
        "summary": evaluation.event.summary,
    }


def _serialize_request(record: WorkflowRunRecord) -> Dict[str, object]:
    return {
        "prompt": record.request.prompt,
        "city": record.request.city,
        "timeframe": record.request.timeframe,
        "brand_category": record.request.brand_category,
        "audience": record.request.audience,
        "campaign_goal": record.request.campaign_goal,
        "requested_outputs": list(record.request.requested_outputs),
    }
