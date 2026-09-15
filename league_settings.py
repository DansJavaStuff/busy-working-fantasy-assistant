from datetime import date


LEAGUE_NAME = "Busy Working"
TEAM_COUNT = 12

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

TRADE_DEADLINES = {
    2026: date(2026, 11, 28),
}
ALLOW_DRAFT_PICK_TRADES = True
TRADE_REVIEW = "commissioner"
TRADE_REJECT_TIME_DAYS = 1

WAIVER_TIME_DAYS = 1
WAIVER_TYPE = "weekly_rolling_standings"
WEEKLY_WAIVERS = "game_time_to_tuesday"
POST_DRAFT_PLAYERS = "follow_waiver_rules"
ALLOW_INJURED_DIRECT_TO_IR = False

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
