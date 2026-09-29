from unittest import TestCase

import weekly_evidence


class WeeklyEvidenceTests(TestCase):
    def _lineup(self):
        return [
            {
                "slot": "FLEX",
                "player": {
                    "name": "Mike Evans",
                    "position": "WR",
                    "team": "TB",
                    "current_week_projection": 9.88,
                    "current_week_actual": None,
                },
            }
        ]

    def _bench(self):
        return [
            {
                "name": "Courtland Sutton",
                "position": "WR",
                "team": "DEN",
                "current_week_projection": 9.02,
                "current_week_actual": None,
            }
        ]

    def test_agreeing_sources_produce_start_recommendation(self):
        def fake_sleeper(players, week):
            return [
                {
                    "name": "Mike Evans",
                    "sleeper_yahoo_projection": 10.94,
                },
                {
                    "name": "Courtland Sutton",
                    "sleeper_yahoo_projection": 7.95,
                },
            ]

        result = weekly_evidence.build_start_sit_evidence(
            self._lineup(),
            self._bench(),
            week=2,
            sleeper_fetch=fake_sleeper,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["recommendation"], "START Mike Evans")
        self.assertEqual(result[0]["sleeper"]["edge"], 2.99)
        self.assertEqual(result[0]["sleeper"]["agreement"], "agree")

    def test_disagreeing_sources_are_flagged(self):
        def fake_sleeper(players, week):
            return [
                {
                    "name": "Mike Evans",
                    "sleeper_yahoo_projection": 8.0,
                },
                {
                    "name": "Courtland Sutton",
                    "sleeper_yahoo_projection": 10.0,
                },
            ]

        result = weekly_evidence.build_start_sit_evidence(
            self._lineup(),
            self._bench(),
            week=2,
            sleeper_fetch=fake_sleeper,
        )

        self.assertEqual(
            result[0]["recommendation"],
            "SOURCES DISAGREE",
        )
        self.assertEqual(result[0]["sleeper"]["agreement"], "disagree")

    def test_sleeper_failure_does_not_break_yahoo_decision(self):
        def fake_sleeper(players, week):
            raise RuntimeError("feed unavailable")

        result = weekly_evidence.build_start_sit_evidence(
            self._lineup(),
            self._bench(),
            week=2,
            sleeper_fetch=fake_sleeper,
        )

        self.assertEqual(result[0]["recommendation"], "LEAN Mike Evans")
        self.assertIn("feed unavailable", result[0]["sleeper"]["error"])


if __name__ == "__main__":
    import unittest
    unittest.main()
