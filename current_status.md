# Busy Working NFL — current handover

Last updated: 22 October 2026 (Europe/London).

## Read this first in a new chat

This is the working handover for `DansJavaStuff/busy-working-fantasy-assistant`.
Read this file, then inspect the current Git branch, working tree and upstream
main before editing. Use `README.md` for setup and `ROADMAP.md` for the broader
backlog. Those documents still contain older draft-era descriptions and unchecked
items that have since been delivered; this handover describes our latest session.

Update this file whenever a task finishes, priorities change, or work pauses.
Replace stale information rather than appending an endless chat transcript.
Record unfinished work, validation, deployment status and the next concrete step.
Keep credentials, raw Yahoo HTML, private database contents and tokens out of Git.

## User preferences and authorization

- Daniel wants completed, tested work committed, pushed and merged automatically
  when required tests and CI/security checks pass. Do not ask for confirmation
  for each routine push or merge.
- Finish an active fix before moving to another development task.
- Keep the app's workflow simple and explain recommendations in plain language.
- Actual Yahoo waiver claims and lineup changes remain the user's responsibility;
  recording or saving them in the assistant does not submit them to Yahoo.

## Application and data model

- Personal assistant for the 2026 Busy Working Yahoo NFL league (12 teams).
- Hosted on Daniel's Raspberry Pi 2, using systemd service `busy-working` and nginx.
- Pi checkout: `/home/daniel/fantasy-assistant`.
- The draft is complete. Current work focuses on weekly lineups, availability,
  waivers, roster depth, bye coverage and recommendation clarity.
- Yahoo Player List downloads include all listed players, including rostered
  players. They populate projections/actual scores and league ownership; a
  separate roster table records Daniel's roster and views bring the data together.
  Do not rebuild the roster from a filtered available-player list.
- Projection inputs include current-week, following-week and four-week files,
  with paginated offensive players plus separate K and DEF files, including
  `Yahoo_Player_list_K_4week-Proj.html` and
  `Yahoo_Player_list_DEF_4week-Proj.html`.
- Ownership/status must use the freshest file observation across projection
  horizons. Older week5/week6/four-week files must not override newer week4 data.
- MyTeam HTML has not been maintained reliably. Can't Cut players and waiver
  priority are confirmed manually in the app. Protect Can't Cut players in all
  drop recommendations.
- Manual HTML imports are the working source. Yahoo API integration remains on
  the broader roadmap; do not assume live API access works without verifying it.
- Yahoo is the projection baseline; Sleeper supplies an independent second
  opinion for shortlisted offensive players, rescored to the league's points.

## Current workflow and reported team state

The "What to do today" checklist guides the weekly workflow alongside History,
Weekly, Available, Waivers, Roster and league settings.

- After the gameweek: import actuals and verify History against Yahoo; refresh
  upcoming projections, confirm waiver priority and this week's Can't Cut list.
- Review Available, submit chosen claims on Yahoo, and record them in the app.
- After processing: record outcomes, refresh ownership data and return to
  Available for remaining pickups.
- Before games: refresh projections/status, review Weekly and K/DEF options,
  check actual Yahoo availability and make the final lineup changes on Yahoo.
- Latest reported waiver priority: #10 (reconfirm after transactions).
- Dalton Schultz and MarShawn Lloyd claims succeeded. Sutton was dropped to add
  Lloyd. A subsequent Sutton suggestion was versus Bateman, not a reversal of
  the Lloyd move; it was a HOLD rather than a recommended immediate claim.
- Puka Nacua's stale Out status has been fixed; Daniel confirmed he returned to
  the recommended starting lineup.
- The Sunday 4 October plan above is historical. No current roster, waiver
  priority or latest data freshness has been confirmed as of 14 October.

## Recent completed fixes

- Freshest Yahoo ownership wins across files; Luther Burden III no longer appears
  available after newer downloads show him on another fantasy team.
- Cancelling "Save lineup" confirmation no longer leaves the busy overlay stuck
  (PR #18).
- Start/Sit comparisons exclude unavailable bench players (PR #20).
- A saved recommended lineup can be updated again using "Update Saved Lineup
  from Recommendation" (PR #21). Existing actual-score locks are preserved.
- Freshest injury observation can clear an old O/IR status even when the newer
  HTML has no status marker (PR #22).
- Recommendation clarity is finished (PR #23):
  - HOLD/WATCH suggestions remain visible but do not become waiver instructions.
  - Speculative claims are excluded from the normal actionable waiver queue.
  - Weekly and Available share the speculative-claim/fallback assessment.
  - Fallback comparisons use comparable individual player projections.
  - UI separates weekly lineup gain, four-week outlook, bench depth and combined
    move score; the combined score is not a projected points increase.
- Matchup labels are context, not the recommendation itself. Evans can be
  recommended over Pollard despite a tougher matchup when both Yahoo and Sleeper
  project more points. Early-season matchup figures have small samples.

## Latest screen change — 14 October 2026

- Available / Tracked Moves now separates pending moves from completed history.
- History is collapsed by default; each table scrolls within a bounded area with
  sticky headings. Row details expand to show type, recommendation and dates.
- Pending outcomes use a dropdown and Save button, with all four outcomes kept.
- The existing 20-move query limit is unchanged and stated beside history.
- CI identified CVE-2026-102598 in Werkzeug 3.1.8; the dependency pin is
  updated to the audit-recommended fix, 3.1.9.
- No roster, scoring or waiver-processing logic changed.
- Validation: 140 unit tests pass; changed templates compile and render pending,
  completed, mixed and empty states. Browser visual QA was unavailable because
  the local Playwright browser executable is missing.
- The supplied screenshot could not be read from its attachment path; this change
  was based on the current Available template. Daniel confirmed the layout looks much better on 14 October.

## Latest recommendation change — 21 October 2026

- Daniel approved treating DEF/K as weekly streams in the 12-team league.
- Transaction scores and move labels for DEF/K now use current-week lineup gain
  only; four-week projections, bench value and future bye adjustments cannot
  outweigh a better stream. Future metrics remain visible as context.
- Available's DEF/K positional value also uses current-week projections only.
- All DEF/K candidates reach transaction evaluation, even outside the general
  60-player candidate cap. Future-bye deduplication does not hide streams.
- Offensive-player transaction scoring remains unchanged; roster legality,
  availability and Can't Cut checks still apply.
- Regression: Colts 5.51, Lions 5.79 (four-week average 6.54), Titans FA 7.72
  (average 4.12): Titans scores +2.21 and STRONG MOVE; Lions +0.28 and HOLD.
  Covered for both DST and K, including a future-only upgrade being rejected.
- CI identified PYSEC-2026-4320 in certifi 2026.7.22; updated its pin to
  the audit-recommended fixed release 2026.10.19.
- Validation: 143 unit tests pass. Deployment is pending the Pi update.

## DEF/K second-source comparison — 21 October 2026

- Live Sleeper Week7 K/DEF projection responses identify `company: rotowire`.
  Correct earlier explanation: no direct RotoWire integration exists, but the
  Sleeper feed itself carries RotoWire projections; do not count these as two
  independent opinions.
- Weekly streaming cards and Available now expose add/keep comparison, provider,
  provider update time and coverage notes, including unavailable/disagreement.
- K uses total field goals minus 40–49/50+ makes for sub-40 attempts because
  short-distance bands can be incomplete. All sub-40 kicks score 2 in this league.
- DEF uses supplied points-allowed bands and aggregate defensive TDs without
  re-adding interception/fumble TD components. It is a rescored estimate, not an
  expected score derived from a probability distribution. Missing required
  components yield unavailable; preset Sleeper fantasy totals are never substituted.
- DEF/K comparison is evidence only: Yahoo still drives move scores and ranking.
  Offensive blending remains unchanged. Per-position feed errors preserve other
  comparisons. Feed and Available caches expire after 15 minutes.
- Live captured Week7 feed rescored Titans 7.33, Colts 5.36, Lions 5.43; this
  supports the current-week Titans move. These figures are observations, not
  durable player advice.
- Validation: 148 unit tests pass, including Available keeping Yahoo ranking
  unchanged when the second source disagrees. Changed templates compile and
  render partial/missing evidence; live K/DEF feed probes succeeded. Browser
  visual QA remains unavailable locally. Deployment awaits Pi update and UI confirmation.

## Wider Weekly and Available layouts — 21 October 2026

- Daniel supplied desktop screenshots confirming the second-source comparison
  renders on the Pi. Both Yahoo and RotoWire marginally favour Bates over Smack;
  HOLD / too close to call is appropriate.
- Added a scoped 1800px container for Weekly and Available (previously 1200px).
  Existing mobile padding/layout remains in force; other pages retain their width.
- Weekly move cards keep three columns at desktop widths of 1200px and above,
  and align at the top so expanded details do not stretch neighbouring cards.
- The unmatched Jr. names identified here are addressed by the suffix-matching
  change below, verified against the live provider feed.

## Mobile summary view — 21 October 2026

- Daniel prioritises his MacBook display (15.4-inch Retina, 2880x1800 physical
  pixels; browser CSS viewport depends on scaling). Desktop retains full detail.
- Weekly and Available default to a summary at widths up to 700 CSS pixels:
  decisions, add/drop, status, current-week points and deadlines remain visible.
- Available shortlist, waiver queue and Start/Sit tables become compact labelled
  cards. Long explanations and secondary metrics are hidden in summary mode.
- Source-comparison verdicts and speculative warnings remain visible. A mobile
  Show details / Show summary toggle restores full reasoning and tables.
- If JavaScript is unavailable, full content remains accessible by default.
- Validation: 148 tests pass; templates compile; JS syntax/toggle smoke checks
  pass. Browser visual QA is still pending user confirmation.

## Suffix matching and comparison dialogs — 21 October 2026

- Live Week7 Sleeper feeds confirmed Chris Godwin/TB/WR, Tyrone Tracy/NYG/RB,
  and Mike Washington/LV/RB omit the Jr. suffix Yahoo supplies.
- Exact names are preferred. If absent, suffix-insensitive matching is permitted
  only with matching team and position and exactly one candidate. Ambiguous,
  wrong-team, wrong-position and fuzzy-name matches stay unavailable.
- Desktop (>700px) second-source comparisons open in an accessible native dialog
  with Close/Escape and focus return. The grid no longer grows a row when a
  comparison opens. Mobile and browsers without dialog support retain details.
- Validation: all 150 tests pass; templates compile; JS syntax/dialog smoke
  checks pass; live captured feed now matches all three players (rescored 7.75,
  6.33 and 5.29 respectively). Browser visual QA of the dialog is pending.
- Previous widened desktop screenshots confirmed the layout and Titans starting
  slot; mobile summary has not yet been visually confirmed.

## Temporary Sleeper connection failures — 22 October 2026

- Daniel reported a temporary DNS resolution failure for api.sleeper.com exposed
  as a long raw requests/urllib3 error on Available. This is a connection error,
  not a missing Cowboys projection or a Yahoo data problem.
- Feed exceptions now show a short temporary-unavailability message. Full error
  details and traceback go to Python logs (systemd journal on the Pi).
- Available caches failed comparison responses for 60 seconds instead of 15
  minutes; reload after a minute retries without a new Yahoo import. Successful
  rankings/feeds retain the 15-minute cache. No background retry is scheduled.
- Validation: all 151 tests pass, including failure/cache/recovery with unchanged
  Yahoo data. Persistent DNS failures still require checking the Pi's networking;
  this change improves presentation/recovery and does not repair DNS itself.
- Daniel confirmed the suffix-matching/dialog changes look better on the Pi.

## Validation and deployment

Previous recommendation-clarity baseline: PR #23, merged to main as
`9dd5d137f50ab0e705bd66b2392c48853f9d67e2`.
Link: https://github.com/DansJavaStuff/busy-working-fantasy-assistant/pull/23

- All 140 unit tests passed; templates compiled and diff checks passed.
- Required CI tests/security checks and post-merge workflows passed. Code-quality
  checks are advisory in the current workflow; do not describe that as zero lint
  warnings across the repository.
- Daniel was given the following Pi update commands; deployment of PR #23 has
  not yet been confirmed in this chat:

```sh
cd ~/fantasy-assistant
git pull --ff-only
sudo systemctl restart busy-working
```

Standard test command with dependencies installed:

```sh
python -m unittest discover -s tests -v
```

## Unfinished work and next development decision

The recommendation clarity and tracked-moves layout tasks are complete.
The latest task adds DEF/K second-source comparisons. Confirm the comparison
coverage and Titans/Lions ranking after updating the Pi and refreshing.

After Sunday's refresh, collect any concrete recommendation discrepancies, then
choose the next task using the broader roadmap. Possible follow-up: compare
Week4 recommendations/projections with actual outcomes. This is a proposal, not
an agreed development commitment.

One technical item to verify before claiming full kickoff-lock protection:
existing lineup locking primarily uses recorded actual scores. Exact kickoff
locking and late-game FLEX behaviour have not been audited in this session.

## Checkout cautions for the next agent

The current scratch checkout is on `fix-available-cant-cut` with accumulated local
commits; local ancestry does not match remote main even though the application
files reflect the merged work. Inspect before pulling or publishing; use a clean
checkout when necessary.

There is an unrelated local executable-mode difference for
`tools/grab_data_from_macbook.sh`. Daniel already pushed its executable bit to
remote main as `226b313`; do not accidentally publish a reversal or include it in
an unrelated change. Do not commit local dependency directories.
