from unittest import TestCase
from unittest.mock import patch

from tools import import_yahoo_players


class YahooRosterReconciliationTests(TestCase):
    def test_same_position_changes_are_applied(self):
        local = [
            {
                "player_id": "lawrence",
                "player_name": "Trevor Lawrence",
                "position": "QB",
                "team": "JAX",
            },
            {
                "player_id": "buccaneers",
                "player_name": "Buccaneers",
                "position": "DST",
                "team": "TB",
            },
        ]

        yahoo = {
            "1": {
                "yahoo_player_id": "1",
                "name": "C.J. Stroud",
                "position": "QB",
                "team": "HOU",
            },
            "2": {
                "yahoo_player_id": "2",
                "name": "Packers",
                "position": "DST",
                "team": "GB",
            },
        }

        with patch.object(
            import_yahoo_players,
            "replace_roster_player",
        ) as replace:
            changed = (
                import_yahoo_players
                .reconcile_local_roster_from_yahoo(
                    local,
                    yahoo,
                )
            )

        self.assertTrue(changed)
        self.assertEqual(replace.call_count, 2)

    def test_cross_position_change_is_not_applied(self):
        local = [
            {
                "player_id": "lawrence",
                "player_name": "Trevor Lawrence",
                "position": "QB",
                "team": "JAX",
            }
        ]

        yahoo = {
            "1": {
                "yahoo_player_id": "1",
                "name": "Tyjae Spears",
                "position": "RB",
                "team": "TEN",
            }
        }

        with patch.object(
            import_yahoo_players,
            "replace_roster_player",
        ) as replace:
            changed = (
                import_yahoo_players
                .reconcile_local_roster_from_yahoo(
                    local,
                    yahoo,
                )
            )

        self.assertFalse(changed)
        replace.assert_not_called()
