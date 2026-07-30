# Proof brief 1 — source-backed data integrity

Status: ready for Human Gate 1 review; internal only.

## Proposition

CareGist can turn CQC's location-level register into a transparent directory with
deterministic service taxonomy, explicit unit counts and visible freshness,
without inventing a care-quality score.

## Controlled proof

- Demonstrate a dry-run reconciliation against a fixed CQC snapshot fixture.
- Show source publication time, retrieval time, ingestion outcome and row units.
- Replay the same snapshot and prove no duplicate state events.
- Trace one provider organisation to multiple locations and one named group to
  show that the units remain distinct.

## Acceptance evidence

- Migration 038/039; `incremental_update.py`; `api/services/pipeline_health.py`.
- Shared service taxonomy and tests.
- `data-reconciliation.md` counts and provenance.
- No external data export or production import.

## Human Gate 1 decision requested

Approve or reject only this internal fixture-based proof and name a data owner.
Do not approve publication, customer delivery, outreach or production mutation.

## Residuals

Production source is stale until an authorised import runs. CQC supply has no
warranty. Field-level privacy review remains required before personal-data use.
