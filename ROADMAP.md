# Busy Working Fantasy Assistant Roadmap

This roadmap tracks the development of the Busy Working Fantasy Assistant.

The immediate priority is reliability for the 2026 draft. Larger architectural changes and season-management features should not be allowed to destabilise the draft-night application.

---

# Current Milestone: 2026 Draft Night

## Completed

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
- [x] Move manually downloaded CSV data into `data/`
- [x] Recommendation-engine regression testing
- [x] Recommendation-engine code freeze

---

# Before Draft Night

## Priority 1 — FantasyPros API Usage

- [x] Show current FantasyPros API usage on Settings
- [x] Show:
  - calls used today
  - configured daily limit
  - calls remaining
  - last API call time
- [x] Clearly explain that the value is locally recorded
- [x] Verify daily counter resets correctly
- [x] Warn before a refresh when API allowance is low
- [x] Prevent a full four-position refresh if fewer than four calls remain
- [x] Consider warning thresholds, for example:
  - normal
  - low
  - refresh unavailable

FantasyPros does not currently return a usable server-side remaining-quota header, so the application maintains its own local counter.

## Priority 2 — Data Refresh Workflow

Make draft-day refreshing simple and difficult to get wrong.

- [x] Confirm Settings clearly shows each data source
- [x] Confirm missing/stale/current status is obvious
- [x] Confirm merged database rebuild occurs when required
- [x] Verify manual CSV replacement workflow
- [x] Verify online refresh workflow
- [z] Confirm `Player data: READY` before Draft Night

Manual files required:

- [ ] FantasyPros Overall ADP
- [ ] FantasyPros QB rankings
- [ ] FantasyPros RB rankings
- [ ] FantasyPros WR rankings
- [ ] FantasyPros TE rankings
- [ ] FantasyPros K rankings
- [ ] FantasyPros DST rankings

The FantasyPros ALL/Superflex file is not required for the 2026 Busy Working draft.

## Priority 3 — Draft Night Checklist

Create a short operational checklist.

Suggested sequence:

1. Download latest FantasyPros CSV files.
2. Replace files in `data/`.
3. Refresh FantasyPros API data.
4. Refresh Fantasy Football Calculator data.
5. Rebuild player database.
6. Run:

   ```bash
   python data_status.py
Confirm READY.
Restart application if code/config has changed.

Confirm:

curl http://127.0.0.1:8080/health
Open Yahoo draft.
Open Busy Working Fantasy Assistant.
Confirm actual draft order and pick #8.
Start Draft Night.
Record every Yahoo selection manually.
Use Undo immediately if a pick is entered incorrectly.
Confirm draft completes at pick 168.
Draft-Night Code Freeze

Recommendation logic is frozen for the 2026 draft.

Only make recommendation-engine changes before Draft Night when:

an actual functional bug is demonstrated
stored draft data is at risk
Draft Night cannot operate correctly

Do not tune recommendations merely to make another mock roster look prettier.

## Immediately After the Draft

The immediate goal is to preserve the result rather than immediately build the whole season-management system.

 Confirm completed actual draft is stored
 Preserve final draft history
 Confirm final roster
 Export or display draft summary
 Take an off-Pi backup of the completed draft database
 Establish the initial in-season roster state
 Preserve historical draft recommendations for later analysis

No requirement to build waiver/start-sit functionality immediately after the draft.

## Team Identity

- [ ] Identify likely franchise/star players from final roster
- [ ] Generate fantasy team-name ideas
- [ ] Prefer player-name puns / pop-culture references
- [ ] Shortlist favourite names
- [ ] Develop matching logo concepts
- [ ] Generate square team logo
- [ ] Set final Yahoo team name and image


## In-Season Phase 1 — My Team

Build the post-draft home screen.

My Team Dashboard
 Current roster
 Starter / bench positions
 Bye weeks
 Player status
 Injury/availability indicators
 Current matchup
 Projected matchup score where suitable
 Identify weak roster positions
 Highlight players who require attention
Roster Synchronisation

Preferred order:

Yahoo Fantasy API
FantasyPros My Playbook investigation
Simple manual roster maintenance
 Re-test Yahoo Fantasy API access
 Investigate FantasyPros My Playbook as a possible roster-data fallback
 Build manual add/drop interface if automated synchronisation remains unavailable

The season-management application must not depend entirely on Yahoo API access.

In-Season Phase 2 — Waivers

This is likely to be the highest-value weekly feature.

 Available-player ranking
 Suggested adds
 Suggested drops
 ADD / DROP pair recommendations
 Roster-need awareness
 Bye-week awareness
 Injury replacements
 Recent usage/opportunity changes
 Targets
 Carries
 Snap share where data is available
 Upcoming matchup quality
 Multi-week outlook
 Waiver priority awareness
 Explain recommendations

Example goal:

ADD Player X
DROP Player Y

Why:
- Player X has gained a larger role
- WR depth is currently weak
- Player Y is unlikely to enter the starting lineup
- Player X has favourable upcoming fixtures
In-Season Phase 3 — Start / Sit
 Generate legal starting lineups
 Compare realistic lineup alternatives
 QB recommendation
 RB recommendation
 WR recommendation
 TE recommendation
 FLEX optimisation
 K recommendation
 DST recommendation
 Injury/status checks
 Thursday-night decision support
 Sunday inactive-player check
 High-floor vs high-upside recommendations
 Explain each close decision

Draft ADP should have little or no influence on weekly start/sit decisions once the season is underway.

In-Season Phase 4 — Matchups and Opponents
 Opponent roster view
 Weekly projection comparison
 Identify matchup strengths/weaknesses
 Track remaining players during live gameweeks
 Risk/upside recommendations based on matchup state
 League standings
 Playoff-position awareness
In-Season Phase 5 — Trades

Optional rather than essential.

 Trade evaluator
 Positional need comparison
 Rest-of-season ranking
 Replacement value
 Two-for-one trade analysis
 Identify possible trading partners
 Avoid evaluating trades using draft ADP alone
Suggested Weekly Rhythm

Initial target workflow:

Monday
Review weekend
Review injuries
Review player usage
Identify weak roster positions
Tuesday

Primary waiver day:

refresh relevant data
waiver recommendations
add/drop analysis
Wednesday
review waiver results
update roster state
identify remaining free agents
Thursday
start/sit review
Thursday Night Football decisions
injury/status review
Friday / Saturday
lightweight injury/news review
avoid unnecessary API refreshes
Sunday
final active/inactive check
final lineup recommendations
late-game FLEX planning

The goal is a short, useful weekly workflow rather than constant manual monitoring.

FantasyPros API Usage Strategy

The configured free-plan allowance is currently treated as 50 calls per day.

A complete API ranking refresh currently consumes four calls:

QB
RB
WR
TE

Avoid unnecessary full refreshes.

A possible in-season rhythm is:

Tuesday
Thursday
Sunday morning

That would normally consume around 12 calls per week from those scheduled refreshes.

This should be revisited once the in-season data requirements are understood.

Post-Draft Technical Work

Once Draft Night is safely complete:

 Move root-level test_*.py scripts into tests/
 Add automated regression tests
 Convert historical replay cases into repeatable tests
 Remove old .v1 / .v2 development files after review
 Review fantasypros_test.json
 Add backup-retention policy
 Add log-retention policy
 Add off-Pi database backup
 Add report-only dependency maintenance check
 Review service monitoring
 Improve error handling around data refresh
 Improve refresh failure reporting
Post-Season / 2027

Larger changes can wait until there is no live-season risk.

Data Architecture
 Consider moving player snapshots from JSON into SQLite
 Store historical ranking/data snapshots
 Store weekly roster snapshots
 Store waiver recommendations and outcomes
 Store start/sit recommendations and outcomes
Recommendation Architecture
 Break recommendation engine into smaller modules
 Add formal regression test suite
 Separate draft scoring from season scoring
 Make season/year configuration dynamic
 Improve configurable league settings
 Consider optimisation-based lineup selection
Busy Working League Intelligence

Longer-term, use historical league behaviour to make recommendations specific to this league.

Potential examples:

managers who draft QB early
managers who take K/DST early
managers who hoard RB/WR
typical positional runs
waiver tendencies
repeated streaming behaviour
manager-specific draft tendencies

The long-term goal is to combine public player data with knowledge of how Busy Working actually behaves.

Hosting
 Review whether Raspberry Pi remains the best long-term host
 Consider external hosting
 Consider secure remote access
 Consider PWA/mobile-friendly operation
 Maintain simple local fallback for Draft Night
Parking Lot

Good ideas that are deliberately not current priorities:

 Multiple league support
 Full Yahoo write access
 Automated waiver submission
 Automated lineup changes
 Public/multi-user deployment
 Advanced visualisations
 Draft-history analytics
 Recommendation accuracy dashboard
 Player watch lists
 Notifications/alerts
Development Principle

The assistant should save time and improve fantasy decisions.

It should not become a system that requires constant maintenance just to keep playing fantasy football.

- [ ] Make draft strategy league-size aware
- [ ] Remove remaining 12-team assumptions
- [ ] Parameterise FFC ADP by league size
- [ ] Regression-test 8/10/12/14/16-team drafts

