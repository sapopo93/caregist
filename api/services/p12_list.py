"""P12 list: medium care homes whose Well-led rating is below Good.

Care homes with 11-49 registered places whose resolved *current* Well-led
rating (api/services/rating_resolver.py, domain ``Well-led``) is Requires
improvement or Inadequate, with publication dates and both sources' values.

Wording is factual: each row states what CQC has published. Nothing here
predicts anything about an individual home. Inherited and unresolved Well-led
ratings are excluded from the list and counted in the reconciliation, so the
list plus every exclusion always equals the SQL base population.

Pure: callers supply the base rows (api/queries/p12_list.py) and the evidence.
Generation refuses unless ``p12_list_enabled``.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from api.services.rating_resolver import (
    SOURCE_API,
    SOURCE_FILE,
    RatingEvidence,
    ResolvedRating,
    canonical_rating,
    resolve_rating,
)

DOMAIN = "Well-led"
BELOW_GOOD = ("Requires improvement", "Inadequate")
STATEMENT = (
    "This list reports CQC's published Well-led ratings for care homes with 11-49 registered "
    "places. It makes no prediction or statement about any individual home's current quality, "
    "finances or intentions. CareGist is independent of CQC. Contains public sector information "
    "licensed under the Open Government Licence v3.0."
)


class P12Disabled(RuntimeError):
    pass


def ensure_enabled() -> None:
    from api.config import settings

    if not settings.p12_list_enabled:
        raise P12Disabled("P12 list is disabled (P12_LIST_ENABLED=false)")


@dataclass(frozen=True)
class FileDomainRating:
    rating: str
    publication_date: date | None
    inherited: bool | None


@dataclass(frozen=True)
class P12Result:
    region: str
    rows: tuple[dict[str, Any], ...]
    base_count: int
    reconciliation: dict[str, int] = field(default_factory=dict)


def _bucket(r: ResolvedRating) -> str:
    if r.status == "current":
        return "listed" if r.value in BELOW_GOOD else f"current_{r.value.lower().replace(' ', '_')}"
    return r.status


def build_p12_list(
    *,
    region: str,
    base_rows: Iterable[dict[str, Any]],
    api_well_led: Mapping[str, tuple[str | None, date | None]],
    file_well_led: Mapping[str, FileDomainRating],
    file_edition_date: date | None,
    file_sha256: str | None,
) -> P12Result:
    ensure_enabled()
    rows, buckets = [], Counter()
    base = list(base_rows)
    for row in base:
        lid = row["id"]
        api_raw, api_date = api_well_led.get(lid, (None, None))
        evidence = [RatingEvidence(source=SOURCE_API, value=canonical_rating(api_raw),
                                   publication_date=api_date, raw_value=api_raw)]
        f = file_well_led.get(lid)
        if f is not None:
            evidence.append(RatingEvidence(
                source=SOURCE_FILE, value=canonical_rating(f.rating), publication_date=f.publication_date,
                inherited_flag=f.inherited, source_sha256=file_sha256, edition_date=file_edition_date,
                raw_value=f.rating,
            ))
        resolved = resolve_rating(evidence, registration_date=row.get("registration_date"), domain=DOMAIN)
        bucket = _bucket(resolved)
        buckets[bucket] += 1
        if bucket != "listed":
            continue
        d = resolved.to_dict()
        rows.append({
            "region": row.get("region") or "",
            "local_authority": row.get("local_authority") or "",
            "cqc_location_id": lid,
            "cqc_provider_id": row.get("provider_id") or "",
            "care_home": row.get("name") or "",
            "postcode": row.get("postcode") or "",
            "registered_places": row.get("number_of_beds"),
            "well_led_rating": d["value"],
            "well_led_published": d["publication_date"] or "",
            "rating_source": d["source"],
            "api_well_led": d["api_value"] or "",
            "api_well_led_date": d["api_publication_date"] or "",
            "file_well_led": d["file_value"] or "",
            "file_well_led_date": d["file_publication_date"] or "",
            "file_sha256": d["file_sha256"] or "",
            "file_edition_date": d["file_edition_date"] or "",
            "cqc_url": f"https://www.cqc.org.uk/location/{lid}",
        })
    rows.sort(key=lambda r: (r["local_authority"], r["care_home"], r["cqc_location_id"]))
    reconciliation = dict(sorted(buckets.items()))
    if sum(reconciliation.values()) != len(base):
        raise RuntimeError("P12 reconciliation failed: buckets do not sum to the base population")
    return P12Result(region=region, rows=tuple(rows), base_count=len(base), reconciliation=reconciliation)


def p12_to_csv(result: P12Result) -> str:
    buf = io.StringIO()
    fields = list(result.rows[0].keys()) if result.rows else [
        "region", "local_authority", "cqc_location_id", "cqc_provider_id", "care_home", "postcode",
        "registered_places", "well_led_rating", "well_led_published", "rating_source", "api_well_led",
        "api_well_led_date", "file_well_led", "file_well_led_date", "file_sha256", "file_edition_date", "cqc_url",
    ]
    w = csv.DictWriter(buf, fieldnames=[*fields, "statement"])
    w.writeheader()
    for row in result.rows:
        w.writerow({**row, "statement": STATEMENT})
    return buf.getvalue()
