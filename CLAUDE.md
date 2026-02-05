# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project fetches Genshin Impact artifact recommendations from a public Google Spreadsheet, processes the data, and generates a self-contained HTML artifact evaluator tool.

## Commands

```bash
# Activate virtual environment (required before running Python)
source .venv/bin/activate

# Run the main script (fetches data, generates output files)
python genshin.py
```

## Architecture

### Data Flow

1. **genshin.py** fetches character/artifact data from Google Sheets API (spreadsheet ID hardcoded)
2. Parses and normalizes the data (handling multiline fields, canonicalizing names, expanding set categories)
3. Generates three outputs in `output/`:
   - `output.csv` - Pipe-delimited raw data
   - `artifact_data.json` - Optimized JSON for web UI
   - `artifact_evaluator.html` - Self-contained web app (template + embedded JSON)

### HTML Generation

The web evaluator is built by:
1. Reading `artifact_evaluator_template.html` (contains CSS, JS, placeholder for data)
2. Replacing `ARTIFACT_DATA_PLACEHOLDER` with generated JSON
3. Writing complete HTML to `output/artifact_evaluator.html`

### JSON Data Structure

The generated JSON has three main sections:
- `meta`: Lists of all sets, slots, characters, substats, and main stats by slot
- `bySet`: Index by artifact set → characters + slot breakdowns with substats
- `byArtifact`: Index by "set|slot|mainStat" key → characters + substats with characterRoles

Substats include `characterRoles` array (not just character names) to support the compatible substat highlighting feature.

### Web UI Features

Two tabs:
- **Browse by Set**: Shows characters wanting a set, slot breakdown with clickable main stats and substat tiles
- **Evaluate Artifact**: Select set/slot/main stat to see which characters want it and what substats to look for

Interactive highlighting system: clicking substats or character chips highlights compatible items across the UI.

## Environment Setup

Requires `.env` file with `GOOGLE_API_KEY` (see `.env.example`).
