# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Rules

- Check `tools/` and `workflows/` for existing scripts and SOPs before building anything new.
- Don't create or overwrite workflow files (`workflows/*.md`) without asking first.
- If a script uses paid API calls or credits, confirm with the user before re-running it.
- When you fix a bug or discover a constraint (rate limits, timing quirks), update the relevant workflow with what you learned.
- Credentials and API keys live in `.env` — never store secrets anywhere else.
- Final deliverables go to cloud services (Google Sheets, Slides, etc.). Local files are for processing only. Everything in `.tmp/` is disposable.

## File Structure

```
tools/          # Python scripts for execution (API calls, data transforms, file ops)
workflows/      # Markdown SOPs defining objectives, inputs, tools, outputs, edge cases
.tmp/           # Temporary/intermediate files, regenerated as needed
.env            # API keys and environment variables
credentials.json, token.json  # Google OAuth (gitignored)
```

## CQC Directory Pipeline

Python ETL pipeline that extracts UK care provider data from the CQC (Care Quality Commission) public API, cleans/normalizes it, runs quality audits, and produces directory-ready outputs.

### Pipeline Stages

The full pipeline runs via `run_enriched_pipeline.sh` and executes in order:

1. **`extract_cqc.py`** — Pulls all providers and locations from `api.service.cqc.org.uk/public/v1`. Paginates list endpoints, fetches detail endpoints for enrichment. Resumable via `checkpoint.json`; logs failed IDs to `failed_ids.txt`. Caches provider details in `_provider_cache.sqlite`. Outputs `raw_combined.csv`.

2. **`clean_cqc.py`** — Normalizes names, phones (UK format via `phonenumbers`), postcodes, websites, addresses, dates, coordinates, ratings, and taxonomy fields. Deduplicates on `locationId`. Splits into `cleaned_cqc.csv` (active), `inactive_providers.csv`, and `duplicates_removed.csv`.

3. **`quality_audit.py`** — Scores each record (0–100) across weighted fields and assigns data completeness tiers (NOT CQC ratings): COMPLETE ≥85, GOOD ≥60, PARTIAL ≥40, SPARSE <40. Writes scores back into `cleaned_cqc.csv`. Produces `quality_report.json` and `quality_summary.txt`.

4. **`prepare_directory.py`** — Transforms cleaned data into directory-ready schema with slugs, meta titles/descriptions, CQC inspection URLs, and optional geocoding via postcodes.io. Outputs `directory_providers.csv`, `.json`, `.sql`, and `import_to_db.sql` (PostgreSQL + MySQL DDL).

### Shared Module

`cqc_common.py` — Shared utilities: `normalize_whitespace`, `parse_any_date`, `ensure_list`, `flatten_json`, `deep_get`, `first_non_empty`, `to_float`, `as_json`.

### Running the Pipeline

```bash
# Full pipeline
./run_enriched_pipeline.sh

# Individual stages
python3 extract_cqc.py --sleep 0.02
python3 clean_cqc.py
python3 quality_audit.py
python3 prepare_directory.py
python3 prepare_directory.py --enable-geocode  # backfill missing coords via postcodes.io
```

All scripts accept `--help`. Key extract flags: `--sleep` (inter-request delay), `--checkpoint-every`, `--workers` (parallel detail fetches).

### Dependencies

```bash
pip install -r requirements.txt
```

Core: `requests`, `pandas`, `numpy`, `tqdm`, `python-slugify`, `phonenumbers`, `validators`. The pipeline gracefully degrades if `phonenumbers` or `validators` are missing.

### Data Flow

```
CQC API → raw_combined.csv → cleaned_cqc.csv → directory_providers.{csv,json,sql}
                               ├── inactive_providers.csv
                               ├── duplicates_removed.csv
                               └── quality_report.json / quality_summary.txt
```

Intermediate files prefixed with `_` (e.g., `_providers_list.ndjson`, `_provider_cache.sqlite`) are regenerable pipeline artifacts.

### Key Conventions

- CQC API key is passed via `CQC_API_KEY` environment variable
- UK-specific validation: postcodes match `^[A-Z]{1,2}[0-9][0-9A-Z]?\s[0-9][A-Z]{2}$`, coordinates within 49–61°N / 8°W–2°E
- Taxonomy fields (service types, specialisms, regulated activities) are pipe-delimited (`|`)
- `locationId` is the primary key for deduplication and record identity
- The extract stage is resumable via `checkpoint.json`
