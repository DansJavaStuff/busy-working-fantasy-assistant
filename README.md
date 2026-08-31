# Busy Working Fantasy Assistant

A personal Fantasy NFL assistant built for the **Busy Working** Yahoo Fantasy Football league.

The project currently focuses on making the 2026 live draft reliable and useful, with the longer-term goal of becoming a season-long assistant for roster management, waiver analysis, start/sit decisions, matchup planning and trade evaluation.

## Current Status

The 2026 draft assistant is operational and has completed multiple full mock-draft rehearsals.

The recommendation engine is currently **frozen for the 2026 draft** unless a genuine functional bug is discovered.

Current capabilities include:

- 12-team snake-draft support
- Busy Working league roster configuration
- Mock Draft and Draft Night modes
- Manual live-draft pick recording
- Draft undo support
- Persistent draft sessions using SQLite
- Automatic database backup before starting an actual draft
- Resume of an active Draft Night session after application restart
- Draft completion detection
- Best Available player display
- Recommendation scoring with explanations
- Roster construction awareness
- RB/WR depth balancing
- QB and TE positional-scarcity detection
- Protection against unnecessary QB2 / TE2 / TE3 selections
- K/DST late-round timing
- K/DST elite-player depletion and recent-run awareness
- FantasyPros positional-rank and tier integration
- Yahoo / consensus ADP awareness
- Fantasy Football Calculator draft-market data
- Player-data freshness/status reporting
- FantasyPros API usage accounting and quota protection
- FFC-only refresh and database-only rebuild workflows
- Historical recommendation replay
- Draft roster board
- Waitress + systemd deployment on Raspberry Pi

## League Format

Busy Working is currently a 12-team Yahoo head-to-head league.

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

The draft engine itself stores the team count per session and supports snake drafts dynamically, but the recommendation strategy and FFC data are currently calibrated for the 12-team Busy Working league.

## Recommendation Philosophy

The assistant is intended to support decisions rather than blindly follow a single ranking.

Recommendations consider factors including:

- Yahoo ADP
- Consensus ADP
- FantasyPros positional ranking
- FantasyPros tier
- Value relative to expected draft position
- Likelihood of surviving to the next pick
- Current roster construction
- RB/WR depth balance
- Open starting positions
- FLEX availability
- QB/TE positional scarcity
- Avoiding unnecessary backup QB and extra TE selections
- K/DST draft timing
- Elite K/DST market depletion
- Recent K/DST runs

The model deliberately allows exceptional value to override normal roster preferences in some situations.

## Data Sources

The assistant combines several sources rather than depending on a single ranking.

### FantasyPros Overall ADP

Used as the broad draft-market backbone.

The CSV is downloaded manually and stored under:

```text
data/FantasyPros_2026_Overall_ADP_Rankings.csv
```

### FantasyPros Positional Rankings

Separate positional ranking files are used for:

- QB
- RB
- WR
- TE
- K
- DST

These provide positional rank / ECR and tier information.

The CSV files are stored under `data/` and intentionally excluded from Git.

### FantasyPros API

The FantasyPros API is used for additional ranking/player enrichment.

The current workflow requests:

- QB
- RB
- WR
- TE

A complete refresh therefore consumes four API calls.

The application tracks API usage locally, shows the remaining allowance on the Settings page and blocks a complete FantasyPros refresh when fewer than four locally tracked calls remain.

FantasyPros does not currently return a usable remaining-quota response header for this endpoint.

### Fantasy Football Calculator

Recent half-PPR mock-draft data is used as an additional indication of real draft behaviour and player availability.

It is deliberately not treated as the primary ranking source.

The current FFC feed is configured for a 12-team league.

### Yahoo

Yahoo is the target league platform.

OAuth authentication works, but Yahoo Fantasy Sports API access currently returns an additional-authorisation error.

The 2026 draft therefore uses manual pick entry rather than depending on live Yahoo API access.

Yahoo API integration remains a future goal.

## Draft Modes

### Mock Draft

Used for testing the recommendation engine and rehearsing the draft.

The simulator advances other teams automatically while the user's selections are made manually.

### Draft Night

Used for the real draft.

Draft Night:

- records selections manually
- persists picks in SQLite
- supports Undo
- resumes after an application restart
- creates a database backup before the actual draft begins
- prevents accidental simulation behaviour
- recognises completion after all 168 picks in the current 12-team / 14-round format

## Historical Replay

Past draft decisions can be replayed through the current recommendation engine.

Example:

```bash
python -m tools.historical_replay 25 41 104 128
```

The first argument is the draft session ID.

Remaining arguments are overall draft picks to analyse.

This is useful for regression testing recommendation changes without rerunning an entire mock draft.

## Player Data and Refresh Workflow

The Settings page shows the state of:

- FantasyPros API cache
- FantasyPros Overall ADP
- FantasyPros positional rankings
- Fantasy Football Calculator data
- merged player database
- FantasyPros API allowance

The target state before the actual draft is:

```text
Player data: READY
```

There are three refresh operations:

### Refresh All Online Data

Refreshes:

1. FantasyPros API
2. Fantasy Football Calculator
3. merged player database

This consumes four FantasyPros API calls.

### Refresh FFC Only

Refreshes:

1. Fantasy Football Calculator
2. merged player database

This consumes no FantasyPros API calls.

### Rebuild Player Database

Rebuilds the merged player database from the data already present on disk.

This is useful after manually replacing the FantasyPros CSV files and consumes no online API calls.

Command-line status check:

```bash
python data_status.py
```

## Running the Application

The application is a Flask application served by Waitress.

Typical local/manual launch:

```bash
source venv/bin/activate
waitress-serve --listen=0.0.0.0:8080 app:app
```

On the Raspberry Pi it normally runs through the `busy-working` systemd service.

Useful commands:

```bash
sudo systemctl status busy-working
sudo systemctl restart busy-working
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

## Environment

Typical Python setup:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Local credentials and tokens are stored outside Git.

## Development Checks

After modifying Python code:

```bash
python -m py_compile *.py tools/*.py
git diff --check
```

Before committing:

```bash
git status --short
git diff --check --cached
```

## Repository Layout

```text
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
│   └── downloaded ranking data and local usage state
├── tools/
│   └── historical_replay.py
├── templates/
├── static/
├── README.md
└── ROADMAP.md
```

Runtime databases, caches, credentials, downloaded rankings and backups are excluded from Git.

## Draft-Day Workflow

The high-level draft-day sequence is:

1. Download the latest FantasyPros Overall ADP CSV.
2. Download the latest FantasyPros positional ranking CSVs.
3. Replace the files in `data/`.
4. Refresh online data.
5. Rebuild the merged player database.
6. Confirm `python data_status.py` reports `READY`.
7. Confirm the application health check succeeds.
8. Open Yahoo and the Busy Working Fantasy Assistant.
9. Confirm the real draft order and pick #8.
10. Start Draft Night.
11. Record each Yahoo selection manually.
12. Use Undo immediately if a pick is entered incorrectly.
13. Confirm the draft completes at pick 168.

See [ROADMAP.md](ROADMAP.md) for the detailed checklist and current priorities.

## In-Season Direction

After the draft, the project will transition from a draft assistant into a weekly fantasy-management assistant.

Planned areas include:

- My Team dashboard
- roster synchronisation
- waiver recommendations
- add/drop analysis
- start/sit recommendations
- injuries and availability
- bye-week planning
- opponent and matchup analysis
- trade analysis
- weekly summaries
- team-name and logo generation after the final roster is known

## Development

Development priorities, technical debt and future features are tracked in [ROADMAP.md](ROADMAP.md).

The current priority is **2026 Draft Night reliability**.

## Disclaimer

This is a personal, non-commercial hobby project.

It is not affiliated with or endorsed by Yahoo, FantasyPros or Fantasy Football Calculator.

It does not currently submit Yahoo transactions, waiver claims, lineup changes or trades.
