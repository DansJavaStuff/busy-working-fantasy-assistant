from pathlib import Path
from unittest import TestCase


class BusyOverlayTests(TestCase):
    def test_cancelled_submission_does_not_show_overlay(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "busy_overlay.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'document.addEventListener("submit"',
            script,
        )
        self.assertIn(
            "event.defaultPrevented",
            script,
        )
        self.assertNotIn(
            'form.addEventListener("submit"',
            script,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
