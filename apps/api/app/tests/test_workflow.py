import unittest
from tempfile import TemporaryDirectory

from app.application.serializers import serialize_run
from app.application.services.creative_service import MockCreativeProvider
from app.application.services.refinement_service import refine_workflow_result
from app.application.services.run_service import RunService
from app.application.orchestrators.activation_run import run_activation_workflow
from app.application.services.intent_service import normalize_request
from app.application.services.scoring_service import rank_events
from app.config.settings import AppSettings
from app.domain.models import CampaignRequest
from app.infra.factories import build_creative_provider, build_event_provider, build_run_repository
from app.infra.providers.mock_event_provider import MockEventProvider
from app.infra.providers.creative_provider import GeminiCreativeProvider
from app.infra.providers.ticketmaster_provider import normalize_ticketmaster_events
from app.infra.repositories.file_repository import FileRunRepository
from app.infra.repositories.in_memory import InMemoryRunRepository


class IntentNormalizationTests(unittest.TestCase):
    def test_infers_defaults_when_prompt_is_sparse(self):
        request = CampaignRequest(prompt="Need a local activation idea")

        intent = normalize_request(request)

        self.assertEqual(intent.city, "Dallas")
        self.assertEqual(intent.timeframe, "this weekend")
        self.assertIn("poster", intent.requested_outputs)

    def test_detects_family_constraint_and_city(self):
        request = CampaignRequest(
            prompt="Find a family-friendly event in Houston this weekend for a snack brand"
        )

        intent = normalize_request(request)

        self.assertEqual(intent.city, "Houston")
        self.assertIn("family_friendly", intent.constraints)
        self.assertEqual(intent.brand_category, "snack")


class ScoringTests(unittest.TestCase):
    def test_family_friendly_event_beats_non_family_event(self):
        intent = normalize_request(
            CampaignRequest(
                prompt="Find the best family-friendly event in Dallas this weekend for a cold beverage brand"
            )
        )
        provider = MockEventProvider()
        events = list(provider.search("Dallas", "this weekend"))

        evaluations = rank_events(intent, events)

        self.assertEqual(evaluations[0].event.name, "Dallas Family Festival")
        self.assertGreater(evaluations[0].total_score, evaluations[1].total_score)

    def test_empty_events_returns_empty_ranking(self):
        intent = normalize_request(CampaignRequest(prompt="Any event in Dallas"))

        evaluations = rank_events(intent, [])

        self.assertEqual(evaluations, [])


class WorkflowTests(unittest.TestCase):
    def test_workflow_returns_brief_copy_and_image_concept(self):
        request = CampaignRequest(
            prompt="Find the best family-friendly event in Dallas this weekend for promoting a cold beverage brand."
        )

        result = run_activation_workflow(request, MockEventProvider())

        self.assertEqual(result.selected_event.event.name, "Dallas Family Festival")
        self.assertIn("Dallas Family Festival", result.campaign_brief.event_name)
        self.assertIn("Dallas", result.image_concept.prompt)

    def test_workflow_raises_when_provider_returns_nothing(self):
        class EmptyProvider:
            def search(self, city, timeframe):
                return []

        with self.assertRaises(ValueError):
            run_activation_workflow(CampaignRequest(prompt="Find an event in El Paso"), EmptyProvider())


class RunServiceTests(unittest.TestCase):
    def test_create_run_persists_completed_record(self):
        service = RunService(
            InMemoryRunRepository(), MockEventProvider(), MockCreativeProvider()
        )
        request = CampaignRequest(
            prompt="Find the best family-friendly event in Dallas this weekend for promoting a cold beverage brand."
        )

        record = service.create_run(request)

        self.assertEqual(record.status, "completed")
        self.assertIsNotNone(record.result)
        self.assertEqual(record.steps[-1].status, "completed")
        self.assertEqual(record.result.generated_asset.status, "preview_ready")
        self.assertEqual(record.result.revision_id, 1)
        self.assertTrue(record.created_at.endswith("Z"))
        self.assertGreaterEqual(len(record.events), 4)

    def test_serialized_run_contains_alternatives_and_steps(self):
        service = RunService(
            InMemoryRunRepository(), MockEventProvider(), MockCreativeProvider()
        )
        record = service.create_run(CampaignRequest(prompt="Find an event in Dallas this weekend"))

        payload = serialize_run(record)

        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["steps"])
        self.assertIn("alternative_events", payload)
        self.assertIn("generated_asset", payload)
        self.assertIn("created_at", payload)
        self.assertIn("revision_id", payload)
        self.assertIn("events", payload)

    def test_failed_run_marks_current_step_as_failed(self):
        class EmptyProvider:
            def search(self, city, timeframe):
                return []

        service = RunService(InMemoryRunRepository(), EmptyProvider(), MockCreativeProvider())
        record = service.create_run(CampaignRequest(prompt="Find an event in El Paso"))

        self.assertEqual(record.status, "failed")
        self.assertEqual(record.steps[1].status, "failed")
        self.assertIn("No candidate events found", record.error)

    def test_list_runs_returns_saved_records(self):
        repository = InMemoryRunRepository()
        service = RunService(repository, MockEventProvider(), MockCreativeProvider())
        service.create_run(CampaignRequest(prompt="Find an event in Dallas this weekend"))
        service.create_run(CampaignRequest(prompt="Find an event in Houston this weekend"))

        records = service.list_runs()

        self.assertEqual(len(records), 2)

    def test_refine_run_updates_copy_without_changing_selected_event(self):
        service = RunService(
            InMemoryRunRepository(), MockEventProvider(), MockCreativeProvider()
        )
        record = service.create_run(CampaignRequest(prompt="Find an event in Dallas this weekend"))

        refined = service.refine_run(
            record.run_id,
            instruction="Make it more energetic",
            target="copy",
        )

        self.assertEqual(
            refined.result.selected_event.event.name, record.result.selected_event.event.name
        )
        self.assertIn("Make it more energetic", refined.result.copy_assets.headline)
        self.assertEqual(refined.steps[-1].status, "completed")
        self.assertEqual(refined.result.revision_id, 2)
        self.assertEqual(len(refined.result.refinement_history), 1)
        self.assertEqual(refined.events[-1].event_type, "run_refined")


class TicketmasterNormalizationTests(unittest.TestCase):
    def test_normalize_ticketmaster_events_maps_common_fields(self):
        payload = {
            "_embedded": {
                "events": [
                    {
                        "id": "tm-1",
                        "name": "Dallas Summer Festival",
                        "dates": {"start": {"localDate": "2026-03-21"}},
                        "classifications": [{"segment": {"name": "Music"}}],
                        "_embedded": {
                            "venues": [
                                {
                                    "name": "Fair Park",
                                    "city": {"name": "Dallas"},
                                }
                            ]
                        },
                        "info": "Outdoor live music festival",
                        "priceRanges": [{"min": 25, "max": 80}],
                    }
                ]
            }
        }

        events = normalize_ticketmaster_events(payload, "Dallas")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Dallas Summer Festival")
        self.assertEqual(events[0].category, "music")
        self.assertIn("snack", events[0].brand_tags)
        self.assertEqual(events[0].visibility_hint, "high")


class SettingsAndFactoryTests(unittest.TestCase):
    def test_app_settings_defaults_to_mock_modes(self):
        settings = AppSettings()

        self.assertEqual(settings.run_repository, "memory")
        self.assertEqual(settings.event_provider, "mock")
        self.assertEqual(settings.creative_provider, "mock")
        self.assertEqual(settings.prompt_version, "v1")

    def test_factories_select_mock_or_real_providers(self):
        mock_settings = AppSettings()
        real_settings = AppSettings(
            event_provider="ticketmaster",
            creative_provider="gemini",
            ticketmaster_api_key="tm-key",
            gemini_api_key="gm-key",
            run_repository="file",
            run_storage_path="data/test-runs.json",
        )

        self.assertIsInstance(build_event_provider(mock_settings), MockEventProvider)
        self.assertIsInstance(build_creative_provider(mock_settings), MockCreativeProvider)
        self.assertIsInstance(build_run_repository(mock_settings), InMemoryRunRepository)
        self.assertEqual(build_event_provider(real_settings).api_key, "tm-key")
        self.assertIsInstance(build_creative_provider(real_settings), GeminiCreativeProvider)
        self.assertIsInstance(build_run_repository(real_settings), FileRunRepository)


class RefinementServiceTests(unittest.TestCase):
    def test_refine_image_updates_style_notes_and_asset_metadata(self):
        base_result = run_activation_workflow(
            CampaignRequest(prompt="Find an event in Dallas this weekend"),
            MockEventProvider(),
        )

        refined_result = refine_workflow_result(
            result=base_result,
            instruction="Use warmer outdoor colors",
            target="image",
            prompt_version="v2",
            creative_provider=MockCreativeProvider(),
            applied_at="2026-03-17T22:05:00Z",
        )

        self.assertIn("Use warmer outdoor colors", refined_result.image_concept.style_notes)
        self.assertEqual(refined_result.generated_asset.prompt_version, "v2")
        self.assertEqual(refined_result.selected_event.event.name, base_result.selected_event.event.name)
        self.assertEqual(refined_result.revision_id, 2)
        self.assertEqual(len(refined_result.asset_versions), 2)

    def test_refine_requires_instruction(self):
        base_result = run_activation_workflow(
            CampaignRequest(prompt="Find an event in Dallas this weekend"),
            MockEventProvider(),
        )

        with self.assertRaises(ValueError):
            refine_workflow_result(
                result=base_result,
                instruction="   ",
                target="copy",
                prompt_version="v1",
                creative_provider=MockCreativeProvider(),
                applied_at="2026-03-17T22:05:00Z",
            )


class FileRepositoryTests(unittest.TestCase):
    def test_file_repository_persists_and_reloads_runs(self):
        with TemporaryDirectory() as temp_dir:
            repository = FileRunRepository(temp_dir + "/runs.json")
            service = RunService(repository, MockEventProvider(), MockCreativeProvider())

            created = service.create_run(CampaignRequest(prompt="Find an event in Dallas this weekend"))
            reloaded_repository = FileRunRepository(temp_dir + "/runs.json")
            restored = reloaded_repository.get(created.run_id)

            self.assertIsNotNone(restored)
            self.assertEqual(restored.run_id, created.run_id)
            self.assertEqual(restored.result.selected_event.event.name, created.result.selected_event.event.name)
            self.assertTrue(restored.events)


if __name__ == "__main__":
    unittest.main()
