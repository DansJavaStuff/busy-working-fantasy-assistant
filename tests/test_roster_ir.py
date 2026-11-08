from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import database
from roster_manager import record_ir_change


class RosterIRTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db_patch = patch.object(database, 'DB_FILE', Path(self.temp.name) / 'test.db')
        db_patch.start()
        self.addCleanup(db_patch.stop)
        database.initialise_database()
        starters = [('QB', 1), ('RB', 1), ('RB', 2), ('WR', 1), ('WR', 2),
                    ('TE', 1), ('FLEX', 1), ('K', 1), ('DEF', 1)]
        self.roster = [dict(player_id=f'{slot}{index}', player_name=f'{slot} {index}',
                            position='WR' if slot == 'FLEX' else slot,
                            roster_slot=slot, slot_index=index) for slot, index in starters]
        self.roster += [dict(player_id=f'bench{i}', player_name='Mike Evans' if i == 1 else f'Bench {i}',
                             position='WR', roster_slot='BN', slot_index=i) for i in range(1, 6)]
        self.roster += [dict(player_id='tyson', player_name='Jordyn Tyson', position='WR',
                             roster_slot='IR', slot_index=1)]
        database.replace_season_roster(self.roster, season=2026)

    def rows(self):
        return {r['player_id']: r for r in database.load_season_roster(2026)}

    def test_full_bench_swap_preserves_membership_and_historical_records(self):
        database.snapshot_season_roster(9, season=2026)
        before = self.rows()
        with database.connect() as db:
            history = [tuple(r) for r in db.execute('SELECT * FROM season_week_roster')]
        record_ir_change('bench1', 'to_ir')
        after = self.rows()
        self.assertEqual(set(before), set(after))
        self.assertEqual(after['bench1']['roster_slot'], 'IR')
        self.assertEqual(after['tyson']['roster_slot'], 'BN')
        self.assertEqual(sum(r['roster_slot'] == 'BN' for r in after.values()), 5)
        self.assertEqual(sum(r['roster_slot'] == 'IR' for r in after.values()), 1)
        self.assertEqual(after['bench1']['acquired_at'], before['bench1']['acquired_at'])
        with database.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM season_week_roster')], history)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM season_transactions').fetchone()[0], 0)

    def test_activate_without_room_rejected_without_changes(self):
        before = self.rows()
        with self.assertRaisesRegex(ValueError, 'full'):
            record_ir_change('tyson', 'to_bench')
        self.assertEqual(before, self.rows())

    def test_activate_with_room_then_fill_empty_ir_slot(self):
        database.replace_season_roster([r for r in self.roster if r['player_id'] != 'bench5'], season=2026)
        record_ir_change('tyson', 'to_bench')
        self.assertEqual(self.rows()['tyson']['roster_slot'], 'BN')
        self.assertFalse(any(r['roster_slot'] == 'IR' for r in self.rows().values()))
        record_ir_change('bench1', 'to_ir')
        self.assertEqual(self.rows()['bench1']['roster_slot'], 'IR')
        self.assertEqual(self.rows()['tyson']['roster_slot'], 'BN')

    def test_invalid_moves_and_wrong_season_leave_roster_unchanged(self):
        before = self.rows()
        for player, direction, season in [('missing', 'to_ir', 2026), ('bench1', 'invalid', 2026),
                                           ('QB1', 'to_ir', 2026), ('bench1', 'to_bench', 2026),
                                           ('bench1', 'to_ir', 2027)]:
            with self.subTest(player=player, direction=direction, season=season):
                with self.assertRaises(ValueError):
                    record_ir_change(player, direction, season)
                self.assertEqual(before, self.rows())

    def test_route_and_my_team_recording_controls(self):
        import app as web
        client = web.app.test_client()
        with patch.object(web, 'enrich_local_roster', side_effect=lambda rows: rows), \
             patch.object(web, 'get_yahoo_provider_status', return_value={}), \
             patch.object(web.yahoo_provider, 'get_roster', return_value=[]), \
             patch.object(web.yahoo_provider, 'get_available_players', return_value=[]):
            response = client.get('/my-team')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Record Yahoo IR move', response.data)
        self.assertIn(b'Jordyn Tyson will move from IR', response.data)
        response = client.post('/my-team/ir', data={'player_id': 'bench1', 'direction': 'to_ir'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('moved=1', response.location)
        self.assertEqual(self.rows()['bench1']['roster_slot'], 'IR')
        response = client.post('/my-team/ir', data={'player_id': 'tyson', 'direction': 'invalid'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('move_error=', response.location)
