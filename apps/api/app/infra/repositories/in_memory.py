"""In-memory repository used for local development and tests."""

from typing import Dict, Optional

from app.application.services.run_service import RunRepository
from app.domain.models import WorkflowRunRecord


class InMemoryRunRepository(RunRepository):
    def __init__(self):
        self._records: Dict[str, WorkflowRunRecord] = {}

    def save(self, record: WorkflowRunRecord) -> WorkflowRunRecord:
        self._records[record.run_id] = record
        return record

    def get(self, run_id: str) -> Optional[WorkflowRunRecord]:
        return self._records.get(run_id)

    def list(self):
        return [self._records[key] for key in sorted(self._records.keys())]
