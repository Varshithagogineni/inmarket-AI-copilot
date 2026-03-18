"""JSON-backed repository for local persistence."""

import json
import os
from dataclasses import asdict
from typing import List, Optional

from app.application.services.run_service import RunRepository
from app.domain.models import (
    AssetVersion,
    CampaignBrief,
    CampaignRequest,
    CopyAssetSet,
    EventCandidate,
    EventEvaluation,
    GeneratedAsset,
    ImageConcept,
    NormalizedIntent,
    RefinementRecord,
    WorkflowEvent,
    WorkflowResult,
    WorkflowRunRecord,
    WorkflowStep,
)


class FileRunRepository(RunRepository):
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        directory = os.path.dirname(storage_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def save(self, record: WorkflowRunRecord) -> WorkflowRunRecord:
        records = {item.run_id: item for item in self.list()}
        records[record.run_id] = record
        payload = [self._serialize_record(records[key]) for key in sorted(records.keys())]
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return record

    def get(self, run_id: str) -> Optional[WorkflowRunRecord]:
        for record in self.list():
            if record.run_id == run_id:
                return record
        return None

    def list(self) -> List[WorkflowRunRecord]:
        if not os.path.exists(self.storage_path):
            return []
        with open(self.storage_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return [self._deserialize_record(item) for item in payload]

    def _serialize_record(self, record: WorkflowRunRecord):
        return asdict(record)

    def _deserialize_record(self, payload):
        result_payload = payload.get("result")
        result = self._deserialize_result(result_payload) if result_payload else None
        return WorkflowRunRecord(
            run_id=payload["run_id"],
            status=payload["status"],
            request=CampaignRequest(**payload["request"]),
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            steps=[WorkflowStep(**step) for step in payload.get("steps", [])],
            events=[WorkflowEvent(**item) for item in payload.get("events", [])],
            result=result,
            error=payload.get("error"),
        )

    def _deserialize_result(self, payload):
        evaluations = []
        for item in payload.get("candidate_evaluations", []):
            evaluations.append(
                EventEvaluation(
                    event=EventCandidate(**item["event"]),
                    total_score=item["total_score"],
                    score_breakdown=item["score_breakdown"],
                    rationale=item["rationale"],
                )
            )

        return WorkflowResult(
            normalized_intent=NormalizedIntent(**payload["normalized_intent"]),
            candidate_evaluations=evaluations,
            selected_event=EventEvaluation(
                event=EventCandidate(**payload["selected_event"]["event"]),
                total_score=payload["selected_event"]["total_score"],
                score_breakdown=payload["selected_event"]["score_breakdown"],
                rationale=payload["selected_event"]["rationale"],
            ),
            campaign_brief=CampaignBrief(**payload["campaign_brief"]),
            copy_assets=CopyAssetSet(**payload["copy_assets"]),
            image_concept=ImageConcept(**payload["image_concept"]),
            generated_asset=GeneratedAsset(**payload["generated_asset"]),
            revision_id=payload.get("revision_id", 1),
            refinement_history=[
                RefinementRecord(**item) for item in payload.get("refinement_history", [])
            ],
            asset_versions=[
                AssetVersion(**item) for item in payload.get("asset_versions", [])
            ],
        )
