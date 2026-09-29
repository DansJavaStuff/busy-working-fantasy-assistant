from unittest import TestCase

import fantasypros_targeted


class FantasyProsTargetedTests(TestCase):
    def test_extracts_nested_player_catalogue(self):
        payload = {
            "data": {
                "players": {
                    "9999": {
                        "player_name": "Mike Evans",
                        "player_positions": "WR",
                        "player_team_id": "SF",
                        "player_yahoo_id": "30123",
                    }
                }
            }
        }

        players = fantasypros_targeted._extract_catalog_players(payload)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["id"], "9999")
        self.assertEqual(players[0]["name"], "Mike Evans")
        self.assertEqual(players[0]["position"], "WR")
        self.assertEqual(players[0]["team"], "SF")
        self.assertEqual(players[0]["yahoo_id"], "30123")

    def test_resolves_by_name_when_team_metadata_differs(self):
        player = {
            "name": "Mike Evans",
            "position": "WR",
            "team": "SF",
        }
        candidates = [
            {
                "id": "9999",
                "name": "Mike Evans",
                "position": "WR",
                "team": "",
                "yahoo_id": "",
            }
        ]

        result = fantasypros_targeted._resolve_from_candidates(
            player,
            candidates,
        )

        self.assertEqual(result["id"], "9999")


if __name__ == "__main__":
    import unittest

    unittest.main()
