# Busy Working Fantasy Assistant

A personal Fantasy NFL assistant built for the **Busy Working** Yahoo Fantasy Football league.

The project currently focuses on supporting the live fantasy draft, with the longer-term goal of becoming a season-long assistant for roster management, waiver analysis, start/sit decisions and matchup planning.

## Current Status

The 2026 draft assistant is operational and has completed multiple full mock-draft rehearsals.

Current capabilities include:

- 12-team snake draft support
- Busy Working league roster configuration
- Mock Draft and Draft Night modes
- Manual live-draft pick recording
- Draft undo support
- Persistent draft sessions using SQLite
- Automatic database backup before starting an actual draft
- Draft completion detection
- Best-available player display
- Recommendation scoring with explanations
- Roster construction awareness
- RB/WR depth balancing
- QB and TE positional scarcity detection
- Protection against over-drafting QB and TE
- K/DST draft timing
- K/DST elite-player depletion and run awareness
- FantasyPros positional-tier integration
- Yahoo / consensus ADP awareness
- Fantasy Football Calculator draft-market data
- Player-data freshness/status reporting
- Historical recommendation replay
- Draft roster board
- FantasyPros API usage tracking

The recommendation engine is currently **frozen for the 2026 draft** unless a genuine functional bug is discovered.

## League Format

Busy Working is a 12-team Yahoo head-to-head league.

Draft roster:

- 1 QB
- 2 RB
- 2 WR
- 1 TE
- 1 W/R/T FLEX
- 1 K
- 1 DEF
- 5 Bench
- 1 IR

The IR position is not intentionally filled during the draft, giving a 14-player drafted roster.

## Data Sources

The assistant combines several sources rather than depending on a single ranking.

### FantasyPros Overall ADP

Used as the broad draft-market backbone.

The CSV is downloaded manually and stored under:

```text
data/FantasyPros_2026_Overall_ADP_Rankings.csv

Draft Modes
Mock Draft

Used for testing the recommendation engine and rehearsing the draft.

The simulator can advance other teams automatically while the user's selections are made manually.

Draft Night

Used for the real draft.

Draft Night:

records selections manually
persists picks in SQLite
supports undo
resumes after an application restart
creates a backup before the actual draft begins
prevents accidental simulation behaviour
recognises completion after all 168 picks
Historical Replay

Past draft decisions can be replayed through the current recommendation engine.

Example:

python -m tools.historical_replay 25 41 104 128

The first argument is the draft session ID.

Remaining arguments are overall draft picks to analyse.

This is useful for regression testing recommendation changes without rerunning an entire mock draft.

Player Data Status

Check data readiness with:

python data_status.py

The application monitors:

FantasyPros API cache
FantasyPros Overall ADP
FantasyPros positional rankings
Fantasy Football Calculator data
merged player database

The aim before an actual draft is:

Player data: READY
Running the Application

The application is a Flask application served by Waitress.

Development/manual launch:

source venv/bin/activate
waitress-serve --listen=0.0.0.0:8080 app:app

On the Raspberry Pi it normally runs through the busy-working systemd service.

Useful commands:

sudo systemctl status busy-working
sudo systemctl restart busy-working

Health check:

curl http://127.0.0.1:8080/health
Development Checks

After modifying Python code:

python -m py_compile *.py tools/*.py
git diff --check

Before committing:

git status --short
git diff --check --cached
Repository Layout
.
├── app.py
├── database.py
├── draft_engine.py
├── recommendation_engine.py
├── player_database.py
├── fantasypros.py
├── fantasypros_rankings.py
├── ffc.py
├── adp.py
├── data_status.py
├── refresh_data.py
├── league_config.py
├── roster_display.py
├── simulator.py
├── yahoo.py
├── data/
│   └── downloaded ranking data (ignored)
├── tools/
│   └── historical_replay.py
├── templates/
├── static/
└── ROADMAP.md

Runtime databases, caches, credentials, downloaded rankings and backups are excluded from Git.

In-Season Goal

After the draft, the project will transition from a draft assistant into a weekly fantasy-management assistant.

Planned areas include:

My Team dashboard
roster synchronisation
waiver recommendations
add/drop analysis
start/sit recommendations
injuries and availability
bye-week planning
opponent and matchup analysis
trade analysis
weekly summaries

See ROADMAP.md for the current development plan.

Disclaimer

This is a personal, non-commercial project.

It does not currently submit Yahoo transactions, waiver claims, lineup changes or trades.
