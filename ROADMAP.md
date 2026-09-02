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

## Current Milestone — 2026 Draft Night

The immediate priority is reliability for the real 2026 draft. Recommendation logic is frozen unless a genuine functional bug is demonstrated.

### Now — Draft-Day Readiness

- [x] Confirm Settings clearly shows each data source
- [x] Confirm missing / stale / current status is obvious
- [x] Confirm merged database rebuild occurs when source data changes
- [x] Verify manual CSV replacement workflow
- [x] Verify FFC-only refresh workflow
- [x] Verify full online refresh quota protection
- [x] Verify daily FantasyPros counter reset
- [x] Verify `Player data: READY` workflow in rehearsal
- [ ] Confirm `Player data: READY` on actual draft day
- [ ] Perform final service / health check on draft day
- [ ] Confirm final Yahoo draft order and pick #8 before starting
- [ ] Start actual Draft Night session
- [ ] Complete real draft and confirm 168 picks recorded

### Draft-Day Data Checklist

- [ ] Download latest FantasyPros Overall ADP CSV
- [ ] Download latest FantasyPros QB rankings CSV
- [ ] Download latest FantasyPros RB rankings CSV
- [ ] Download latest FantasyPros WR rankings CSV
- [ ] Download latest FantasyPros TE rankings CSV
- [ ] Download latest FantasyPros K rankings CSV
- [ ] Download latest FantasyPros DST rankings CSV
- [ ] Replace files in `data/`
- [ ] Refresh FantasyPros API data
- [ ] Refresh Fantasy Football Calculator data
- [ ] Rebuild merged player database
- [ ] Run `python data_status.py`
- [ ] Confirm `Player data: READY`
- [ ] Confirm `curl http://127.0.0.1:8080/health` returns OK

The FantasyPros ALL / Superflex file is not required for the 2026 Busy Working draft.

### Draft-Night Operating Rules

- [x] Recommendation engine frozen for the 2026 draft
- [ ] Only change recommendation logic before Draft Night if an actual functional bug is demonstrated
- [ ] Record every Yahoo selection manually
- [ ] Use Undo immediately if a pick is entered incorrectly
- [ ] Confirm draft completes at pick 168

## Next — Immediately After the Draft

The first post-draft goal is to preserve the result and establish the initial season state, not to build the entire in-season assistant overnight.

- [ ] Confirm completed actual draft is stored
- [ ] Preserve final draft history
- [ ] Confirm final roster
- [ ] Export or display draft summary
- [ ] Take an off-Pi backup of the completed draft database
- [ ] Establish initial in-season roster state
- [ ] Preserve historical draft recommendations for later analysis

### Team Identity

- [ ] Identify likely franchise / star players from the final roster
- [ ] Generate fantasy team-name ideas
- [ ] Include player-name puns and pop-culture references
- [ ] Shortlist favourite names
- [ ] Develop matching logo concepts
- [ ] Generate square Yahoo-compatible team logo
- [ ] Set final Yahoo team name and image

## Near Term — In-Season Phase 1: My Team

Build the post-draft home screen and establish reliable roster synchronisation.

### My Team Dashboard

- [ ] Current roster
- [ ] Starter / bench positions
- [ ] Bye weeks
- [ ] Player status
- [ ] Injury / availability indicators
- [ ] Current matchup
- [ ] Projected matchup score where suitable
- [ ] Identify weak roster positions
- [ ] Highlight players who require attention

### Roster Synchronisation

Preferred order:

1. Yahoo Fantasy API
2. FantasyPros My Playbook investigation
3. Simple manual roster maintenance

Planned work:

- [ ] Re-test Yahoo Fantasy API access
- [ ] Investigate FantasyPros My Playbook as a possible roster-data fallback
- [ ] Build manual add/drop interface if automated synchronisation remains unavailable

The season-management application must not depend entirely on Yahoo API access.

## Near Term — In-Season Phase 2: Waivers

This is likely to be the highest-value weekly feature.

- [ ] Available-player ranking
- [ ] Suggested adds
- [ ] Suggested drops
- [ ] ADD / DROP pair recommendations
- [ ] Roster-need awareness
- [ ] Bye-week awareness
- [ ] Injury replacements
- [ ] Recent usage / opportunity changes
- [ ] Targets
- [ ] Carries
- [ ] Snap share where data is available
- [ ] Upcoming matchup quality
- [ ] Multi-week outlook
- [ ] Waiver priority awareness
- [ ] Explain recommendations

Example target output:

```text
ADD Player X
DROP Player Y

Why:
- Player X has gained a larger role
- WR depth is currently weak
- Player Y is unlikely to enter the starting lineup
- Player X has favourable upcoming fixtures
```

## Near Term — In-Season Phase 3: Start / Sit

- [ ] Generate legal starting lineups
- [ ] Compare realistic lineup alternatives
- [ ] QB recommendation
- [ ] RB recommendation
- [ ] WR recommendation
- [ ] TE recommendation
- [ ] FLEX optimisation
- [ ] K recommendation
- [ ] DST recommendation
- [ ] Injury / status checks
- [ ] Thursday Night Football decision support
- [ ] Sunday inactive-player check
- [ ] High-floor vs high-upside recommendations
- [ ] Explain each close decision

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

1. **2026 Draft Night reliability** — current.
2. Preserve completed draft and final roster.
3. Team identity: name and logo.
4. My Team / roster synchronisation.
5. Waiver recommendations.
6. Start / sit recommendations.
7. Matchups and opponent analysis.
8. Technical cleanup and post-season architecture work.

The order is intentionally flexible: a real draft-night or live-season issue can promote a task if it reveals a material weakness in the system.

## Development Principle

The assistant should save time and improve fantasy decisions.

It should not become a system that requires constant maintenance just to keep playing fantasy football.
