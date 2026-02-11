# CODEX_GUIDE.md

## Purpose
Operational guide for future Codex sessions in this repository.

This project fetches Genshin Impact artifact recommendation data from a public Google Sheet, normalizes/expands it, and generates a self-contained HTML artifact evaluator.

## Session-Verified Snapshot
- Repository shape verified in this session:
  - Includes `README.md` (minimal public URL pointer).
  - Includes `.claude/settings.local.json` for local Claude tooling config.
- Recent git history indicates UI-level improvements after initial guide creation:
  - character+role row focus/highlighting interactions were added/improved
  - `docs/index.html` was republished after template/data updates

## Repository Map
- `genshin.py`: End-to-end pipeline script. Fetches sheet data, cleans/transforms records, writes CSV/JSON/HTML outputs, and writes a validation summary.
- `artifact_evaluator_template.html`: App template (CSS + JS) with `ARTIFACT_DATA_PLACEHOLDER` token.
- `docs/index.html`: Published static app page with embedded JSON data (GitHub Pages-style artifact).
- `README.md`: Landing note that links to the deployed web app.
- `output/`: Generated artifacts from `genshin.py`.
  - `output.csv` (pipe-delimited flattened dataset)
  - `artifact_data.json` (optimized UI index)
  - `artifact_evaluator.html` (template + embedded data)
  - `summary.txt` (validation counts and cleanup diagnostics)
- `CLAUDE.md`: Existing project guidance and high-level architecture notes.
- `.env.example`: Requires `GOOGLE_API_KEY`.
- `requirements.txt`: Python deps (pandas + Google API client stack).

## Runtime and Commands
- Environment: Python in local virtualenv.
- Setup:
  - `source .venv/bin/activate`
  - `cp .env.example .env` and set `GOOGLE_API_KEY`
- Run pipeline:
  - `python genshin.py`

## Data Pipeline (From `genshin.py`)
1. Load `GOOGLE_API_KEY` with `python-dotenv`.
2. Query Google Sheets API (`SPREADSHEET_ID = 1gNxZ2xab1J6o1TuNVWMeLOZ7TPOqrsf3SshP5DLvKzI`) across element tabs.
3. Normalize rows:
   - Rename `TRAVELER` rows to elemental traveler names.
   - Trim first 5 header rows per sheet.
   - Remove keyword rows (`4 STAR`, `5 STAR`, `NOTES`, pending portrait, `Last Updated:`).
4. Parse character blocks and keep rows with meaningful role/artifact/main/substat data.
5. Normalize multiline fields and concatenate lines that start with `~=` or `≈`.
6. Clean/canonicalize artifact set names and stat names; expand category pseudo-sets (e.g. `18% ATK set`) into concrete sets.
7. Parse rank prefixes (`N. text`) and build flattened records for each:
   - Character, Role, Preferred Role, Artifact Set, Artifact Set Rank, Slot, Main Stat, Substat, Substat Rank
   - Skip `main stat == substat` combinations.
8. Write `output/output.csv`.
9. Build web JSON indices:
   - `meta`
   - `bySet` (set-centric browse)
   - `byArtifact` (`set|slot|mainStat` evaluate lookup)
10. Inject JSON into template and write `output/artifact_evaluator.html`.
11. Write `output/summary.txt` diagnostics.

## Web App Behavior
UI in template and `docs/index.html` has two workflows:
- `Browse by Set`: set overview, slot/main-stat breakdown, substat highlighting by clicked substat tile.
- `Evaluate Artifact`: choose set/slot/main stat and inspect matching characters + substats.

Interactive state includes:
- `preferredOnly` toggle
- substat rank threshold filter (top N)
- focused substat (browse; highlights compatible character+role rows/chips)
- focused character+role (both browse and evaluate; cross-highlights compatible rows/tags)
- click-through from browse main-stat links into evaluate preselection (`set + slot + main stat`)

## Current Observations
- Script is monolithic and executes at import time (no `main()` guard), which reduces testability/reuse.
- No automated test suite currently present.
- Data cleaning relies on many hardcoded string replacements; maintenance is expected as sheet content evolves.
- `docs/index.html` is not the template: it already includes a large embedded JSON payload.
- `output/summary.txt` currently reports one suspicious role string: `SHIELD SUPPORT  [C4+ REQUIRED]` (brackets not cleaned in role text).
- `artifact_evaluator_template.html` and `docs/index.html` are expected to diverge in hash because docs has embedded data.

## Collaboration Conventions for Future Codex Work
- Treat `artifact_evaluator_template.html` as source-of-truth UI template.
- Regenerate outputs via `python genshin.py` after data-cleaning or UI-data-shape changes.
- If changing JSON schema in `generate_web_json`, update template JS consumers in lockstep.
- Prefer keeping canonicalization rules centralized in `clean_and_split_artifact_set_names` and `clean_and_split_stats`.
- Preserve `output/summary.txt` diagnostics; they are useful for catching sheet drift/unclean values.
- For publish updates, `docs/index.html` should be refreshed from the latest generated evaluator content.

## Likely High-Value Next Refactors
- Wrap pipeline in functions plus `if __name__ == '__main__':` entrypoint.
- Extract cleanup mappings to structured config data (JSON/YAML/Python dict module).
- Add minimal regression tests for parsers/normalizers (`extract_rank`, stat splitting, set expansion).
- Add a lightweight build step to sync `docs/index.html` from `output/artifact_evaluator.html` when publishing.

## User-Value Feature Candidates
The current app answers "who wants this set/main-stat/substat profile?" well. The biggest user-value gains are likely from helping players make keep/salvage/invest decisions faster.

1. Personalized mode (owned roster + prioritized teams)
- User value: filters recommendations to characters the player actually owns/uses.
- Scope idea: localStorage roster picker + "only show owned" toggle.
- Data impact: none required; existing character/role data is sufficient.

2. "Keep or Feed" verdict with explainable scoring
- User value: immediate decision support for newly dropped artifacts.
- Scope idea: score by demand count, set-rank strength, substat-rank strength, and preferred-role weighting; expose short rationale text.
- Data impact: can start with heuristic scoring using existing fields.

3. Roll-quality aware evaluation (current rolls + remaining potential)
- User value: distinguishes "correct stat line" from "actually strong piece."
- Scope idea: user inputs artifact level and substat roll counts/values; app estimates upgrade ceiling and opportunity cost.
- Data impact: needs stat roll tables/constants and small calculator module.

4. Side-by-side comparison (candidate vs equipped artifact)
- User value: simplifies replacement decisions and avoids manual mental math.
- Scope idea: dual evaluate panes with per-character delta highlight.
- Data impact: no schema change required for first iteration.

5. Character-centric query mode
- User value: lets users start from "I am building X" rather than from artifact set.
- Scope idea: new tab/filter for character+role -> recommended sets, slots, main stats, top substats.
- Data impact: derive on client from existing JSON or add `byCharacter` index in build step.

6. Shareable deep links for exact filter state
- User value: easier collaboration and theorycraft discussion.
- Scope idea: encode tab/set/slot/mainStat/toggles/focus into URL query/hash.
- Data impact: none.

7. Search/fuzzy find across sets, characters, and roles
- User value: faster navigation as data size grows.
- Scope idea: quick search bar + keyboard focus.
- Data impact: none.

8. Data freshness + changelog indicator
- User value: user trust; clarifies when recommendations were last updated.
- Scope idea: stamp generated-at timestamp and row counts into JSON `meta`; optional "what changed" summary.
- Data impact: small `meta` extension in generator.

## Suggested Prioritization (User ROI vs Build Effort)
1. Personalized mode
2. Keep/Feed verdict (heuristic, explainable)
3. Shareable deep links
4. Character-centric query mode
5. Roll-quality aware evaluation
