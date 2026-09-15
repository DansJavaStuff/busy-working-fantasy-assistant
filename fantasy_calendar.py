from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


UK_TIME = ZoneInfo("Europe/London")


def fantasy_season_for_date(today=None):
    """Return the NFL season that contains the supplied calendar date."""
    if today is None:
        today = datetime.now(UK_TIME).date()

    # January and February belong to the NFL season that started in the
    # previous calendar year. March-August are treated as the upcoming season.
    if today.month <= 2:
        return today.year - 1

    return today.year


def week_1_thursday(season):
    """Return the Thursday NFL opener derived from US Labor Day."""
    september_1 = date(season, 9, 1)

    # US Labor Day is the first Monday in September. The NFL opener is the
    # following Thursday.
    days_until_monday = (0 - september_1.weekday()) % 7
    labor_day = september_1 + timedelta(days=days_until_monday)

    return labor_day + timedelta(days=3)


def week_1_start(season):
    """Return the Tuesday that starts fantasy Week 1."""
    return week_1_thursday(season) - timedelta(days=2)


def current_fantasy_week(season=None, today=None):
    """Return fantasy week 1-18 for the supplied/current UK date."""
    if today is None:
        today = datetime.now(UK_TIME).date()

    if season is None:
        season = fantasy_season_for_date(today)

    start = week_1_start(season)

    if today < start:
        return 1

    week = ((today - start).days // 7) + 1

    return max(1, min(18, week))


def game_date_for_week(season, week, game_day):
    """Return the calendar date for a Yahoo game-day label in a fantasy week."""
    offsets = {
        "Thu": 0,
        "Fri": 1,
        "Sat": 2,
        "Sun": 3,
        "Mon": 4,
        "Tue": 5,
        "Wed": 6,
    }

    offset = offsets.get(game_day)
    if offset is None:
        return None

    week_thursday = week_1_thursday(season) + timedelta(weeks=week - 1)
    return week_thursday + timedelta(days=offset)
