# Season schedule and matchup records

Settings contains a season schedule for Weeks 1–17. Names from Yahoo ownership
data are suggestions; unknown opponents can be typed and future weeks left blank.
Weekly and History link to the appropriate matchup. The matchup page can also
select any week directly.

Each matchup stores its opponent, original projected totals, actual totals,
starting slots and recorded game states. These entries are independent of the
current roster tables and Player List imports. They do not change the assistant's
recommended lineup or submit anything to Yahoo.

Enter actual scores only when known. Blank means unknown; zero and negative
scores are valid. Mark a game locked manually when confirming its starter on
Yahoo. This is a record of the observed state, not automatic kickoff detection.
Final matchups require nine starters on each side, actual scores for all players,
and team totals matching the player sums within 0.05 points.

Final records and the identity/projection of locked starters are protected.
Deliberate corrections use the checkbox in the matchup editor. Previous payloads
are retained in `matchup_revisions`; other imports do not overwrite them.

## One-time structured import

Settings → Season schedule → Import saved matchup records accepts JSON files
up to 256 KB. This importer accepts transcribed records, not images or HTML.
Screenshot data prepared for Daniel is delivered separately, outside Git.

The format is an object with `season: 2026` and a `matchups` array (1–17 entries).
Each entry has:

- `week`, `opponent`, `status` (`planned`, `live`, `final`) and optional `source`.
- `own_projection`, `opponent_projection`, `own_actual`, `opponent_actual`:
  numbers or null.
- `own_lineup` and `opponent_lineup`: arrays of starting rows with `slot`, `name`,
  `position`, `team`, `projection`, `actual` and `state`.

Slots: QB, RB1, RB2, WR1, WR2, TE, FLEX, K, DST. FLEX positions must be RB/WR/TE;
other positions must match the slot. States: `not_started`, `locked`, `final`.
Final matchups set every row state to final. Empty scheduled matchups can omit
lineup arrays and scores. Projection totals are stored as reported, rather than
silently recomputed; this accommodates provider rounding.

The complete import is atomic. Duplicate weeks or invalid rows reject the batch.
Repeating the identical import is safe; differing final records must be corrected
explicitly in the editor.

Retrospective screenshots can show original Yahoo projections, but their import
time is not the time those predictions were issued. Do not treat these records
as frozen, timestamped assistant recommendations for model evaluation.

Future work: HTML matchup extraction, automatic player-ID reconciliation,
automatic game-lock tracking and genuinely pre-kickoff recommendation snapshots.
