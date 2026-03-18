"""Workflow run lifecycle management."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from app.application.services.creative_service import CreativeProvider
from app.application.services.brief_service import (
    build_campaign_brief,
    build_copy_assets,
    build_image_concept,
)
from app.application.services.refinement_service import refine_workflow_result
from app.application.services.intent_service import normalize_request
from app.application.services.scoring_service import explain_top_choice, rank_events
from app.domain.models import CampaignRequest, EventRecommendation, WorkflowEvent, WorkflowRunRecord, WorkflowStep
from app.domain.models import WorkflowResult
from app.application.orchestrators.activation_run import EventProvider


class RunRepository:
    def save(self, record: WorkflowRunRecord) -> WorkflowRunRecord:
        raise NotImplementedError

    def get(self, run_id: str) -> Optional[WorkflowRunRecord]:
        raise NotImplementedError

    def list(self) -> List[WorkflowRunRecord]:
        raise NotImplementedError


class RunService:
    def __init__(
        self,
        repository: RunRepository,
        provider: EventProvider,
        creative_provider: CreativeProvider,
        prompt_version: str = "v1",
        gemini_api_key: str = "",
    ):
        self.repository = repository
        self.provider = provider
        self.creative_provider = creative_provider
        self.prompt_version = prompt_version
        self.gemini_api_key = gemini_api_key

        # Initialize LangChain agent orchestrator
        self._agent = None
        try:
            from app.application.services.agent_service import AgentOrchestrator
            self._agent = AgentOrchestrator(
                event_provider=provider,
                creative_provider=creative_provider,
                prompt_version=prompt_version,
                gemini_api_key=gemini_api_key,
            )
        except Exception:
            pass  # Fall back to deterministic orchestration

    def create_run(self, request: CampaignRequest) -> WorkflowRunRecord:
        created_at = _utc_now()
        record = WorkflowRunRecord(
            run_id=str(uuid4()),
            status="running",
            request=request,
            created_at=created_at,
            updated_at=created_at,
            steps=_initial_steps(),
            events=[
                WorkflowEvent(
                    timestamp=created_at,
                    event_type="run_created",
                    message="Workflow run created.",
                )
            ],
        )
        self.repository.save(record)

        try:
            if self._agent:
                self._run_with_agent(record, request)
            else:
                self._run_deterministic(record, request)
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            record.updated_at = _utc_now()
            _mark_failed_step(record, str(exc))
            _append_event(record, "run_failed", str(exc))

        self.repository.save(record)
        return record

    def _run_with_agent(self, record: WorkflowRunRecord, request: CampaignRequest):
        """Orchestrate the workflow using the LangChain agent with tool calling."""
        _append_event(record, "agent_started", "LangChain agent orchestrating workflow via tool calling.")

        agent_result = self._agent.run(request)

        intent = agent_result["intent"]
        _mark_step(record, "intent", "completed", "Campaign intent normalized (LLM agent).")
        _append_event(record, "intent_normalized", "Campaign intent normalized via LangChain agent.")

        candidates = agent_result.get("candidates", [])
        if not candidates:
            raise ValueError("No candidate events found for the given request.")
        _mark_step(
            record, "discovery", "completed",
            "Discovered {0} candidate events.".format(len(candidates)),
        )
        _append_event(
            record, "events_discovered",
            "Agent discovered {0} candidate events via search_events tool.".format(len(candidates)),
        )

        evaluations = agent_result.get("evaluations", [])
        if not evaluations:
            raise ValueError("Agent did not produce event rankings.")
        selected, _alts = explain_top_choice(evaluations)
        _mark_step(record, "evaluation", "completed", "Agent scored and ranked candidates.")

        # Build recommendations from agent cache
        briefs = agent_result.get("briefs", {})
        copies = agent_result.get("copies", {})
        image_concepts = agent_result.get("image_concepts", {})
        assets = agent_result.get("assets", {})

        recommendations = []
        for idx in sorted(briefs.keys()):
            if idx >= len(evaluations):
                continue
            ev = evaluations[idx]
            brief = briefs[idx]
            copy = copies.get(idx, build_copy_assets(intent, brief))
            img = image_concepts.get(idx, build_image_concept(intent, brief, prompt_version=self.prompt_version))
            asset = assets.get(idx, self.creative_provider.generate_asset(img))
            recommendations.append(EventRecommendation(
                evaluation=ev,
                campaign_brief=brief,
                copy_assets=copy,
                image_concept=img,
                generated_asset=asset,
            ))

        if not recommendations:
            raise ValueError("Agent did not generate any recommendations.")

        _append_event(
            record, "event_selected",
            "Top picks: {0}.".format(
                " and ".join(r.evaluation.event.name for r in recommendations)
            ),
        )

        primary = recommendations[0]
        record.result = WorkflowResult(
            normalized_intent=intent,
            candidate_evaluations=evaluations,
            selected_event=selected,
            campaign_brief=primary.campaign_brief,
            copy_assets=primary.copy_assets,
            image_concept=primary.image_concept,
            generated_asset=primary.generated_asset,
            recommendations=recommendations,
            asset_versions=[
                _asset_version(revision_id=1, generated_asset=primary.generated_asset)
            ],
        )
        _mark_step(
            record, "brief", "completed",
            "LangChain agent generated briefs and creatives for {0} events.".format(len(recommendations)),
        )
        record.status = "completed"
        record.updated_at = _utc_now()
        _append_event(
            record, "assets_generated",
            "LangChain agent completed workflow. {0}".format(
                agent_result.get("agent_summary", "")[:200]
            ),
        )

    def _run_deterministic(self, record: WorkflowRunRecord, request: CampaignRequest):
        """Fallback: deterministic orchestration without LLM agent."""
        intent = normalize_request(request)
        _mark_step(record, "intent", "completed", "Campaign intent normalized.")
        _append_event(record, "intent_normalized", "Campaign intent normalized.")

        candidate_events = list(self.provider.search(intent.city, intent.timeframe))
        if not candidate_events:
            raise ValueError("No candidate events found for the given request.")
        _mark_step(
            record,
            "discovery",
            "completed",
            "Discovered {0} candidate events.".format(len(candidate_events)),
        )
        _append_event(
            record,
            "events_discovered",
            "Discovered {0} candidate events.".format(len(candidate_events)),
        )

        evaluations = rank_events(intent, candidate_events)
        selected, _alternatives = explain_top_choice(evaluations)
        _mark_step(record, "evaluation", "completed", "Candidates scored and ranked.")

        top_picks = evaluations[:2]
        recommendations = []
        for pick in top_picks:
            rec_brief = build_campaign_brief(intent, pick)
            rec_copy = build_copy_assets(intent, rec_brief)
            rec_image = build_image_concept(intent, rec_brief, prompt_version=self.prompt_version)
            rec_asset = self.creative_provider.generate_asset(rec_image)
            recommendations.append(EventRecommendation(
                evaluation=pick,
                campaign_brief=rec_brief,
                copy_assets=rec_copy,
                image_concept=rec_image,
                generated_asset=rec_asset,
            ))

        _append_event(
            record,
            "event_selected",
            "Top picks: {0}.".format(
                " and ".join(r.evaluation.event.name for r in recommendations)
            ),
        )

        primary = recommendations[0]
        record.result = WorkflowResult(
            normalized_intent=intent,
            candidate_evaluations=evaluations,
            selected_event=selected,
            campaign_brief=primary.campaign_brief,
            copy_assets=primary.copy_assets,
            image_concept=primary.image_concept,
            generated_asset=primary.generated_asset,
            recommendations=recommendations,
            asset_versions=[
                _asset_version(
                    revision_id=1,
                    generated_asset=primary.generated_asset,
                )
            ],
        )
        _mark_step(
            record,
            "brief",
            "completed",
            "Generated briefs and creatives for {0} events.".format(len(recommendations)),
        )
        record.status = "completed"
        record.updated_at = _utc_now()
        _append_event(
            record,
            "assets_generated",
            "Generated campaign brief, copy, and creative asset metadata.",
        )

    def get_run(self, run_id: str) -> Optional[WorkflowRunRecord]:
        return self.repository.get(run_id)

    def list_runs(self) -> List[WorkflowRunRecord]:
        return self.repository.list()

    def refine_run(self, run_id: str, instruction: str, target: str) -> WorkflowRunRecord:
        record = self.repository.get(run_id)
        if record is None:
            raise ValueError("Run not found: {0}".format(run_id))
        if record.result is None:
            raise ValueError("Run has no result to refine: {0}".format(run_id))

        record.result = refine_workflow_result(
            result=record.result,
            instruction=instruction,
            target=target,
            prompt_version=self.prompt_version,
            creative_provider=self.creative_provider,
            applied_at=_utc_now(),
        )
        record.status = "completed"
        record.error = None
        record.updated_at = _utc_now()
        record.steps = _completed_steps(
            "Assets refined for target '{0}'.".format(target)
        )
        _append_event(
            record,
            "run_refined",
            "Applied refinement to {0}: {1}".format(target, instruction),
        )
        self.repository.save(record)
        return record


def _initial_steps() -> List[WorkflowStep]:
    return [
        WorkflowStep(
            key="intent",
            label="Understand request",
            status="running",
            detail="Parsing marketer intent from the prompt.",
        ),
        WorkflowStep(
            key="discovery",
            label="Find events",
            status="pending",
            detail="Searching event candidates for the requested city and timeframe.",
        ),
        WorkflowStep(
            key="evaluation",
            label="Choose event",
            status="pending",
            detail="Ranking candidates against audience, brand, and activation fit.",
        ),
        WorkflowStep(
            key="brief",
            label="Generate assets",
            status="pending",
            detail="Preparing the campaign brief, copy, and image concept.",
        ),
    ]


def _mark_step(record: WorkflowRunRecord, step_key: str, status: str, detail: str) -> None:
    for index, step in enumerate(record.steps):
        if step.key == step_key:
            record.steps[index] = WorkflowStep(
                key=step.key,
                label=step.label,
                status=status,
                detail=detail,
            )
            if status == "completed" and index + 1 < len(record.steps):
                next_step = record.steps[index + 1]
                if next_step.status == "pending":
                    record.steps[index + 1] = WorkflowStep(
                        key=next_step.key,
                        label=next_step.label,
                        status="running",
                        detail=next_step.detail,
                    )
            return


def _mark_failed_step(record: WorkflowRunRecord, detail: str) -> None:
    for index, step in enumerate(record.steps):
        if step.status == "running":
            record.steps[index] = WorkflowStep(
                key=step.key,
                label=step.label,
                status="failed",
                detail=detail,
            )
            return


def _completed_steps(final_detail: str) -> List[WorkflowStep]:
    return [
        WorkflowStep(
            key="intent",
            label="Understand request",
            status="completed",
            detail="Campaign intent normalized.",
        ),
        WorkflowStep(
            key="discovery",
            label="Find events",
            status="completed",
            detail="Event candidates discovered.",
        ),
        WorkflowStep(
            key="evaluation",
            label="Choose event",
            status="completed",
            detail="Candidates scored and ranked.",
        ),
        WorkflowStep(
            key="brief",
            label="Generate assets",
            status="completed",
            detail=final_detail,
        ),
    ]


def _utc_now() -> str:
    return datetime.now(tz=__import__("datetime").timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _asset_version(revision_id, generated_asset):
    from app.domain.models import AssetVersion

    return AssetVersion(
        revision_id=revision_id,
        prompt_version=generated_asset.prompt_version,
        provider=generated_asset.provider,
        status=generated_asset.status,
        asset_uri=generated_asset.asset_uri,
    )


def _append_event(record: WorkflowRunRecord, event_type: str, message: str) -> None:
    record.events.append(
        WorkflowEvent(
            timestamp=_utc_now(),
            event_type=event_type,
            message=message,
        )
    )
