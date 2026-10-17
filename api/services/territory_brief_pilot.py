"""Buyer-specific pilot layer over the Territory Opportunity Brief.

Operator-only. The paid self-serve path never calls this module. It takes a
generated :class:`~api.services.territory_brief.TerritoryBrief`, applies a
buyer's ideal-customer profile and CRM suppression list, and attaches a
structured qualification record to each remaining account.

Each qualification factor states what the CQC register shows (``Verified`` or
``Not met``) and what it cannot show (``Unknown`` or ``Not researched``). Nothing
is inferred about systems, budgets, buying intent or decision-makers.

Only the ``software`` segment (care software vendors) is supported for now.
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Literal

from api.services.territory_brief import (
    CQC_PROFILE_URL,
    MAX_SHORTLIST,
    OGL_ATTRIBUTION,
    RankedOrganisation,
    ScopeError,
    TerritoryBrief,
    _SOFTWARE_QUESTION,
)
from tools.generate_radar_territory_sample import _load_ndjson, _parse_date

MIN_PILOT_TARGET = 10
MAX_PILOT_TARGET = 30
DEFAULT_PILOT_TARGET = 20

#: Exclusion reasons, in the order they are applied and reported.
EXCLUSION_REASONS = ("excluded_provider", "crm_existing", "service_type", "group_size", "beds")

Status = Literal["Verified", "Not met", "Unknown", "Not researched"]

_CQC_SOURCE = "CQC register"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BuyerProfile:
    """A buyer's ideal-customer profile. Bounds are inclusive; ``None`` is unbounded."""

    segment: Literal["software"] = "software"
    group_size_min: int | None = None
    group_size_max: int | None = None
    beds_min: int | None = None
    beds_max: int | None = None
    include_service_types: tuple[str, ...] = ()
    exclude_service_types: tuple[str, ...] = ()
    exclude_provider_ids: tuple[str, ...] = ()
    pilot_target: int = DEFAULT_PILOT_TARGET

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("include_service_types", "exclude_service_types", "exclude_provider_ids"):
            data[key] = list(data[key])
        return data


def validate_profile(profile: BuyerProfile) -> BuyerProfile:
    """Raise :class:`ScopeError` for a profile that cannot be applied."""
    if profile.segment != "software":
        raise ScopeError(f"unsupported buyer segment: {profile.segment!r}")
    if not MIN_PILOT_TARGET <= profile.pilot_target <= MAX_PILOT_TARGET:
        raise ScopeError(
            f"pilot_target must be between {MIN_PILOT_TARGET} and {MAX_PILOT_TARGET}"
        )
    for label, low, high in (
        ("group_size", profile.group_size_min, profile.group_size_max),
        ("beds", profile.beds_min, profile.beds_max),
    ):
        if (low is not None and low < 0) or (high is not None and high < 0):
            raise ScopeError(f"{label} bounds must not be negative")
        if low is not None and high is not None and low > high:
            raise ScopeError(f"{label}_min is greater than {label}_max")
    include = {t.casefold() for t in profile.include_service_types}
    if include & {t.casefold() for t in profile.exclude_service_types}:
        raise ScopeError("a service type cannot be both included and excluded")
    return profile


_SUFFIX = re.compile(r"\b(limited|ltd\.?|plc|llp)$")


def normalise_org_name(name: str) -> str:
    """Exact-match key for organisation names: casefold, collapse whitespace, drop legal suffix."""
    key = " ".join(str(name or "").casefold().split())
    key = _SUFFIX.sub("", key).strip(" .,")
    return " ".join(key.split())


@dataclass(frozen=True)
class Suppression:
    """Accounts the buyer already has. Holds identifiers and names only."""

    provider_ids: frozenset[str] = frozenset()
    location_ids: frozenset[str] = frozenset()
    organisation_names: frozenset[str] = frozenset()

    def matches(self, org: RankedOrganisation) -> bool:
        return (
            org.provider_id in self.provider_ids
            or org.location_id in self.location_ids
            or normalise_org_name(org.organisation_name) in self.organisation_names
        )


_SUPPRESSION_COLUMNS = {
    "cqc_provider_id": "provider_ids",
    "cqc_location_id": "location_ids",
    "organisation": "organisation_names",
}


def load_crm_suppression(path: str | Path) -> Suppression:
    """Read a buyer CRM export, keeping only identifier and organisation-name columns.

    Every other column (contacts, emails, notes) is ignored and never held, so
    buyer personal data cannot reach any output. A file without any recognised
    column fails loudly instead of silently suppressing nothing.
    """
    collected: dict[str, set[str]] = {attr: set() for attr in _SUPPRESSION_COLUMNS.values()}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None) or []
        positions = {
            index: _SUPPRESSION_COLUMNS[name.strip().casefold()]
            for index, name in enumerate(header)
            if name.strip().casefold() in _SUPPRESSION_COLUMNS
        }
        if not positions:
            raise ScopeError(
                "CRM suppression file needs at least one of the columns: "
                + ", ".join(_SUPPRESSION_COLUMNS)
            )
        for row in reader:
            for index, attr in positions.items():
                if index >= len(row):
                    continue
                value = row[index].strip()
                if attr == "organisation_names":
                    value = normalise_org_name(value)
                if value:
                    collected[attr].add(value)
    return Suppression(**{attr: frozenset(values) for attr, values in collected.items()})


# --------------------------------------------------------------------------- #
# CQC-sourced facts
# --------------------------------------------------------------------------- #


def _registered(row: dict[str, Any]) -> bool:
    return str(row.get("registrationStatus") or "").strip().casefold() == "registered"


def provider_group_sizes(location_rows: Iterable[dict[str, Any]]) -> Counter[str]:
    """Registered CQC locations per provider, counted across the whole snapshot."""
    sizes: Counter[str] = Counter()
    for row in location_rows:
        provider_id = str(row.get("providerId") or "").strip()
        if provider_id and _registered(row):
            sizes[provider_id] += 1
    return sizes


def provider_registrations_in_window(
    location_rows: Iterable[dict[str, Any]], *, window_start: date, window_end: date
) -> Counter[str]:
    """Registered, non-dormant locations per provider with a CQC registration date in the window."""
    counts: Counter[str] = Counter()
    for row in location_rows:
        provider_id = str(row.get("providerId") or "").strip()
        reg_date = _parse_date(row.get("registrationDate"))
        dormant = str(row.get("dormancy") or "").strip().upper().startswith("Y")
        if (
            provider_id
            and _registered(row)
            and not dormant
            and reg_date is not None
            and window_start <= reg_date <= window_end
        ):
            counts[provider_id] += 1
    return counts


# --------------------------------------------------------------------------- #
# Output types
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class QualificationFactor:
    name: str
    status: Status
    finding: str
    source: str


@dataclass(frozen=True)
class PilotAccount:
    rank: int
    base_rank: int
    organisation: RankedOrganisation
    registered_locations: int
    qualification: tuple[QualificationFactor, ...]
    next_step: str

    def fit_summary(self) -> str:
        return "; ".join(
            f"{f.name}: {f.finding}" for f in self.qualification if f.status in ("Verified", "Not met")
        )

    def unknowns(self) -> str:
        return "; ".join(
            f"{f.name} ({f.status.lower()})"
            for f in self.qualification
            if f.status in ("Unknown", "Not researched")
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "base_rank": self.base_rank,
            "registered_locations": self.registered_locations,
            "organisation": self.organisation.to_json(),
            "qualification": [asdict(f) for f in self.qualification],
            "next_step": self.next_step,
        }


@dataclass(frozen=True)
class PilotBrief:
    base: TerritoryBrief
    profile: BuyerProfile
    accounts: tuple[PilotAccount, ...]
    pool_size: int
    exclusions: dict[str, int]
    shortfall_notice: str | None
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        return {
            "scope": self.base.scope.to_json(),
            "purchase_context": self.base.purchase_context.to_json(),
            "source_edition_date": self.base.as_of_date.isoformat(),
            "window_start": self.base.window_start.isoformat(),
            "window_end": self.base.window_end.isoformat(),
            "profile": self.profile.to_json(),
            "pool_size": self.pool_size,
            "exclusions": dict(self.exclusions),
            "shortfall_notice": self.shortfall_notice,
            "accounts": [account.to_json() for account in self.accounts],
            "limitations": list(self.limitations),
            "licence": OGL_ATTRIBUTION,
        }


# --------------------------------------------------------------------------- #
# Filtering + qualification
# --------------------------------------------------------------------------- #


def _within(value: int | None, low: int | None, high: int | None) -> bool:
    if low is None and high is None:
        return True
    if value is None:
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _bounds_phrase(low: int | None, high: int | None) -> str:
    if low is not None and high is not None:
        return f"{low}-{high}"
    if low is not None:
        return f"{low}+"
    if high is not None:
        return f"up to {high}"
    return "any"


def _exclusion_reason(
    org: RankedOrganisation,
    profile: BuyerProfile,
    suppression: Suppression | None,
    group_size: int,
) -> str | None:
    if org.provider_id in set(profile.exclude_provider_ids):
        return "excluded_provider"
    if suppression is not None and suppression.matches(org):
        return "crm_existing"
    services = {s.casefold() for s in org.service_types}
    if profile.include_service_types and not services & {
        s.casefold() for s in profile.include_service_types
    }:
        return "service_type"
    if services & {s.casefold() for s in profile.exclude_service_types}:
        return "service_type"
    if not _within(group_size, profile.group_size_min, profile.group_size_max):
        return "group_size"
    if not _within(org.number_of_beds, profile.beds_min, profile.beds_max):
        return "beds"
    return None


def _software_qualification(
    org: RankedOrganisation,
    profile: BuyerProfile,
    *,
    group_size: int,
    registrations_in_window: int,
    window_start: date,
    window_end: date,
) -> tuple[QualificationFactor, ...]:
    services = "; ".join(org.service_types)
    if not services:
        service_fit = QualificationFactor(
            "Service-type fit", "Unknown", "No service type recorded for this location",
            f"{_CQC_SOURCE}: location.gacServiceTypes",
        )
    else:
        restriction = (
            "matches the agreed service types"
            if profile.include_service_types
            else "no service-type restriction agreed"
        )
        service_fit = QualificationFactor(
            "Service-type fit", "Verified", f"{services} ({restriction})",
            f"{_CQC_SOURCE}: location.gacServiceTypes",
        )
    window = f"{window_start.isoformat()} to {window_end.isoformat()}"
    if registrations_in_window:
        expansion = QualificationFactor(
            "Recent registration",
            "Verified",
            f"{registrations_in_window} location(s) newly registered {window}",
            f"{_CQC_SOURCE}: location.registrationDate",
        )
    else:
        expansion = QualificationFactor(
            "Recent registration",
            "Not met",
            f"No new location registration found {window}",
            f"{_CQC_SOURCE}: location.registrationDate",
        )
    if org.number_of_beds is not None:
        beds = QualificationFactor(
            "Bed count", "Verified", f"{org.number_of_beds} beds",
            f"{_CQC_SOURCE}: location.numberOfBeds",
        )
    else:
        beds = QualificationFactor(
            "Bed count", "Unknown", "Not recorded for this location",
            f"{_CQC_SOURCE}: location.numberOfBeds",
        )
    return (
        service_fit,
        QualificationFactor(
            "Group size",
            "Verified",
            f"{group_size} registered CQC location(s) nationally "
            f"(agreed range: {_bounds_phrase(profile.group_size_min, profile.group_size_max)})",
            f"{_CQC_SOURCE}: location.providerId, location.registrationStatus",
        ),
        expansion,
        beds,
        QualificationFactor(
            "Existing care-records system", "Unknown",
            "Not held in CQC data; confirm with the provider", "none",
        ),
        QualificationFactor(
            "Procurement activity", "Not researched",
            "No procurement source is checked for this brief", "none",
        ),
        QualificationFactor(
            "Decision-maker role", "Not researched",
            "No contact research is included in this brief", "none",
        ),
        QualificationFactor(
            "Buying intent", "Unknown",
            "CQC records cannot show intent or budget", "none",
        ),
    )


def pilot_shortfall_notice(kept: int, pool: int, target: int) -> str | None:
    """Disclose a shortage against the pilot target. The pilot never pads."""
    if kept >= target:
        return None
    return (
        f"Shortfall: {kept} of the {pool} signal-ranked organisation(s) match the agreed "
        f"profile, fewer than the requested {target}. All matching organisations are "
        "included; none have been added to make up the number."
    )


def build_pilot_brief(
    brief: TerritoryBrief,
    profile: BuyerProfile,
    *,
    locations_source: str | Path,
    suppression: Suppression | None = None,
) -> PilotBrief:
    """Filter a generated brief to a buyer's profile and attach qualification records.

    Keeps the base brief's rank order and never adds accounts to reach the
    target. Generate the base brief with ``shortlist_target=MAX_SHORTLIST`` to
    give the filters the widest pool.
    """
    validate_profile(profile)
    location_rows = list(_load_ndjson(Path(locations_source)))
    group_sizes = provider_group_sizes(location_rows)
    registrations = provider_registrations_in_window(
        location_rows, window_start=brief.window_start, window_end=brief.window_end
    )

    exclusions = {reason: 0 for reason in EXCLUSION_REASONS}
    kept: list[RankedOrganisation] = []
    for org in brief.shortlist:
        reason = _exclusion_reason(org, profile, suppression, group_sizes.get(org.provider_id, 0))
        if reason:
            exclusions[reason] += 1
        else:
            kept.append(org)

    accounts = tuple(
        PilotAccount(
            rank=rank,
            base_rank=org.rank,
            organisation=org,
            registered_locations=group_sizes.get(org.provider_id, 0),
            qualification=_software_qualification(
                org,
                profile,
                group_size=group_sizes.get(org.provider_id, 0),
                registrations_in_window=registrations.get(org.provider_id, 0),
                window_start=brief.window_start,
                window_end=brief.window_end,
            ),
            next_step=_SOFTWARE_QUESTION,
        )
        for rank, org in enumerate(kept[: profile.pilot_target], start=1)
    )

    limitations = (
        f"Filters were applied to the base brief's top {len(brief.shortlist)} signal-ranked "
        f"organisations (at most {MAX_SHORTLIST}), not to every location in the territory.",
        "Order follows the base brief's opportunity score; the profile filters accounts but "
        "does not re-score them.",
        "Verified factors come from the CQC register edition dated "
        f"{brief.as_of_date.isoformat()}. Unknown and Not researched factors need confirming "
        "directly before any claim is made about them.",
        "CRM suppression uses exact identifier and normalised exact-name matches only.",
    )
    return PilotBrief(
        base=brief,
        profile=profile,
        accounts=accounts,
        pool_size=len(brief.shortlist),
        exclusions=exclusions,
        shortfall_notice=pilot_shortfall_notice(len(accounts), len(brief.shortlist), profile.pilot_target),
        limitations=limitations,
    )


# --------------------------------------------------------------------------- #
# Exports
# --------------------------------------------------------------------------- #

_FACTOR_NAMES = (
    "Service-type fit",
    "Group size",
    "Recent registration",
    "Bed count",
    "Existing care-records system",
    "Procurement activity",
    "Decision-maker role",
    "Buying intent",
)


def _column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")


def pilot_to_csv(pilot: PilotBrief) -> str:
    """Qualification sheet: one row per account, a status and finding per factor."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "rank",
            "base_rank",
            "organisation",
            "location",
            "cqc_location_id",
            "cqc_provider_id",
            "postcode",
            "registered_locations",
            "primary_signal",
            "reason",
            *(f"{_column(n)}_{part}" for n in _FACTOR_NAMES for part in ("status", "finding")),
            "next_step",
            "cqc_record_url",
            "source_edition_date",
            "shortlist_notice",
            "licence",
        ]
    )
    for account in pilot.accounts:
        org = account.organisation
        factors = {f.name: f for f in account.qualification}
        writer.writerow(
            [
                account.rank,
                account.base_rank,
                org.organisation_name,
                org.location_name,
                org.location_id,
                org.provider_id,
                org.postcode,
                account.registered_locations,
                org.primary_signal,
                org.reason,
                *(
                    value
                    for name in _FACTOR_NAMES
                    for value in (factors[name].status, factors[name].finding)
                ),
                account.next_step,
                CQC_PROFILE_URL.format(location_id=org.location_id),
                pilot.base.as_of_date.isoformat(),
                pilot.shortfall_notice or "",
                OGL_ATTRIBUTION,
            ]
        )
    return buf.getvalue()


CRM_COLUMNS = (
    "Account Name",
    "External ID",
    "Location",
    "Location ID",
    "Postcode",
    "Local Authority",
    "Region",
    "Registered Locations",
    "Fit Summary",
    "Unknowns",
    "Next Step",
    "CQC Record URL",
    "Source Edition Date",
)


def pilot_to_crm_csv(pilot: PilotBrief) -> str:
    """Generic CRM account import. ``External ID`` is the CQC provider id, one row per provider."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CRM_COLUMNS)
    for account in pilot.accounts:
        org = account.organisation
        writer.writerow(
            [
                org.organisation_name,
                org.provider_id,
                org.location_name,
                org.location_id,
                org.postcode,
                org.local_authority,
                org.region,
                account.registered_locations,
                account.fit_summary(),
                account.unknowns(),
                account.next_step,
                CQC_PROFILE_URL.format(location_id=org.location_id),
                pilot.base.as_of_date.isoformat(),
            ]
        )
    return buf.getvalue()


def pilot_to_review_markdown(pilot: PilotBrief) -> str:
    """Operator QC sheet: one checkbox per material claim, for an independent reviewer."""
    scope = pilot.base.scope
    lines = [
        f"# Pilot brief review: {scope.name} ({scope.kind.replace('_', ' ')})",
        "",
        f"- Source edition: {pilot.base.as_of_date.isoformat()}",
        f"- Window: {pilot.base.window_start.isoformat()} to {pilot.base.window_end.isoformat()}",
        f"- Segment: {pilot.profile.segment}",
        f"- Pool considered: {pilot.pool_size}; accounts kept: {len(pilot.accounts)} "
        f"of target {pilot.profile.pilot_target}",
        "- Exclusions: "
        + ", ".join(f"{reason} {count}" for reason, count in pilot.exclusions.items()),
    ]
    if pilot.shortfall_notice:
        lines.append(f"- {pilot.shortfall_notice}")
    lines += ["", "The reviewer is not the person who produced the brief. Tick a claim only after "
              "checking it against the linked source.", ""]
    for account in pilot.accounts:
        org = account.organisation
        url = CQC_PROFILE_URL.format(location_id=org.location_id)
        lines += [
            f"## {account.rank}. {org.organisation_name} - {org.location_name}",
            "",
            f"CQC record: {url}",
            "",
            f"- [ ] Organisation and location identity match the CQC record ({org.provider_id} / "
            f"{org.location_id})",
        ]
        for event in org.evidence:
            lines.append(
                f"- [ ] {event['detail']} ({event['source_field']}): {event['source_url']}"
            )
        for factor in account.qualification:
            if factor.status in ("Verified", "Not met"):
                lines.append(f"- [ ] {factor.name}: {factor.finding} [{factor.source}]")
        lines += [
            f"- [ ] Reason text makes no claim beyond the evidence: \"{org.reason}\"",
            "",
        ]
    lines += ["## Limitations", ""] + [f"- {item}" for item in pilot.limitations] + [""]
    return "\n".join(lines)
