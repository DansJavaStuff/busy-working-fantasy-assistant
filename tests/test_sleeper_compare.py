from unittest import TestCase
from unittest.mock import patch

import sleeper_compare


class SleeperCompareTests(TestCase):
    def test_suffix_fallback_requires_unique_team_and_position(self):
        cases = [("Chris Godwin Jr.", "Chris Godwin", "TB", "WR"),
                 ("Tyrone Tracy Jr.", "Tyrone Tracy", "NYG", "RB"),
                 ("Mike Washington Jr.", "Mike Washington", "LV", "RB"),
                 ("Kenneth Walker", "Kenneth Walker III", "SEA", "RB")]
        for yahoo, provider, team, position in cases:
            with self.subTest(name=yahoo):
                target = {"name": yahoo, "team": team, "position": position}
                row = {"team": team, "player": {"full_name": provider, "position": position}}
                self.assertIs(sleeper_compare.find_projection([row], target), row)
                self.assertIsNone(sleeper_compare.find_projection([row, dict(row)], target))
                self.assertIsNone(sleeper_compare.find_projection([row], {**target, "team": "OTHER"}))
                self.assertIsNone(sleeper_compare.find_projection([row], {**target, "team": None}))
                self.assertIsNone(sleeper_compare.find_projection([row], {**target, "position": "TE"}))

    def test_exact_name_wins_and_suffix_collisions_are_rejected(self):
        target = {"name": "Alex Smith Jr.", "team": "TB", "position": "WR"}
        def row(name):
            return {"team": "TB", "player": {"full_name": name, "position": "WR"}}
        exact = row("Alex Smith Jr.")
        self.assertIs(sleeper_compare.find_projection([exact, row("Alex Smith")], target), exact)
        self.assertIsNone(sleeper_compare.find_projection([row("Alex Smith"), row("Alex Smith Sr.")], target))
        self.assertIsNone(sleeper_compare.find_projection([row("Alan Smith")], target))

    def test_kicker_uses_total_makes_and_custom_distance_weights(self):
        stats = {"fgm": 1.55, "fgm_0_19": .05, "fgm_20_29": .23,
                 "fgm_30_39": .42, "fgm_40_49": .38, "fgm_50p": .19, "xpm": 2.27,
                 "pts_half_ppr": 999}
        score, note = sleeper_compare.score_stream_for_yahoo(stats, "K")
        self.assertEqual(score, 6.13)
        self.assertIn("derived", note)
        del stats["fgm"]
        self.assertIsNone(sleeper_compare.score_stream_for_yahoo(stats, "K")[0])
        stats["fgm"] = .1
        self.assertIsNone(sleeper_compare.score_stream_for_yahoo(stats, "K")[0])

    def test_defence_uses_bands_and_does_not_double_count_touchdowns(self):
        stats = {"sack": 2, "int": 1, "fum_rec": .5, "def_td": .2,
                 "pass_int_td": .1, "def_fum_td": .1, "st_td": .1,
                 "def_pr_td": .1, "pts_allow_14_20": 1, "pts_std": 999}
        score, note = sleeper_compare.score_stream_for_yahoo(stats, "DST")
        self.assertEqual(score, 7.8)
        self.assertIn("not outcome probabilities", note)
        del stats["pts_allow_14_20"]
        stats["pts_allow"] = 17
        self.assertIsNone(sleeper_compare.score_stream_for_yahoo(stats, "DST")[0])

    def test_stream_comparison_matches_defence_by_team_and_reports_provenance(self):
        players = [{"name": "Titans", "team": "TEN", "position": "DST", "current_week_projection": 7.72},
                   {"name": "Colts", "team": "IND", "position": "DST", "current_week_projection": 5.51}]
        def row(team, sacks):
            return {"team": team, "player": {"first_name": "Full", "last_name": "Team Name"},
                    "company": "rotowire", "updated_at": 1792595455969,
                    "stats": {"sack": sacks, "int": 0, "fum_rec": 0, "def_td": 0, "pts_allow_21_27": 1}}
        with patch.object(sleeper_compare, "fetch_week_position", return_value=[row("TEN", 1), row("IND", 3)]) as fetch:
            results = sleeper_compare.compare_players(players, 7)
        fetch.assert_called_once_with("DEF", 7, season=2026)
        self.assertEqual(results[0]["sleeper_yahoo_projection"], 1)
        self.assertEqual(results[0]["provider"], "rotowire")
        self.assertIn("UTC", results[0]["updated_display"])
        move = {"add": players[0], "drop": players[1], "streaming": True}
        evidence = sleeper_compare.stream_move_evidence(move, results)
        self.assertEqual(evidence["verdict"], "SOURCES DISAGREE")
        self.assertEqual(evidence["edge"], -2)
        self.assertIsNone(sleeper_compare.stream_move_evidence(move, results[:1])["edge"])
        self.assertEqual(sleeper_compare.attach_stream_evidence([move], 7, lambda *a, **kw: [])[0]["source_comparison"]["verdict"], "SECOND SOURCE UNAVAILABLE")

    def test_failed_position_does_not_remove_other_comparisons(self):
        def fetch(position, *args, **kwargs):
            if position == "DEF":
                raise RuntimeError("offline")
            return [{"player": {"full_name": "Test Kicker"}, "stats": {"fgm": 1, "fgm_40_49": 0, "fgm_50p": 0, "xpm": 2}}]
        players = [{"name": "Titans", "team": "TEN", "position": "DST"},
                   {"name": "Test Kicker", "position": "K"}]
        with patch.object(sleeper_compare, "fetch_week_position", side_effect=fetch):
            results = sleeper_compare.compare_players(players, 7)
        self.assertIsNone(results[0]["sleeper_yahoo_projection"])
        self.assertIn("offline", results[0]["coverage_note"])
        self.assertEqual(results[1]["sleeper_yahoo_projection"], 4)

    def test_scores_busy_working_offense_rules(self):
        stats = {
            "pass_yd": 250,
            "pass_td": 2,
            "pass_int": 1,
            "rush_yd": 30,
            "rush_td": 1,
            "rec": 4,
            "rec_yd": 50,
            "rec_td": 1,
            "fum_lost": 1,
            "rush_2pt": 1,
        }

        # 250/25 + 2*5 -2 + 30/10 +6 + 4*.5 +50/10 +6 -2 +2
        self.assertEqual(
            sleeper_compare.score_offense_for_yahoo(stats),
            40.0,
        )

    def test_compare_fetches_only_needed_positions(self):
        rows = {
            "RB": [
                {
                    "team": "TEN",
                    "player": {
                        "first_name": "Tony",
                        "last_name": "Pollard",
                        "position": "RB",
                    },
                    "stats": {
                        "rush_yd": 60,
                        "rec": 2,
                        "rec_yd": 20,
                        "pts_half_ppr": 9.0,
                    },
                }
            ],
            "WR": [
                {
                    "team": "SF",
                    "player": {
                        "first_name": "Mike",
                        "last_name": "Evans",
                        "position": "WR",
                    },
                    "stats": {
                        "rec": 4,
                        "rec_yd": 70,
                        "rec_td": 0.5,
                        "pts_half_ppr": 12.0,
                    },
                }
            ],
        }

        calls = []

        def fake_fetch(position, week, season=2026):
            calls.append((position, week, season))
            return rows[position]

        players = [
            {
                "name": "Mike Evans",
                "position": "WR",
                "team": "SF",
                "current_week_projection": 9.88,
            },
            {
                "name": "Tony Pollard",
                "position": "RB",
                "team": "TEN",
                "current_week_projection": 7.46,
            },
        ]

        with patch.object(
            sleeper_compare,
            "fetch_week_position",
            side_effect=fake_fetch,
        ):
            result = sleeper_compare.compare_players(
                players,
                week=2,
            )

        self.assertEqual(
            [call[0] for call in calls],
            ["RB", "WR"],
        )
        self.assertEqual(result[0]["name"], "Mike Evans")
        self.assertEqual(
            result[0]["sleeper_yahoo_projection"],
            12.0,
        )
        self.assertEqual(
            result[1]["sleeper_yahoo_projection"],
            9.0,
        )

    def test_row_name_combines_first_and_last_name(self):
        row = {
            "player": {
                "first_name": "Courtland",
                "last_name": "Sutton",
                "position": "WR",
            }
        }

        self.assertEqual(
            sleeper_compare._row_name(row),
            "Courtland Sutton",
        )


if __name__ == "__main__":
    import unittest
    unittest.main()
