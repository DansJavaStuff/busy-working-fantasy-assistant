from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zoneinfo import ZoneInfo

import available_engine
import database
import weekly_engine
from roster_manager import add_roster_player
from test_transaction_engine import base_roster, player
from transaction_engine import build_transaction_recommendations, open_roster_places


def vacant_roster():
    roster = base_roster()
    roster[5] = {**roster[5], 'roster_slot': 'IR', 'status': 'IR', 'current_week_projection': 100}
    return roster


class OpenPlaceRecommendationTests(TestCase):
    def setUp(self):
        available_engine._AVAILABLE_CACHE['snapshot_key'] = None
        weekly_engine._TRANSACTION_CACHE['snapshot_key'] = None

    def test_ir_frees_a_place_and_all_pickups_keep_every_player(self):
        roster = vacant_roster()
        self.assertEqual(open_roster_places(roster), 1)
        moves = build_transaction_recommendations(roster, [player('new', 'New WR', 'WR', week_projection=20)],
                                                 current_week=10, cant_cut_ids={p['yahoo_player_id'] for p in roster})
        self.assertEqual(len(moves), 1)
        self.assertIsNone(moves[0]['drop'])
        self.assertTrue(moves[0]['add_only'])
        self.assertGreater(moves[0]['week_gain'], 0)
        self.assertIn('no drop needed', moves[0]['reasons'][0])

    def test_full_roster_still_requires_drop_and_protects_ir_player(self):
        roster = base_roster() + [player('ir', 'IR Player', 'WR', roster_slot='IR')]
        self.assertEqual(open_roster_places(roster), 0)
        moves = build_transaction_recommendations(roster, [player('new', 'New WR', 'WR', week_projection=20)])
        self.assertTrue(moves)
        self.assertTrue(all(m['drop'] is not None and m['drop']['yahoo_player_id'] != 'ir' for m in moves))

    def test_open_place_supports_incomplete_starting_lineup_and_position_caps(self):
        roster = [p for p in base_roster() if p['position'] != 'TE']
        moves = build_transaction_recommendations(roster, [player('newte', 'New TE', 'TE', week_projection=10)])
        self.assertTrue(moves)
        self.assertIsNone(moves[0]['drop'])
        self.assertGreaterEqual(moves[0]['week_gain'], 10)
        options = [player('qb3', 'Third QB', 'QB', week_projection=30), player('k2', 'Second K', 'K', week_projection=30),
                   player('own', 'Existing QB', 'QB')]
        self.assertEqual(build_transaction_recommendations(vacant_roster(), options), [])

    def test_ir_slot_change_invalidates_weekly_recommendation_cache(self):
        full = base_roster()
        candidate = player('new', 'New WR', 'WR', week_projection=20)
        first = weekly_engine.cached_transaction_recommendations(full, [candidate], {}, 10)
        second = weekly_engine.cached_transaction_recommendations(vacant_roster(), [candidate], {}, 10)
        self.assertTrue(all(m['drop'] for m in first))
        self.assertTrue(all(m['drop'] is None for m in second))

    def test_open_waiver_has_add_deadline_and_no_speculative_predrop(self):
        when = datetime.now(ZoneInfo('Europe/London')) + timedelta(days=5)
        addition = {**player('new', 'New WR', 'WR'), 'local_game': {'datetime': when}}
        move = {'add': addition, 'drop': None, 'add_only': True}
        result = weekly_engine.add_transaction_deadlines([move], 2026)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['transaction_deadline']['datetime'], when)
        self.assertEqual(weekly_engine.build_speculative_waiver_moves([move], [], 2026), [])

    def test_available_ir_cache_refresh_claim_queue_and_tracking_render(self):
        import app as web
        roster = base_roster()
        candidate = {**player('new', 'New WR', 'WR', week_projection=30), 'team': 'BUF',
                     'weeks': {'10': {'projection': 30}}, 'roster_status': 'W (Nov 14)'}
        with patch.object(available_engine, 'load_season_roster', side_effect=lambda *a: roster), \
             patch.object(available_engine, 'enrich_local_roster', side_effect=lambda rows: rows), \
             patch.object(available_engine, 'load_season_league_state', return_value={}), \
             patch.object(available_engine, 'load_week_cant_cut', return_value=[]), \
             patch.object(available_engine, 'get_effective_available_players', return_value=[candidate]), \
             patch.object(available_engine.yahoo_provider, 'get_status', return_value={}):
            first = available_engine.build_available_rankings(2026, 10, sleeper_fetch=lambda *a, **kw: [])
            roster[:] = vacant_roster()
            second = available_engine.build_available_rankings(2026, 10, sleeper_fetch=lambda *a, **kw: [])
        self.assertIsNot(first, second)
        self.assertIsNone(second['rankings'][0]['best_drop'])
        self.assertTrue(second['rankings'][0]['move']['add_only'])
        self.assertTrue(second['waiver_queue'])
        self.assertIsNone(second['waiver_queue'][0]['drop'])
        with web.app.test_request_context():
            html = web.render_template('_available_rankings.html', available=second, tracked_keys={'new::'})
        self.assertIn('No drop needed', html)
        self.assertIn('Tracked', html)
        self.assertNotIn('value="None"', html)

    def test_open_stream_comparison_and_unknown_future_data_are_safe(self):
        from sleeper_compare import attach_stream_evidence
        roster = [p for p in base_roster() if p['position'] != 'K']
        candidate = player('knew', 'New K', 'K', week_projection=9, four_week_projection=None)
        moves = build_transaction_recommendations(roster, [candidate])
        seen = []
        def fetch(players, **kwargs):
            seen.extend(players)
            return []
        result = attach_stream_evidence(moves, 10, sleeper_fetch=fetch)
        self.assertEqual(seen, [candidate])
        self.assertIsNone(result[0]['drop'])
        self.assertEqual(result[0]['four_week_gain'], 0)
        self.assertFalse(result[0]['four_week_data_complete'])

    def test_open_metrics_match_full_optimizer_with_no_injury_or_vacancy(self):
        from transaction_engine import _open_slot_metrics, roster_metrics
        roster = base_roster()
        self.assertEqual(_open_slot_metrics(roster, []), roster_metrics(roster, []))


class AddOnlyRecordingTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db_patch = patch.object(database, 'DB_FILE', Path(self.temp.name) / 'test.db')
        db_patch.start()
        self.addCleanup(db_patch.stop)
        database.initialise_database()
        rows = []
        for i, p in enumerate(vacant_roster(), 1):
            rows.append(dict(player_id=p['yahoo_player_id'], player_name=p['name'], position=p['position'],
                             roster_slot=p['roster_slot'], slot_index=i))
        database.replace_season_roster(rows, season=2026)
        self.incoming = dict(player_id='new', player_name='New WR', position='WR', team='BUF')

    def test_add_only_fills_place_and_preserves_ir_history_and_capacity(self):
        database.snapshot_season_roster(9, season=2026)
        before = database.load_season_roster(2026)
        with database.connect() as db:
            history = [tuple(r) for r in db.execute('SELECT * FROM season_week_roster')]
        add_roster_player(self.incoming)
        after = database.load_season_roster(2026)
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(open_roster_places(after), 0)
        self.assertEqual(next(r for r in after if r['player_id'] == 'new')['roster_slot'], 'BN')
        self.assertEqual(next(r for r in after if r['roster_slot'] == 'IR'), next(r for r in before if r['roster_slot'] == 'IR'))
        with self.assertRaisesRegex(ValueError, 'already'):
            add_roster_player(self.incoming)
        with self.assertRaisesRegex(ValueError, 'full'):
            add_roster_player({**self.incoming, 'player_id': 'other', 'player_name': 'Other WR'})
        with database.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM season_week_roster')], history)

    def test_add_only_route_uses_snapshot_and_rejects_ambiguous_or_missing_input(self):
        import app as web
        client = web.app.test_client()
        before = database.load_season_roster(2026)
        for form in ({'action': 'add_only'}, {'action': 'add_only', 'drop_player_id': 'qb1', 'add_yahoo_player_id': 'new'}):
            response = client.post('/my-team/transaction', data=form)
            self.assertIn('transaction_error=', response.location)
            self.assertEqual(database.load_season_roster(2026), before)
        incoming = {'yahoo_player_id': 'new', 'name': 'New WR', 'position': 'WR', 'team': 'BUF'}
        with patch.object(web.yahoo_provider, 'get_roster', return_value=[]), \
             patch.object(web.yahoo_provider, 'get_available_players', return_value=[incoming]):
            response = client.post('/my-team/transaction', data={'action': 'add_only', 'add_yahoo_player_id': 'new'})
        self.assertIn('transaction=1', response.location)
        self.assertEqual(len(database.load_season_roster(2026)), len(before) + 1)
