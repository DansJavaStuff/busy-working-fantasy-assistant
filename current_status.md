# Busy Working NFL — current handover

Last updated: 3 October 2026 (Europe/London).

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
- Next playing task agreed: Sunday 4 October, refresh data and review final
  lineup before the expected 18:00 BST games. Check any earlier player locks too.

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

## Validation and deployment

Last application change: PR #23, merged to main as
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

No unfinished application fix remains from this session. The recommendation
clarity task is complete. No subsequent development task has been selected yet.

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
