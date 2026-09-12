# Busy Working Fantasy Assistant — Roadmap

This roadmap tracks the current state, immediate priorities and longer-term direction of the Busy Working Fantasy Assistant.

The guiding principle is to make draft night reliable first, then evolve the project into a useful season-long assistant without adding complexity for its own sake.

## Current Status

The assistant currently supports:

- [x] 12-team Busy Working league configuration
- [x] Pick #8 snake-draft support
- [x] 14-round draft
- [x] Mock Draft mode
- [x] Draft Night mode
- [x] Manual live-pick recording
- [x] Undo support
- [x] SQLite draft persistence
- [x] Resume active actual draft after restart
- [x] Draft Night database backup
- [x] Abandon actual draft safely
- [x] Correct 168-pick draft completion
- [x] Draft-complete UI
- [x] Best Available display
- [x] Your Roster draft board
- [x] FantasyPros Overall ADP integration
- [x] FantasyPros positional-ranking CSV integration
- [x] FantasyPros tier integration
- [x] Fantasy Football Calculator integration
- [x] Data freshness/status reporting
- [x] Merged player database
- [x] Historical recommendation replay tool
- [x] QB positional-scarcity logic
- [x] TE positional-scarcity logic
- [x] QB2 discipline
- [x] TE2 / TE3 roster protection
- [x] RB/WR bench-depth balancing
- [x] K/DST late-round timing
- [x] K/DST FantasyPros positional-quality weighting
- [x] K/DST elite-depletion awareness
- [x] K/DST recent-run awareness
- [x] Waitress production server
- [x] systemd service
- [x] FantasyPros local API-call accounting
- [x] FantasyPros API allowance displayed on Settings
- [x] Full FantasyPros refresh blocked when fewer than four calls remain
- [x] FFC-only refresh path
- [x] Player-database-only rebuild path
- [x] Move manually downloaded CSV data into `data/`
- [x] Recommendation-engine regression testing
- [x] Recommendation-engine code freeze
- [x] My Team roster dashboard
- [x] Yahoo manual roster / free-agent snapshot import
- [x] Yahoo data-provider abstraction
- [x] Weekly Assistant dashboard
- [x] Recommended weekly starting lineup
- [x] Bench and IR review
- [x] Player-status watch
- [x] Upcoming lineup-lock tracking
- [x] Transaction deadline awareness
- [x] ADD / DROP transaction recommendations
- [x] Multi-week transaction scoring
- [x] Roster-role classification
- [x] Replacement-security framework
- [x] Bye-week concentration analysis
- [x] Future bye-coverage warnings
- [x] Bye coverage included in transaction scoring
- [x] Recommendation diversity for duplicate bye fixes

## Current Milestone — In-Season Phase 2: Weekly Assistant + Yahoo API Integration

The 2026 draft is complete and preserved, and the first version of the season-long Weekly Assistant is operational.

The immediate priority is to replace the manual Yahoo snapshot with approved read-only Yahoo Fantasy API data while keeping the existing manual import as a fallback. The Weekly Assistant should then be hardened using live league context such as current week, roster state, available players and waiver priority.

### Now — Draft-Day Readiness

- [x] Confirm Settings clearly shows each data source
- [x] Confirm missing / stale / current status is obvious
- [x] Confirm merged database rebuild occurs when source data changes
- [x] Verify manual CSV replacement workflow
- [x] Verify FFC-only refresh workflow
- [x] Verify full online refresh quota protection
- [x] Verify daily FantasyPros counter reset
- [x] Verify `Player data: READY` workflow in rehearsal
- [x] Confirm `Player data: READY` on actual draft day
- [x] Perform final service / health check on draft day
- [x] Confirm final Yahoo draft order and pick #8 before starting
- [x] Start actual Draft Night session
- [x] Complete real draft and confirm 168 picks recorded

### Draft-Day Data Checklist

- [x] Download latest FantasyPros Overall ADP CSV
- [x] Download latest FantasyPros QB rankings CSV
- [x] Download latest FantasyPros RB rankings CSV
- [x] Download latest FantasyPros WR rankings CSV
- [x] Download latest FantasyPros TE rankings CSV
- [x] Download latest FantasyPros K rankings CSV
- [x] Download latest FantasyPros DST rankings CSV
- [x] Replace files in `data/`
- [x] Refresh FantasyPros API data
- [x] Refresh Fantasy Football Calculator data
- [x] Rebuild merged player database
- [x] Run `python data_status.py`
- [x] Confirm `Player data: READY`
- [x] Confirm `curl http://127.0.0.1:8080/health` returns OK

The FantasyPros ALL / Superflex file is not required for the 2026 Busy Working draft.

### Draft-Night Operating Rules

- [x] Recommendation engine frozen for the 2026 draft
- [x] Only change recommendation logic before Draft Night if an actual functional bug is demonstrated
- [x] Record every Yahoo selection manually
- [x] Use Undo immediately if a pick is entered incorrectly
- [x] Confirm draft completes at pick 168

## Next — Immediately After the Draft

The first post-draft goal is to preserve the result and establish the initial season state, not to build the entire in-season assistant overnight.

- [x] Confirm completed actual draft is stored
- [x] Preserve final draft history
- [x] Confirm final roster
- [x] Export or display draft summary
- [x] Take an off-Pi backup of the completed draft database
- [x] Establish initial in-season roster state
- [x] Preserve historical draft recommendations for later analysis

### Team Identity

- [x] Identify likely franchise / star players from the final roster
- [x] Generate fantasy team-name ideas
- [x] Include player-name puns and pop-culture references
- [x] Shortlist favourite names
- [x] Develop matching logo concepts
- [x] Generate square Yahoo-compatible team logo
- [x] Set final Yahoo team name and image

## Completed Foundation — In-Season Phase 1: My Team

The initial post-draft roster-management foundation is now in place.

### My Team Dashboard

- [x] Current roster
- [x] Starter / bench positions
- [x] Bye weeks
- [x] Player status
- [x] Injury / availability indicators
- [ ] Current matchup
- [ ] Projected matchup score where suitable
- [x] Identify roster-depth concerns
- [x] Highlight players who require attention
- [x] Yahoo-style lineup-management interface
- [x] Team branding / Allen Wrench identity

### Roster Synchronisation

The application currently uses a manual Yahoo snapshot behind a provider abstraction so that the UI and recommendation engines do not depend directly on the source of the Yahoo data.

Preferred order remains:

1. Yahoo Fantasy API
2. Manual Yahoo snapshot fallback
3. Manual roster maintenance only if required

Current state:

- [x] Manual Yahoo roster import
- [x] Manual Yahoo available-player import
- [x] Manual Yahoo status import
- [x] Data freshness / captured-at display
- [x] Refresh workflow
- [x] `YahooDataProvider` abstraction
- [x] Keep raw Yahoo HTML / token material out of Git
- [ ] Replace manual provider data with Yahoo Fantasy API
- [ ] Retain manual snapshot as fallback after API launch

The season-management application must not depend entirely on Yahoo API access.


## Current — Yahoo Fantasy API Integration

Yahoo approved the Fantasy API application in September 2026. The agreement indicates an access period beginning 15 September 2026, so live API provisioning is expected on or after that date.

The integration should remain read-only.

- [x] Yahoo developer application created
- [x] OAuth web-authorisation flow proven
- [x] Yahoo Fantasy API application submitted
- [x] Yahoo Fantasy API application approved
- [x] Required confirmation completed
- [ ] Confirm Fantasy API endpoints work on / after 15 September 2026
- [ ] Implement API-backed `YahooDataProvider`
- [ ] Fetch current season from Yahoo
- [ ] Fetch current fantasy week from Yahoo
- [ ] Fetch current roster and roster slots
- [ ] Fetch player injury / availability statuses
- [ ] Fetch available / free-agent players
- [ ] Fetch live waiver priority
- [ ] Fetch league settings where useful
- [ ] Fetch matchup / opponent data
- [ ] Fetch league standings
- [ ] Confirm API refresh / token-renewal behaviour
- [ ] Add clear API failure / fallback status
- [ ] Preserve manual-import fallback
- [ ] Document Yahoo API compliance and attribution requirements

Yahoo should become the authoritative source for league context where the API exposes it. Calendar-derived season/week logic should remain only as a fallback.


## Current — In-Season Phase 2: Waivers and Transactions

The first transaction recommendation engine is operational.

### Completed

- [x] Suggested adds
- [x] Suggested drops
- [x] ADD / DROP pair recommendations
- [x] Roster-need awareness
- [x] Positional depth awareness
- [x] Multi-week projection outlook
- [x] Explain recommendations
- [x] Transaction deadline calculation
- [x] K / DST streaming awareness
- [x] Replacement-player comparison
- [x] Comparable-replacement counts
- [x] Roster-role classification
- [x] Replacement-security framework
- [x] Bye-week awareness
- [x] Full-roster future bye coverage
- [x] FLEX-aware bye coverage
- [x] Future bye-risk scoring
- [x] Transaction-score adjustment for bye coverage
- [x] Avoid duplicate recommendations that solve the same bye problem
- [x] Future Bye Coverage dashboard

### Still to add / improve

- [ ] Dedicated available-player ranking view
- [ ] Live waiver priority from Yahoo
- [ ] Include waiver priority in replacement-security scoring
- [ ] Better injury-replacement recommendations
- [ ] Recent usage / opportunity changes
- [ ] Targets
- [ ] Carries
- [ ] Snap share where data is available
- [ ] Upcoming matchup quality
- [ ] Rest-of-season ranking / value
- [ ] Waiver-processing-state awareness
- [ ] Distinguish free-agent moves from waiver claims
- [ ] Record transaction recommendations and outcomes for later analysis

The engine should increasingly answer not only "who scores more?" but also "what does this move do to the roster now and later in the season?"


## Current — In-Season Phase 3: Start / Sit

The first weekly lineup engine is operational.

### Completed

- [x] Generate legal starting lineup
- [x] QB selection
- [x] RB selection
- [x] WR selection
- [x] TE selection
- [x] FLEX optimisation
- [x] K selection
- [x] DST selection
- [x] Injury / availability filtering
- [x] Bench display
- [x] IR review
- [x] Upcoming lineup locks
- [x] Next-decision summary
- [x] Local UK kickoff-time conversion
- [x] Current actual-points tracking
- [x] Projected-final score

### Still to add / improve

- [ ] Compare realistic close lineup alternatives
- [ ] Explain close start / sit decisions
- [ ] Thursday Night Football-specific decision support
- [ ] Sunday active / inactive-player check
- [ ] High-floor vs high-upside recommendations
- [ ] Late-game FLEX planning
- [ ] Use matchup state to alter risk / upside preference
- [ ] Use live Yahoo current-week context rather than fallback calendar logic

Draft ADP should have little or no influence on weekly start/sit decisions once the season is underway.


## Later — Matchups and Opponents

- [ ] Opponent roster view
- [ ] Weekly projection comparison
- [ ] Identify matchup strengths / weaknesses
- [ ] Track remaining players during live gameweeks
- [ ] Risk / upside recommendations based on matchup state
- [ ] League standings
- [ ] Playoff-position awareness

## Later — Trades

Optional rather than essential.

- [ ] Trade evaluator
- [ ] Positional-need comparison
- [ ] Rest-of-season ranking
- [ ] Replacement value
- [ ] Two-for-one trade analysis
- [ ] Identify possible trading partners
- [ ] Avoid evaluating trades using draft ADP alone

## Suggested Weekly Rhythm

### Monday

- [ ] Review weekend
- [ ] Review injuries
- [ ] Review player usage
- [ ] Identify weak roster positions

### Tuesday

Primary waiver day:

- [ ] Refresh relevant data
- [ ] Run waiver recommendations
- [ ] Review add/drop analysis

### Wednesday

- [ ] Review waiver results
- [ ] Update roster state
- [ ] Identify remaining free agents

### Thursday

- [ ] Run start/sit review
- [ ] Review Thursday Night Football decisions
- [ ] Review injury / status changes

### Friday / Saturday

- [ ] Lightweight injury / news review
- [ ] Avoid unnecessary API refreshes

### Sunday

- [ ] Final active / inactive check
- [ ] Final lineup recommendations
- [ ] Late-game FLEX planning

The goal is a short, useful weekly workflow rather than constant manual monitoring.

## FantasyPros API Usage Strategy

The configured free-plan allowance is currently treated as 50 calls per day.

A complete API ranking refresh currently consumes four calls:

- QB
- RB
- WR
- TE

Potential in-season rhythm:

- Tuesday
- Thursday
- Sunday morning

This would normally consume around 12 calls per week from those scheduled refreshes.

- [ ] Revisit API refresh cadence once in-season data requirements are understood

## Technical / Maintenance Backlog

- [ ] Move root-level `test_*.py` scripts into `tests/`
- [ ] Add automated regression tests
- [ ] Convert historical replay cases into repeatable tests
- [ ] Remove old `.v1` / `.v2` development files after review
- [ ] Review `fantasypros_test.json`
- [ ] Add backup-retention policy
- [ ] Standardise application logging through Python `logging`
- [ ] Send application logs to journald via systemd
- [ ] Define sensible log levels and message format
- [ ] Review journald retention / disk limits
- [ ] Add off-Pi database backup
- [ ] Add report-only dependency maintenance check
- [ ] Review service monitoring
- [ ] Improve error handling around data refresh
- [ ] Improve refresh failure reporting
- [ ] Rename local project folder from `fantasy-assistant` to `nfl-fantasy-assistant`
- [ ] Search for hard-coded local paths before folder rename
- [ ] Recreate the Python virtual environment after folder rename
- [ ] Update the systemd service after folder rename

## Post-Season / 2027

### 2027/Draft improvements

- [ ] Add live player-status awareness to draft recommendations
- [ ] Add bye-week concentration awareness
- [ ] Improve recovery workflow after Yahoo disconnect / auto-pick

### League-Size Awareness

The current draft mechanics are largely flexible, but the strategy and FFC feed are calibrated for a 12-team league.

- [ ] Make draft strategy league-size aware
- [ ] Remove remaining 12-team assumptions
- [ ] Parameterise FFC ADP by league size
- [ ] Use separate FFC caches by league size
- [ ] Review positional-scarcity thresholds for deeper leagues
- [ ] Review K/DST timing rules for deeper leagues
- [ ] Regression-test 8 / 10 / 12 / 14 / 16-team drafts

### Data Architecture

- [ ] Consider moving player snapshots from JSON into SQLite
- [ ] Store historical ranking / data snapshots
- [ ] Store weekly roster snapshots
- [ ] Store waiver recommendations and outcomes
- [ ] Store start/sit recommendations and outcomes

### Recommendation Architecture

- [ ] Break recommendation engine into smaller modules
- [ ] Add formal regression test suite
- [ ] Separate draft scoring from season scoring
- [ ] Make season / year configuration dynamic
- [ ] Improve configurable league settings
- [ ] Consider optimisation-based lineup selection

### Busy Working League Intelligence

Longer-term, use historical league behaviour to make recommendations specific to this league.

- [ ] Track managers who draft QB early
- [ ] Track managers who take K/DST early
- [ ] Track managers who hoard RB/WR
- [ ] Detect typical positional runs
- [ ] Track waiver tendencies
- [ ] Track repeated streaming behaviour
- [ ] Build manager-specific draft tendencies

The long-term goal is to combine public player data with knowledge of how Busy Working actually behaves.

### Hosting

- [ ] Review whether Raspberry Pi remains the best long-term host
- [ ] Consider external hosting
- [ ] Consider secure remote access
- [ ] Consider PWA / mobile-friendly operation
- [ ] Maintain simple local fallback for Draft Night

## Parking Lot

Good ideas that are deliberately not current priorities:

- [ ] Multiple league support
- [ ] Full Yahoo write access
- [ ] Automated waiver submission
- [ ] Automated lineup changes
- [ ] Public / multi-user deployment
- [ ] Advanced visualisations
- [ ] Draft-history analytics
- [ ] Recommendation accuracy dashboard
- [ ] Player watch lists
- [ ] Notifications / alerts

## Priority Order

1. **Yahoo Fantasy API integration** — confirm live access and replace manual Yahoo snapshots with the API while retaining the fallback.
2. **Harden Weekly Assistant / waiver logic** — live waiver priority, replacement security, transaction-state awareness and better weekly recommendations.
3. **Matchups and opponent analysis** — opponent roster, matchup projection, standings and live matchup state.
4. **Player usage / injury intelligence** — richer opportunity data, news and injury-driven recommendations.
5. **Technical cleanup and reliability** — logging, tests, backups, folder rename and maintenance.
6. **2027 draft improvements**.

The order is intentionally flexible: a real live-season issue can promote a task if it reveals a material weakness in the system.

## Development Principle

The assistant should save time and improve fantasy decisions.

It should not become a system that requires constant maintenance just to keep playing fantasy football.
