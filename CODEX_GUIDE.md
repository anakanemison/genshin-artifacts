# CODEX_GUIDE.md

## Purpose
Operational guide for future Codex sessions in this repository.

This project fetches Genshin Impact artifact recommendation data from a public Google Sheet, normalizes/expands it, and generates a self-contained HTML artifact evaluator.

## Repository Map
- `genshin.py`: End-to-end pipeline script. Fetches sheet data, cleans/transforms records, writes CSV/JSON/HTML outputs, and writes a validation summary.
- `artifact_evaluator_template.html`: App template (CSS + JS) with `ARTIFACT_DATA_PLACEHOLDER` token.
- `docs/index.html`: Published static app page with embedded JSON data (GitHub Pages-style artifact).
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
- focused substat (browse)
- focused character+role (evaluate)

## Current Observations
- Script is monolithic and executes at import time (no `main()` guard), which reduces testability/reuse.
- No automated test suite currently present.
- Data cleaning relies on many hardcoded string replacements; maintenance is expected as sheet content evolves.
- `docs/index.html` is not the template: it already includes a large embedded JSON payload.
- `output/summary.txt` currently reports one suspicious role string: `SHIELD SUPPORT  [C4+ REQUIRED]` (brackets not cleaned in role text).

## Collaboration Conventions for Future Codex Work
- Treat `artifact_evaluator_template.html` as source-of-truth UI template.
- Regenerate outputs via `python genshin.py` after data-cleaning or UI-data-shape changes.
- If changing JSON schema in `generate_web_json`, update template JS consumers in lockstep.
- Prefer keeping canonicalization rules centralized in `clean_and_split_artifact_set_names` and `clean_and_split_stats`.
- Preserve `output/summary.txt` diagnostics; they are useful for catching sheet drift/unclean values.

## Likely High-Value Next Refactors
- Wrap pipeline in functions plus `if __name__ == '__main__':` entrypoint.
- Extract cleanup mappings to structured config data (JSON/YAML/Python dict module).
- Add minimal regression tests for parsers/normalizers (`extract_rank`, stat splitting, set expansion).
- Add a lightweight build step to sync `docs/index.html` from `output/artifact_evaluator.html` when publishing.
