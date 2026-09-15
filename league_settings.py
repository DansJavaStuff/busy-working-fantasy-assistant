from datetime import date


LEAGUE_ID = 688636
LEAGUE_NAME = "Busy Working"
LEAGUE_URL = "https://football.fantasysports.yahoo.com/league/busyworking"
TEAM_COUNT = 12
SCORING_TYPE = "head_to_head"
START_SCORING_WEEK = 1
AUTO_RENEW = True
PUBLICLY_VIEWABLE = False
CASH_LEAGUE = False

DRAFT_TYPE = "live_standard"
LIVE_DRAFT_PICK_TIME_SECONDS = 90
ALLOW_DRAFT_PICK_TRADES = True

REGULAR_SEASON_WEEKS = 14
PLAYOFF_TEAM_COUNT = 6
PLAYOFF_START_WEEK = 15
CHAMPIONSHIP_WEEK = 17
FINAL_FANTASY_WEEK = CHAMPIONSHIP_WEEK
PLAYOFF_TIE_BREAKER = "higher_seed"
PLAYOFF_RESEEDING = False
DIVISION_COUNT = 2
DIVISION_WINNERS_TOP_SEEDS = True
LOCK_ELIMINATED_TEAMS = False
PLAY_AGAINST_MEDIAN = False
PLAY_AGAINST_SECOND_OPPONENT = False

TRADE_DEADLINES = {
    2026: date(2026, 11, 28),
}
MAX_TRADES_SEASON = None
TRADE_REVIEW = "commissioner"
TRADE_REJECT_TIME_DAYS = 1

MAX_ACQUISITIONS_SEASON = None
MAX_ACQUISITIONS_WEEK = None
WAIVER_TIME_DAYS = 1
WAIVER_TYPE = "weekly_rolling_standings"
WEEKLY_WAIVERS = "game_time_to_tuesday"
POST_DRAFT_PLAYERS = "follow_waiver_rules"
ALLOW_INJURED_DIRECT_TO_IR = False
CANT_CUT_LIST_PROVIDER = "yahoo_sports"

APPLY_INJURED_STATUS_FOR_POSTPONED_GAMES = False
LOCK_BENCHED_PLAYERS = False
FRACTIONAL_POINTS = True
NEGATIVE_POINTS = True

ROSTER_POSITIONS = (
    "QB",
    "WR",
    "WR",
    "RB",
    "RB",
    "TE",
    "W/R/T",
    "K",
    "DEF",
    "BN",
    "BN",
    "BN",
    "BN",
    "BN",
    "IR",
)

OFFENSE_SCORING = {
    "passing_yards_per_point": 25,
    "passing_touchdown": 5,
    "interception": -2,
    "rushing_yards_per_point": 10,
    "rushing_touchdown": 6,
    "reception": 0.5,
    "receiving_yards_per_point": 10,
    "receiving_touchdown": 6,
    "return_touchdown": 6,
    "two_point_conversion": 2,
    "fumble_lost": -2,
    "offensive_fumble_return_touchdown": 6,
}

KICKER_SCORING = {
    "field_goal_0_19": 2,
    "field_goal_20_29": 2,
    "field_goal_30_39": 2,
    "field_goal_40_49": 3,
    "field_goal_50_plus": 4,
    "pat_made": 1,
}

DEFENSE_SCORING = {
    "sack": 1,
    "interception": 2,
    "fumble_recovery": 2,
    "touchdown": 6,
    "safety": 2,
    "blocked_kick": 2,
    "kickoff_punt_return_touchdown": 6,
    "points_allowed_0": 10,
    "points_allowed_1_6": 7,
    "points_allowed_7_13": 4,
    "points_allowed_14_20": 1,
    "points_allowed_21_27": 0,
    "points_allowed_28_34": -1,
    "points_allowed_35_plus": -4,
    "extra_point_returned": 2,
}
