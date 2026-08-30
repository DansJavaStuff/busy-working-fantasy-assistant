# Busy Working Fantasy Assistant Roadmap

## Current Status
- Flask app running on Raspberry Pi
- Waitress + systemd service configured
- SQLite draft state and backup support working
- Draft Night mock/actual modes working
- Data refresh/status flow in place
- FantasyPros positional rankings integrated
- Historical replay tool moved into `tools/`

---

## Before Draft Night (Highest Priority)
- [ ] Show FantasyPros API usage counter on Settings page
- [ ] Warn when FantasyPros API usage is getting close to limit
- [ ] Finalise data refresh workflow/checklist
- [ ] Add clear “last refreshed” timestamps to Settings/dashboard if needed
- [ ] Final draft-night smoke test
- [ ] Verify mock draft / actual draft / abandon draft flow
- [ ] Review recommendation behaviour for:
  - [ ] early QB timing
  - [ ] late QB2 discipline
  - [ ] TE over-drafting protection
  - [ ] K / DST timing and run detection

---

## Draft Day Checklist
- [ ] Download latest FantasyPros Overall ADP CSV
- [ ] Download latest FantasyPros positional ranking CSVs
- [ ] Refresh FantasyPros API cache
- [ ] Refresh FFC cache
- [ ] Rebuild merged player database
- [ ] Confirm `python data_status.py` shows READY/FRESH
- [ ] Restart service if needed
- [ ] Create Draft Night backup at draft start
- [ ] Use actual draft mode during the live draft

---

## After Draft / In-Season
- [ ] Create “My Team” view
- [ ] Store and display final drafted roster clearly
- [ ] Add manual roster maintenance tools
- [ ] Waiver wire recommendations
- [ ] Free agent recommendations
- [ ] Start / sit recommendations
- [ ] Bench / lineup advice
- [ ] Weekly opponent overview
- [ ] Injury / bye week visibility
- [ ] Trade ideas / trade evaluator (optional)

---

## Post-Season / Refactor
- [ ] Move player database storage from JSON into SQLite
- [ ] Refactor recommendation engine into smaller modules
- [ ] Review project structure (`tools/`, `data/`, services, helpers)
- [ ] Add housekeeping for old backups/logs
- [ ] Add package update / dependency maintenance process
- [ ] Consider hosted deployment instead of Raspberry Pi
- [ ] Build draft-position selection assistant for next season

---

## Ideas / Nice-to-Haves
- [ ] Better draft board / roster UI polish
- [ ] More diagnostics/explanations for recommendations
- [ ] Exportable draft results / summary
- [ ] API call dashboards / counters
- [ ] Multiple league support
- [ ] Yahoo API integration if access is approved
- [ ] Investigate FantasyPros as fallback data source
