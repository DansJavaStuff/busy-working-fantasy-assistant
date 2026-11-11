from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import database
from roster_manager import drop_roster_player, record_ir_change


class RosterDropOnlyTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db_patch = patch.object(database, 'DB_FILE', Path(self.temp.name) / 'test.db')
        db_patch.start()
        self.addCleanup(db_patch.stop)
        database.initialise_database()
        database.replace_season_roster([
            dict(player_id='godwin', player_name='Chris Godwin Jr.', position='WR', team='TB', roster_slot='BN', slot_index=1),
            dict(player_id='tyson', player_name='Jordyn Tyson', position='WR', team='NO', roster_slot='BN', slot_index=2),
            dict(player_id='evans', player_name='Mike Evans', position='WR', team='SF', roster_slot='IR', slot_index=1),
        ], season=2026)

    def rows(self):
        return {r['player_id']: r for r in database.load_season_roster(2026)}

    def test_drop_only_removes_one_player_and_renumbers_bench(self):
        before = self.rows()
        drop_roster_player('godwin')
        after = self.rows()
        self.assertEqual(set(after), {'tyson', 'evans'})
        self.assertEqual(after['tyson']['slot_index'], 1)
        self.assertEqual(after['evans'], before['evans'])
        self.assertEqual(after['tyson']['acquired_at'], before['tyson']['acquired_at'])
        record_ir_change('evans', 'to_bench')
        self.assertTrue(all(r['roster_slot'] == 'BN' for r in self.rows().values()))

    def test_missing_repeated_or_wrong_season_drop_does_not_change_roster(self):
        before = self.rows()
        for player_id, season in [('', 2026), ('missing', 2026), ('godwin', 2027)]:
            with self.assertRaises(ValueError):
                drop_roster_player(player_id, season)
            self.assertEqual(self.rows(), before)
        drop_roster_player('godwin')
        before = self.rows()
        with self.assertRaises(ValueError):
            drop_roster_player('godwin')
        self.assertEqual(self.rows(), before)

    def test_historical_rosters_and_scores_remain_after_drop(self):
        database.snapshot_season_roster(9, season=2026)
        database.upsert_player_week_history({'godwin-yahoo': {'name': 'Chris Godwin Jr.', 'position': 'WR', 'team': 'TB',
            'weeks': {'9': {'actual': 3.6}}}}, season=2026)
        with database.connect() as db:
            snapshots = [tuple(r) for r in db.execute('SELECT * FROM season_week_roster')]
            scores = [tuple(r) for r in db.execute('SELECT * FROM season_player_week')]
        drop_roster_player('godwin')
        with database.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM season_week_roster')], snapshots)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM season_player_week')], scores)

    def test_route_drop_only_without_add_and_empty_ir_activation(self):
        import app as web
        client = web.app.test_client()
        response = client.post('/my-team/transaction', data={'drop_player_id': 'godwin', 'action': 'drop_only'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('transaction=1', response.location)
        self.assertNotIn('godwin', self.rows())
        response = client.post('/my-team/ir', data={'player_id': 'evans', 'direction': 'to_bench'})
        self.assertIn('moved=1', response.location)
        self.assertEqual(self.rows()['evans']['roster_slot'], 'BN')

    def test_route_requires_explicit_drop_only_and_unambiguous_selection(self):
        import app as web
        client = web.app.test_client()
        before = self.rows()
        for form in ({'drop_player_id': 'godwin'},
                     {'action': 'drop_only'},
                     {'drop_player_id': 'godwin', 'add_yahoo_player_id': 'deebo', 'action': 'drop_only'}):
            response = client.post('/my-team/transaction', data=form)
            self.assertIn('transaction_error=', response.location)
            self.assertEqual(self.rows(), before)

    def test_my_team_renders_drop_only_button_bypassing_add_requirement(self):
        import app as web
        with patch.object(web, 'enrich_local_roster', side_effect=lambda rows: rows), \
             patch.object(web, 'get_yahoo_provider_status', return_value={}), \
             patch.object(web.yahoo_provider, 'get_roster', return_value=[]), \
             patch.object(web.yahoo_provider, 'get_available_players', return_value=[]):
            response = web.app.test_client().get('/my-team')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="action" value="drop_only" formnovalidate', response.data)
        self.assertIn(b'Record drop only', response.data)
