#!/usr/bin/env python3
"""Build and verify the Birmingham and Solihull domiciliary-care sample."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / "directory_providers.csv"
DATASET = HERE / "bsol-domiciliary-dataset.csv"
SHORTLIST = HERE / "shortlist-25-50.csv"
OBSERVED_ON = "2026-03-28"
GENERATED_ON = "2026-09-08"

DATASET_FIELDS = [
    "id", "provider_id", "name", "slug", "type", "status", "registration_date",
    "town", "county", "postcode", "region", "overall_rating", "service_types",
    "data_completeness_tier", "phone", "email", "website", "latitude", "longitude",
    "local_authority", "specialisms", "regulated_activities", "number_of_beds",
    "ownership_type", "last_inspection_date", "inspection_report_url",
    "service_type_group", "data_observation_date", "evidence_source",
]


def safe_cell(value: str) -> str:
    """Neutralise spreadsheet formulas while preserving source text."""
    return "'" + value if value.startswith(("=", "+", "-", "@")) else value


def source_rows() -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            services = set(filter(None, row["service_types"].split("|")))
            if (
                row["local_authority"] in {"Birmingham", "Solihull"}
                and "Homecare Agencies" in services
                and row["status"] == "ACTIVE"
            ):
                row["_source_line"] = str(line_number)
                selected.append(row)
    return selected


def write_dataset(rows: list[dict[str, str]]) -> None:
    with DATASET.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATASET_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item["local_authority"], item["name"], item["id"])):
            output = {key: safe_cell(row.get(key, "")) for key in DATASET_FIELDS}
            output["data_completeness_tier"] = safe_cell(row.get("quality_tier", ""))
            output["service_type_group"] = "Domiciliary care (Homecare Agencies)"
            output["data_observation_date"] = OBSERVED_ON
            output["evidence_source"] = f"directory_providers.csv:{row['_source_line']}"
            writer.writerow(output)


def ranked_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    territory_locations = Counter(row["provider_id"] for row in rows)
    return sorted(
        rows,
        key=lambda row: (
            row["registration_date"],
            territory_locations[row["provider_id"]],
            row["name"],
            row["id"],
        ),
        reverse=True,
    )[:40]


def write_shortlist(rows: list[dict[str, str]]) -> None:
    territory_locations = Counter(row["provider_id"] for row in rows)
    fields = ["rank", "provider_name", "local_authority", "why_this_account", "evidence_source"]
    with SHORTLIST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, row in enumerate(ranked_rows(rows), start=1):
            scale = territory_locations[row["provider_id"]]
            reason = (
                f"Repository snapshot records this active homecare location with registration date "
                f"{row['registration_date']}."
            )
            if scale > 1:
                reason += f" Its linked provider ID has {scale} active homecare locations in this territory snapshot."
            reason += " Review current staffing and supplier relevance before contact; no staffing need is inferred."
            writer.writerow({
                "rank": rank,
                "provider_name": safe_cell(row["name"]),
                "local_authority": row["local_authority"],
                "why_this_account": reason,
                "evidence_source": f"directory_providers.csv:{row['_source_line']}",
            })


def write_readme(rows: list[dict[str, str]]) -> None:
    authority = Counter(row["local_authority"] for row in rows)
    README = HERE / "README.md"
    README.write_text(f"""# Birmingham and Solihull domiciliary care sample

**SAMPLE — NOT VERIFIED. Built from repository snapshot data for pre-test use only. Not for client delivery until the CQC week-1 data path gate passes.**

Generated on {GENERATED_ON}. The underlying directory rows carry a common last-updated timestamp of 2026-03-28 01:04:17, recorded here as the observation date {OBSERVED_ON}.

## What is included

- `bsol-domiciliary-dataset.csv`: {len(rows)} active location records classified with the source service type `Homecare Agencies`, comprising {authority['Birmingham']} in Birmingham and {authority['Solihull']} in Solihull.
- `shortlist-25-50.csv`: 40 locations ranked first by registration date, then by the number of active homecare locations sharing the same provider ID in this territory snapshot. Every reason states its source row and avoids inferring a vacancy or staffing need.
- `executive-brief.md`: a recruitment and staffing buyer brief based on the same rows.
- `build_sample.py` and `build.log`: deterministic build and verification route.
- `pre-test-kit/`: drafts and templates for Henry. Nothing in the kit sends or creates a live record.

## Provenance

Primary source: `/Users/user/CareGist/directory_providers.csv`, itself labelled `CQC API v1`. Rows qualify only when `local_authority` is Birmingham or Solihull, `status` is `ACTIVE`, and the pipe-separated `service_types` field contains the exact label `Homecare Agencies`.

`cqc_data_quality_report.md` was reviewed for snapshot limitations but does not supply rows to these CSVs. `_providers_detail.ndjson`, `_providers_list.ndjson`, and `provider_groups.csv` were inspected but were not needed to support the exported row-level claims.

## Known gaps

- This is a repository snapshot, not a current CQC refresh. It has not passed the governed week-1 data-path gate.
- The snapshot contains current ratings but no rating-change history, so the sample makes no rating-movement claim.
- It does not contain a verified closure-event series. Only active rows are included.
- A shared provider ID supports a location-count observation, not a claim of recent expansion, common ownership beyond the identifier, staffing demand, vacancy, budget, or buying intent.
- The source does not distinguish domiciliary care from every other activity at a mixed-service location. Inclusion means the location carries `Homecare Agencies` among its service types.
- Contact fields are incomplete. Blank phone, email, website, rating, inspection, or address fields remain blank. Nothing was enriched or invented.
- Local-authority labels and service classification are accepted as stored in the repository and have not been rechecked against live CQC records.

## Rebuild and verify

From the repository root:

```bash
python3 artifacts/launch-samples/bsol-domiciliary-sample/build_sample.py
python3 artifacts/launch-samples/bsol-domiciliary-sample/build_sample.py --verify
```

The verifier checks every exported dataset row and shortlist evidence pointer against the cited source line, then checks shortlist ranks, qualification rules, observation dates, and stated aggregate location counts.
""", encoding="utf-8")


def write_brief(rows: list[dict[str, str]]) -> None:
    authority = Counter(row["local_authority"] for row in rows)
    combos = Counter(row["service_types"] for row in rows)
    ratings = Counter(row["overall_rating"] or "Blank" for row in rows)
    providers = defaultdict(list)
    for row in rows:
        providers[row["provider_id"]].append(row)
    multi = sorted(
        ((pid, items) for pid, items in providers.items() if len(items) > 1),
        key=lambda item: (-len(item[1]), item[0]),
    )
    newest = ranked_rows(rows)[:10]
    top_combos = "\n".join(f"- {name}: {count} locations" for name, count in combos.most_common(6))
    rating_lines = "\n".join(f"- {name}: {count}" for name, count in ratings.most_common())
    newest_lines = "\n".join(
        f"- {row['name']} ({row['local_authority']}), registration date {row['registration_date']}, source row {row['_source_line']}"
        for row in newest
    )
    group_lines = "\n".join(
        f"- Provider ID `{pid}`: {len(items)} active homecare locations in territory; examples: "
        + ", ".join(item["name"] for item in sorted(items, key=lambda x: x["name"])[:3])
        for pid, items in multi[:10]
    ) or "- No provider ID appears against more than one qualifying location."
    (HERE / "executive-brief.md").write_text(f"""# Birmingham and Solihull domiciliary care opportunity brief

## Purpose and status

This sample helps a recruitment or staffing sales team decide which domiciliary-care accounts in Birmingham and Solihull deserve manual review first. It is a prioritisation aid, not a statement that any provider has a vacancy, staffing shortage, budget, or intent to buy.

**SAMPLE — NOT VERIFIED. Built from repository snapshot data for pre-test use only. Not for client delivery until the CQC week-1 data path gate passes.**

The snapshot was observed on {OBSERVED_ON}. All counts below come from {len(rows)} active repository rows whose local authority is Birmingham or Solihull and whose service types include `Homecare Agencies`.

## The decision in this territory

The main finding is concentration. Birmingham accounts for {authority['Birmingham']} of {len(rows)} qualifying locations ({authority['Birmingham']/len(rows):.1%}); Solihull accounts for {authority['Solihull']} ({authority['Solihull']/len(rows):.1%}). A sales team covering both authorities should not split prospecting time equally. The stored footprint supports a larger Birmingham review queue, while Solihull remains a smaller list that a named owner could work in full.

The shortlist does not rank accounts by contact-data volume. It ranks the 40 most recently registered qualifying locations in the repository snapshot, then uses the count of matching territory locations under the same provider ID as a secondary signal. This gives the team a clear starting queue and an explicit reason for every selection. Before outreach, a person must confirm the record against the current CQC publication and qualify whether the account fits the offer.

## Territory size and market structure

The repository snapshot contains:

- Birmingham: {authority['Birmingham']} active locations carrying the `Homecare Agencies` label.
- Solihull: {authority['Solihull']} active locations carrying the `Homecare Agencies` label.
- Combined: {len(rows)} qualifying active locations linked to {len(providers)} distinct provider IDs.
- Provider IDs appearing against more than one qualifying territory location: {len(multi)}.

Service labels overlap because a location can carry more than one source category. The leading combinations are:

{top_combos}

For a staffing buyer, these combinations matter at the qualification stage. A location recorded only as `Homecare Agencies` presents a different service mix from one also recorded as supported living, supported housing, nursing, or community services. The source does not show workforce demand, so the sales team should use service mix to prepare a relevant question, not to assert a need.

The current-rating field is a snapshot attribute, not movement history:

{rating_lines}

These ratings should not drive a claim that a provider is improving or declining. A current rating is useful only as background for manual account research unless a separate, observation-dated comparison proves a change.

## Observation-dated account movements

The repository supports registration dates, not a complete event history. The ten highest-ranked rows in this sample are:

{newest_lines}

These dates identify accounts for current verification. They do not prove that a registration remained unchanged after {OBSERVED_ON}, that the business is expanding, or that it needs recruitment support. The sensible action is to verify the live record, inspect the provider's own public material, then ask a discovery question tied to the buyer's service.

The snapshot also shows repeated provider IDs across qualifying territory locations. The largest repeated identifiers are:

{group_lines}

This is a scale indicator within the stored territory extract. It is not evidence of a corporate group acquisition or recent expansion. The identifier gives a recruitment team a reason to coordinate account ownership and avoid separate representatives approaching related locations without checking the relationship.

## Recommended recruitment sales approach

Start with the 40-row shortlist. Assign one owner per provider ID, then verify each shortlisted location against the current CQC record before any contact. Record the verification date and remove any account whose status, authority, or service type no longer matches.

For the first conversation, lead with the buyer's job rather than the CQC row. Ask how the organisation currently covers shifts or grows its workforce, if that question is appropriate to the buyer's lawful and compliant sales process. Do not say the registration date means the provider is hiring. A safe internal prompt is: "This account appears in our territory shortlist because the repository snapshot records an active homecare location with registration date X. What current public evidence would make it relevant to our staffing offer?"

Separate account priority from contact readiness. A high-ranked record with no verified decision-maker is a research task. It is not permission to send. Entity type, contact route, suppression status, and any TPS or CTPS checks remain separate compliance steps. This sample contains provider contact fields only where they already exist in the repository. Blank fields remain blank.

After the first ten verified accounts, review what changed. Record which accounts were relevant, which reason led to a conversation, and which were rejected. Preserve objections in the buyer's words. If registration recency does not change sales behaviour, alter the ranking rule only after documenting that evidence. Do not silently replace it with an unsupported score.

## What the data does not support

This snapshot does not support claims about rating movement, closures, new vacancies, manager absence, distress, purchasing budget, recent group expansion, or complete market coverage. It does not prove a causal link between a registration date and recruitment demand. Those gaps are material because the approved product promise includes notable movements only where evidence supports them.

The sample should therefore be tested as a decision aid: does a ranked, traceable review queue change where a recruitment sales team spends time? The pre-test should not ask buyers to accept unverified movement language. If buyers need rating-history or closure evidence before they would pay, record that as a product requirement and keep the sample out of client delivery until the data path supplies it.

## Sources, licence, and independence

Source rows: `/Users/user/CareGist/directory_providers.csv`, labelled `CQC API v1` and carrying a common last-updated timestamp of 2026-03-28 01:04:17. The dataset and shortlist retain a source-line pointer for every exported row.

CQC information is reused under the Open Government Licence v3.0. CareGist is independent and is not affiliated with or endorsed by the Care Quality Commission.

Observation date: {OBSERVED_ON}. Generated: {GENERATED_ON}. This sample remains unverified and is not for client delivery until the governed CQC week-1 data-path gate passes.
""", encoding="utf-8")


def verify() -> None:
    source_by_line: dict[str, dict[str, str]] = {}
    qualified = source_rows()
    for row in qualified:
        source_by_line[row["_source_line"]] = row
    territory_locations = Counter(row["provider_id"] for row in qualified)

    with DATASET.open(newline="", encoding="utf-8") as handle:
        dataset_rows = list(csv.DictReader(handle))
    assert len(dataset_rows) == len(qualified) == 371
    for row in dataset_rows:
        line = row["evidence_source"].split(":", 1)[1]
        source = source_by_line[line]
        assert row["id"] == source["id"]
        assert row["name"].lstrip("'") == source["name"]
        assert row["local_authority"] == source["local_authority"]
        assert "Homecare Agencies" in source["service_types"].split("|")
        assert row["data_observation_date"] == OBSERVED_ON

    with SHORTLIST.open(newline="", encoding="utf-8") as handle:
        shortlist = list(csv.DictReader(handle))
    assert 25 <= len(shortlist) <= 50
    assert [int(row["rank"]) for row in shortlist] == list(range(1, len(shortlist) + 1))
    expected = ranked_rows(qualified)
    for row, source in zip(shortlist, expected, strict=True):
        line = row["evidence_source"].split(":", 1)[1]
        assert line == source["_source_line"]
        assert row["provider_name"].lstrip("'") == source["name"]
        assert row["local_authority"] == source["local_authority"]
        scale = territory_locations[source["provider_id"]]
        if scale > 1:
            assert f"has {scale} active homecare locations" in row["why_this_account"]
        assert "no staffing need is inferred" in row["why_this_account"]
    print(f"VERIFIED: {len(dataset_rows)} dataset rows and {len(shortlist)} shortlist rows trace to directory_providers.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify()
        return
    rows = source_rows()
    write_dataset(rows)
    write_shortlist(rows)
    write_readme(rows)
    write_brief(rows)
    print(f"BUILT: {len(rows)} dataset rows and {len(ranked_rows(rows))} shortlist rows")


if __name__ == "__main__":
    main()
