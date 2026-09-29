"""Day-by-day in-season workflow for the fantasy assistant."""

from datetime import timedelta

DAILY_TASKS = {
    0: {
        "focus": "Finish the current matchup",
        "tasks": [
            {
                "key": "monday_refresh",
                "title": "Refresh the latest Yahoo data",
                "detail": "Bring projections, actual scores and player statuses up to date.",
                "endpoint": "weekly",
                "link_label": "Open Weekly",
            },
            {
                "key": "monday_players",
                "title": "Check every player still able to score",
                "detail": "Review Monday-night starters, injuries and the remaining matchup position.",
                "endpoint": "weekly",
                "link_label": "Review lineup",
            },
            {
                "key": "monday_waivers",
                "title": "Note the roster problems to solve tomorrow",
                "detail": "Use injuries, weak positions and upcoming byes to prepare for waivers.",
                "endpoint": "available_players",
                "link_label": "Preview players",
            },
        ],
    },
    1: {
        "focus": "Prepare this week's waiver claims",
        "tasks": [
            {
                "key": "tuesday_refresh",
                "title": "Download the Yahoo files and refresh the data",
                "detail": "Include the full Player_list files plus the separate K and DEF files.",
                "endpoint": "weekly",
                "link_label": "Refresh Yahoo data",
            },
            {
                "key": "tuesday_settings",
                "title": "Confirm waiver priority and Can't Cut players",
                "detail": "Save the current Yahoo values in Settings before assessing moves.",
                "endpoint": "settings_page",
                "link_label": "Open Settings",
            },
            {
                "key": "tuesday_history",
                "title": "Check last week's result and history",
                "detail": "Confirm the stored lineup and actual scores agree with Yahoo.",
                "endpoint": "history",
                "link_label": "Check History",
            },
            {
                "key": "tuesday_claims",
                "title": "Choose, submit and track waiver claims",
                "detail": "Submit the selected claims in Yahoo and record them in priority order here.",
                "endpoint": "available_players",
                "link_label": "Review Available",
            },
            {
                "key": "tuesday_lineup",
                "title": "Take an initial look at this week's lineup",
                "detail": "Review the recommendation, but wait for waivers before saving the submitted lineup.",
                "endpoint": "weekly",
                "link_label": "Preview Weekly",
            },
        ],
    },
    2: {
        "focus": "Reconcile waivers and update the roster",
        "tasks": [
            {
                "key": "wednesday_results",
                "title": "Confirm the waiver results",
                "detail": "Check Yahoo, then mark each tracked claim as succeeded, failed or cancelled.",
                "endpoint": "available_players",
                "link_label": "Update claims",
            },
            {
                "key": "wednesday_roster",
                "title": "Record successful adds and drops",
                "detail": "Make My Team match the roster now shown in Yahoo.",
                "endpoint": "my_team",
                "link_label": "Update My Team",
            },
            {
                "key": "wednesday_refresh",
                "title": "Download fresh Yahoo files and refresh again",
                "detail": "Refresh the player database after the waiver changes have cleared.",
                "endpoint": "weekly",
                "link_label": "Refresh Yahoo data",
            },
            {
                "key": "wednesday_available",
                "title": "Review the remaining available players",
                "detail": "Look for useful free-agent additions after the waiver run.",
                "endpoint": "available_players",
                "link_label": "Review Available",
            },
            {
                "key": "wednesday_lineup",
                "title": "Set the updated lineup in Yahoo",
                "detail": "Apply the recommendation, then save it as submitted here once both lineups match.",
                "endpoint": "weekly",
                "link_label": "Open Weekly",
            },
        ],
    },
    3: {
        "focus": "Make the first lineup-lock decisions",
        "tasks": [
            {
                "key": "thursday_refresh",
                "title": "Refresh Yahoo data and player statuses",
                "detail": "Use the latest information before the Thursday game locks.",
                "endpoint": "weekly",
                "link_label": "Open Weekly",
            },
            {
                "key": "thursday_status",
                "title": "Review injuries and Start/Sit evidence",
                "detail": "Pay particular attention to questionable players and close decisions.",
                "endpoint": "weekly",
                "link_label": "Review decisions",
            },
            {
                "key": "thursday_lock",
                "title": "Set every Thursday player before kickoff",
                "detail": "Confirm their Yahoo slots before their individual games lock.",
                "endpoint": "weekly",
                "link_label": "Check next lock",
            },
            {
                "key": "thursday_save",
                "title": "Save the lineup currently submitted to Yahoo",
                "detail": "Only save after the app and Yahoo lineups agree.",
                "endpoint": "weekly",
                "link_label": "Save submitted lineup",
            },
        ],
    },
    4: {
        "focus": "Monitor injuries and late-week news",
        "tasks": [
            {
                "key": "friday_refresh",
                "title": "Refresh Yahoo data and injury statuses",
                "detail": "Check for changes following Thursday's game and Friday practice reports.",
                "endpoint": "weekly",
                "link_label": "Open Weekly",
            },
            {
                "key": "friday_lineup",
                "title": "Review the recommended lineup",
                "detail": "Revisit any close Start/Sit calls affected by new information.",
                "endpoint": "weekly",
                "link_label": "Review lineup",
            },
            {
                "key": "friday_available",
                "title": "Check available replacements if needed",
                "detail": "Look for injury cover, bye cover or a stronger free-agent option.",
                "endpoint": "available_players",
                "link_label": "Review Available",
            },
        ],
    },
    5: {
        "focus": "Prepare for Sunday's games",
        "tasks": [
            {
                "key": "saturday_refresh",
                "title": "Refresh Yahoo data and final practice statuses",
                "detail": "Use the latest designations before making weekend decisions.",
                "endpoint": "weekly",
                "link_label": "Open Weekly",
            },
            {
                "key": "saturday_status",
                "title": "Resolve questionable starters where possible",
                "detail": "Check injury news, replacements and the timing of each kickoff.",
                "endpoint": "weekly",
                "link_label": "Review Status Watch",
            },
            {
                "key": "saturday_available",
                "title": "Make any necessary free-agent moves",
                "detail": "Add cover before Sunday if the current roster has a clear problem.",
                "endpoint": "available_players",
                "link_label": "Review Available",
            },
            {
                "key": "saturday_lineup",
                "title": "Make the Yahoo and app lineups agree",
                "detail": "Leave only genuine game-time decisions for Sunday.",
                "endpoint": "weekly",
                "link_label": "Review lineup",
            },
        ],
    },
    6: {
        "focus": "Complete the final lineup checks",
        "tasks": [
            {
                "key": "sunday_refresh",
                "title": "Refresh the latest Yahoo data",
                "detail": "Pull in Sunday actives, inactives, injuries and projection changes.",
                "endpoint": "weekly",
                "link_label": "Open Weekly",
            },
            {
                "key": "sunday_early",
                "title": "Finalise the early-game starters",
                "detail": "Resolve every decision before the first Sunday kickoff.",
                "endpoint": "weekly",
                "link_label": "Check next lock",
            },
            {
                "key": "sunday_save",
                "title": "Save the lineup submitted to Yahoo",
                "detail": "Confirm both lineups match before saving the weekly record.",
                "endpoint": "weekly",
                "link_label": "Save submitted lineup",
            },
            {
                "key": "sunday_late",
                "title": "Recheck late and evening players",
                "detail": "Keep flexible players in FLEX and respond to later inactive announcements.",
                "endpoint": "weekly",
                "link_label": "Review upcoming locks",
            },
        ],
    },
}


def checklist_for_day(checklist_date):
    """Return the workflow checklist for one local calendar date."""

    definition = DAILY_TASKS[
        checklist_date.weekday()
    ]

    return {
        "date": checklist_date,
        "day_name": checklist_date.strftime(
            "%A"
        ),
        "date_display": checklist_date.strftime(
            "%-d %B %Y"
        ),
        "focus": definition["focus"],
        "tasks": [
            dict(task)
            for task in definition["tasks"]
        ],
    }


def tomorrow_checklist(checklist_date):
    """Return tomorrow's workflow checklist."""

    return checklist_for_day(
        checklist_date
        + timedelta(days=1)
    )
