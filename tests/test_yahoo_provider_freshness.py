from datetime import datetime, timezone
from unittest import TestCase

from yahoo_provider import YahooDataProvider


class YahooProviderFreshnessTests(TestCase):
    def _provider(self, captured_at, generated_at):
        provider = YahooDataProvider()
        provider._loaded_at = datetime(
            2026, 9, 17, 20, 0,
            tzinfo=timezone.utc,
        )
        provider._captured_at = captured_at
        provider._generated_at = generated_at
        provider._source = "manual_html"
        provider._dataset = {
            "schema_version": 1,
            "players": {},
        }
        return provider

    def test_snapshot_is_current_when_normalized_after_html(self):
        provider = self._provider(
            datetime(2026, 9, 17, 19, 24, tzinfo=timezone.utc),
            datetime(2026, 9, 17, 19, 25, tzinfo=timezone.utc),
        )

        status = provider.get_status()

        self.assertTrue(status["snapshot_current"])
        self.assertIn("normalized", status["captured_at_display"])
        self.assertIn("CURRENT", status["captured_at_display"])

    def test_snapshot_is_stale_when_html_is_newer(self):
        provider = self._provider(
            datetime(2026, 9, 17, 19, 30, tzinfo=timezone.utc),
            datetime(2026, 9, 17, 19, 25, tzinfo=timezone.utc),
        )

        status = provider.get_status()

        self.assertFalse(status["snapshot_current"])
        self.assertIn("STALE", status["captured_at_display"])
