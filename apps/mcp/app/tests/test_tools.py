import unittest

from app.tools.strategy import rank_event_candidates, score_event_fit


class StrategyToolTests(unittest.TestCase):
    def test_score_event_fit_prefers_family_friendly_event(self):
        intent = {
            "city": "Dallas",
            "audience": "family",
            "brand_category": "cold beverage",
            "constraints": ["family_friendly"],
        }
        event = {
            "name": "Dallas Family Festival",
            "city": "Dallas",
            "category": "family",
            "audience_tags": ["family", "general audience"],
            "brand_tags": ["cold beverage", "beverage", "outdoor"],
            "family_friendly": True,
            "visibility_hint": "high",
        }

        payload = score_event_fit(intent, event)["payload"]

        self.assertGreater(payload["score"], 70)
        self.assertIn("family-friendly", payload["rationale"])

    def test_rank_event_candidates_returns_best_event_first(self):
        intent = {
            "city": "Dallas",
            "audience": "family",
            "brand_category": "cold beverage",
            "constraints": ["family_friendly"],
        }
        events = [
            {
                "name": "Dallas Rock Night",
                "city": "Dallas",
                "category": "music",
                "audience_tags": ["music fans"],
                "brand_tags": ["snack", "beverage"],
                "family_friendly": False,
                "visibility_hint": "medium",
            },
            {
                "name": "Dallas Family Festival",
                "city": "Dallas",
                "category": "family",
                "audience_tags": ["family", "general audience"],
                "brand_tags": ["cold beverage", "beverage", "outdoor"],
                "family_friendly": True,
                "visibility_hint": "high",
            },
        ]

        ranked = rank_event_candidates(intent, events)["payload"]["ranked_events"]

        self.assertEqual(ranked[0]["event"]["name"], "Dallas Family Festival")


if __name__ == "__main__":
    unittest.main()
