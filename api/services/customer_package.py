"""Canonical, payment-bound customer packages for CareGist's two products.

The product generators remain authoritative for their content.  This module
adds the shared layer that they previously lacked: an immutable selection
snapshot, provider-level validation, a customer-readable confirmation, a
hashed manifest and an atomic ZIP publication boundary.

It deliberately performs no delivery or order-state mutation.  Callers must
first prove payment (or explicitly request a preview), then mark an order
fulfilled only after the complete package has been published successfully.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from pypdf import PdfReader

from api.services.pdf_writer import PdfBuilder

PACKAGE_SCHEMA_VERSION = "1.0"
TERRITORY_TEMPLATE_VERSION = "territory-brief-v2"
WEEKLY_DIGEST_TEMPLATE_VERSION = "weekly-digest-v2.2.1"
MAX_PROVIDERS = 50


class PackageBuildError(RuntimeError):
    """The package cannot be published without weakening its contract."""


class PackageBindingError(PackageBuildError):
    """Order, customer, payment or immutable snapshot evidence conflicts."""


class ProviderSelectionError(PackageBuildError):
    """The provider-level cohort is ambiguous, duplicated or above its cap."""


@dataclass(frozen=True)
class ProductDefinition:
    public_id: str
    internal_id: str
    display_name: str
    price_pence: int
    promise: str
    required_payloads: tuple[str, ...]


PRODUCTS: dict[str, ProductDefinition] = {
    "territory-opportunity-brief": ProductDefinition(
        public_id="territory-opportunity-brief",
        internal_id="territory_opportunity_brief",
        display_name="Territory Opportunity Brief",
        price_pence=74500,
        promise=(
            "One buyer-specific England territory research pack with a shortlist of up to 50 providers, "
            "a CRM-ready CSV and dated public-CQC evidence."
        ),
        required_payloads=("brief.pdf", "providers.csv"),
    ),
    "weekly-digest": ProductDefinition(
        public_id="weekly-digest",
        internal_id="weekly_digest_pilot",
        display_name="Weekly Digest pilot",
        price_pence=15000,
        promise=(
            "Four weekly issues for one England region, covering new registrations and newly published "
            "ratings with the observation window and source edition stated."
        ),
        required_payloads=("digest.pdf", "digest.csv"),
    ),
}

STANDARD_PAYLOADS = (
    "selection-confirmation.pdf",
    "selection.json",
    "evidence.json",
    "manifest.json",
)

DOSSIER_FIELDS = (
    "published_findings",
    "subsequent_evidence",
    "buyer_question",
    "comparative_reason",
    "disconfirming_evidence",
    "next_step",
    "owner_role",
    "decision_effect",
)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def customer_email_reference(email: str) -> str:
    """The customer binding every package carries: a hash, never the plain address.

    The reference appears in selection.json, manifest.json and the
    "Prepared for" line of the confirmation PDF, so a forwarded package must
    not expose the buyer's email.
    """
    cleaned = str(email or "").strip().lower()
    if not cleaned:
        raise PackageBindingError("customer email is required for the package binding")
    return f"email-sha256:{_sha256(cleaned.encode('utf-8'))}"


def _pdf_text(data: bytes, filename: str) -> str:
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if not reader.pages:
            raise ValueError("PDF has no pages")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise PackageBuildError(f"artifact {filename} is not an openable PDF") from exc


def _clean_text(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    text = str(value or "").strip()
    if required and not text:
        raise PackageBuildError(f"{field} is required")
    return text or None


@dataclass(frozen=True)
class SelectionSnapshot:
    order_reference: str
    customer_reference: str
    product_id: str
    payment_reference: str | None
    selection_version: int
    template_version: str
    source_version: str
    geography: str
    service_types: tuple[str, ...]
    rating_context_criteria: tuple[str, ...]
    provider_cap: int | None
    buyer_objective: str | None
    requested_files: tuple[str, ...]
    confirmed_at: str
    preview: bool = False

    def __post_init__(self) -> None:
        _clean_text(self.order_reference, "order_reference")
        _clean_text(self.customer_reference, "customer_reference")
        if self.product_id not in PRODUCTS:
            raise PackageBuildError(f"unsupported product_id {self.product_id!r}")
        if not self.preview:
            _clean_text(self.payment_reference, "payment_reference")
        if self.selection_version < 1:
            raise PackageBuildError("selection_version must be at least 1")
        _clean_text(self.template_version, "template_version")
        _clean_text(self.source_version, "source_version")
        _clean_text(self.geography, "geography")
        if self.provider_cap is not None and not 1 <= self.provider_cap <= MAX_PROVIDERS:
            raise PackageBuildError(f"provider_cap must be between 1 and {MAX_PROVIDERS}")
        if self.product_id == "territory-opportunity-brief" and self.provider_cap is None:
            raise PackageBuildError("provider_cap is required for a Territory Opportunity Brief")
        if self.product_id == "weekly-digest" and self.provider_cap is not None:
            raise PackageBuildError("provider_cap is not valid for a Weekly Digest")
        if len(set(self.requested_files)) != len(self.requested_files):
            raise PackageBuildError("requested_files contains duplicates")
        required = set(PRODUCTS[self.product_id].required_payloads) | set(STANDARD_PAYLOADS)
        missing = sorted(required - set(self.requested_files))
        if missing:
            raise PackageBuildError(f"requested_files is missing required output(s): {', '.join(missing)}")

    def payload(self) -> dict[str, Any]:
        return {"schema_version": PACKAGE_SCHEMA_VERSION, **asdict(self)}

    @property
    def sha256(self) -> str:
        return _sha256(_canonical_json(self.payload()))


@dataclass(frozen=True)
class PackageArtifact:
    filename: str
    data: bytes
    content_type: str

    def __post_init__(self) -> None:
        if not self.filename or Path(self.filename).name != self.filename:
            raise PackageBuildError(f"unsafe artifact filename {self.filename!r}")
        if not self.data:
            raise PackageBuildError(f"artifact {self.filename} is empty")
        if self.filename.endswith(".pdf"):
            _pdf_text(self.data, self.filename)
        if self.filename.endswith(".csv"):
            try:
                text = self.data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise PackageBuildError(f"artifact {self.filename} is not UTF-8 CSV") from exc
            if not next(csv.reader(io.StringIO(text)), []):
                raise PackageBuildError(f"artifact {self.filename} has no CSV header")


@dataclass(frozen=True)
class BuiltPackage:
    zip_bytes: bytes
    manifest: dict[str, Any]
    selection: dict[str, Any]
    evidence: dict[str, Any]
    version: str

    @property
    def sha256(self) -> str:
        return _sha256(self.zip_bytes)


def provider_cohort_from_locations(
    rows: Iterable[Mapping[str, Any]], *, provider_cap: int = MAX_PROVIDERS
) -> list[dict[str, Any]]:
    """Convert location rows to distinct providers before enforcing the cap.

    Multiple locations for the same provider are merged.  Conflicting provider
    names are rejected rather than silently binding the package to an ambiguous
    organisation.  The function never truncates an over-cap cohort.
    """
    if not 1 <= provider_cap <= MAX_PROVIDERS:
        raise ProviderSelectionError(f"provider cap must be between 1 and {MAX_PROVIDERS}")
    providers: dict[str, dict[str, Any]] = {}
    for raw in rows:
        provider_id = _clean_text(raw.get("provider_id"), "provider_id")
        location_id = _clean_text(raw.get("location_id"), "location_id")
        name = _clean_text(raw.get("provider_name") or raw.get("name"), "provider_name")
        current = providers.setdefault(
            provider_id,
            {
                "provider_id": provider_id,
                "provider_name": name,
                "location_ids": [],
                "qualification_status": "Qualification incomplete",
            },
        )
        if current["provider_name"].casefold() != name.casefold():
            raise ProviderSelectionError(f"provider {provider_id} has conflicting names")
        if location_id not in current["location_ids"]:
            current["location_ids"].append(location_id)
    if len(providers) > provider_cap:
        raise ProviderSelectionError(
            f"selection has {len(providers)} distinct providers, above the confirmed cap of {provider_cap}; "
            "narrow the selection and rebuild"
        )
    return [providers[key] for key in sorted(providers)]


def validate_provider_records(
    records: Iterable[Mapping[str, Any]], *, provider_cap: int | None
) -> list[dict[str, Any]]:
    """Validate final provider records and the premium-dossier boundary."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in records:
        row = dict(raw)
        provider_id = _clean_text(row.get("provider_id"), "provider_id")
        if provider_id in seen:
            raise ProviderSelectionError(f"duplicate provider record {provider_id}")
        seen.add(provider_id)
        status = _clean_text(row.get("qualification_status"), "qualification_status")
        dossier = row.get("dossier")
        if status == "Researched":
            if not isinstance(dossier, Mapping):
                raise ProviderSelectionError(f"researched provider {provider_id} has no dossier")
            missing = [field for field in DOSSIER_FIELDS if not str(dossier.get(field) or "").strip()]
            if missing:
                raise ProviderSelectionError(
                    f"researched provider {provider_id} dossier is missing: {', '.join(missing)}"
                )
        else:
            row["qualification_status"] = "Qualification incomplete"
            row.pop("dossier", None)
        row["provider_id"] = provider_id
        row["location_ids"] = sorted(set(str(item).strip() for item in row.get("location_ids", []) if str(item).strip()))
        result.append(row)
    if provider_cap is not None and len(result) > provider_cap:
        raise ProviderSelectionError(
            f"selection has {len(result)} providers, above the confirmed cap of {provider_cap}"
        )
    return sorted(result, key=lambda item: item["provider_id"])


def provider_records_from_csv(csv_text: str, *, provider_cap: int) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ProviderSelectionError("provider CSV has no header")
    locations = []
    seen_rows: set[tuple[str, str]] = set()
    for row_number, row in enumerate(reader, start=2):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        provider_id = row.get("provider_id") or row.get("cqc_provider_id")
        location_id = row.get("location_id") or row.get("cqc_location_id")
        name = (
            row.get("organisation_name")
            or row.get("organisation")
            or row.get("provider_name")
            or row.get("name")
        )
        if not provider_id or not location_id or not name:
            raise ProviderSelectionError(
                f"provider CSV row {row_number} is missing provider ID, location ID or organisation name"
            )
        row_identity = (str(provider_id).strip(), str(location_id).strip())
        if row_identity in seen_rows:
            raise ProviderSelectionError(
                f"provider CSV contains duplicate provider/location row {row_identity[0]}/{row_identity[1]}"
            )
        seen_rows.add(row_identity)
        locations.append({"provider_id": provider_id, "location_id": location_id, "provider_name": name})
    if not locations:
        raise ProviderSelectionError("provider CSV contains no provider rows")
    return provider_cohort_from_locations(locations, provider_cap=provider_cap)


def provider_roster_sha256(records: Iterable[Mapping[str, Any]]) -> str:
    roster = [
        {
            "provider_id": _clean_text(row.get("provider_id"), "provider_id"),
            "provider_name": _clean_text(row.get("provider_name"), "provider_name"),
            "location_ids": sorted(
                {_clean_text(item, "location_id") for item in row.get("location_ids", ())}
            ),
        }
        for row in records
    ]
    return _sha256(_canonical_json(sorted(roster, key=lambda row: row["provider_id"] or "")))


def _reconcile_provider_csv(
    artifact: PackageArtifact,
    providers: list[dict[str, Any]],
    *,
    provider_cap: int,
) -> None:
    csv_providers = provider_records_from_csv(
        artifact.data.decode("utf-8-sig"),
        provider_cap=provider_cap,
    )
    expected = {
        row["provider_id"]: (
            str(row.get("provider_name") or "").strip().casefold(),
            frozenset(row.get("location_ids") or ()),
        )
        for row in providers
    }
    actual = {
        row["provider_id"]: (
            str(row.get("provider_name") or "").strip().casefold(),
            frozenset(row.get("location_ids") or ()),
        )
        for row in csv_providers
    }
    if actual != expected:
        raise ProviderSelectionError(
            "providers.csv does not match the validated provider IDs, names and locations"
        )


def _validate_digest_csv(artifact: PackageArtifact) -> None:
    reader = csv.DictReader(io.StringIO(artifact.data.decode("utf-8-sig")))
    required = {"section", "date", "location_id", "name", "local_authority", "detail", "cqc_url"}
    missing = sorted(required - set(reader.fieldnames or ()))
    if missing:
        raise PackageBuildError(f"digest.csv is missing required column(s): {', '.join(missing)}")
    allowed_sections = {"new_registration", "rating_published"}
    for row_number, row in enumerate(reader, start=2):
        if not any(str(value or "").strip() for value in row.values()):
            continue
        if row.get("section") not in allowed_sections:
            raise PackageBuildError(f"digest.csv row {row_number} has an unsupported section")
        if not str(row.get("date") or "").strip() or not str(row.get("location_id") or "").strip():
            raise PackageBuildError(f"digest.csv row {row_number} is missing date or location_id")


def _selection_confirmation_pdf(
    snapshot: SelectionSnapshot,
    provider_count: int,
    researched_count: int,
    incomplete_count: int,
) -> bytes:
    product = PRODUCTS[snapshot.product_id]
    pdf = PdfBuilder(
        title=f"CareGist {product.display_name} - confirmed selection",
        footer=f"Order {snapshot.order_reference}. Selection snapshot {snapshot.sha256[:12]}.",
    )
    pdf.title_block(
        "Confirmed selection",
        [
            f"Order: {snapshot.order_reference}",
            f"Prepared for: {snapshot.customer_reference}",
            f"Product: {product.display_name}",
            f"Selection version: {snapshot.selection_version}",
        ],
    )
    pdf.heading("Scope")
    lines = [
        f"Geography: {snapshot.geography}",
        f"Service types: {', '.join(snapshot.service_types) if snapshot.service_types else 'All agreed service types'}",
        "Rating/context criteria: "
        + (", ".join(snapshot.rating_context_criteria) if snapshot.rating_context_criteria else "None supplied"),
        f"Buyer objective: {snapshot.buyer_objective or 'Not supplied by the buyer'}",
        f"Source version: {snapshot.source_version}",
        f"Template version: {snapshot.template_version}",
    ]
    if snapshot.product_id == "territory-opportunity-brief":
        lines.extend(
            [
                f"Product limit: up to {MAX_PROVIDERS} providers",
                f"Confirmed provider cap: {snapshot.provider_cap}",
                f"Distinct providers in this package: {provider_count}",
                f"Researched dossiers: {researched_count}",
                f"Qualification incomplete candidates: {incomplete_count}",
            ]
        )
    pdf.bullets(lines)
    pdf.heading("Files")
    pdf.bullets(list(snapshot.requested_files))
    pdf.heading("Research status", level=2)
    pdf.paragraph(
        "Only records marked Researched in evidence.json are completed dossiers. Records marked "
        "Qualification incomplete are candidates for further research; a historic rating alone does not "
        "establish a current deficiency, budget, need or buying intention."
    )
    if snapshot.preview:
        pdf.paragraph("ADMIN PREVIEW. This package is not proof of payment or delivery.")
    return pdf.build()


def build_package_bytes(
    snapshot: SelectionSnapshot,
    artifacts: Mapping[str, PackageArtifact],
    *,
    provider_records: Iterable[Mapping[str, Any]] = (),
    evidence: Mapping[str, Any] | None = None,
) -> BuiltPackage:
    """Build and validate one deterministic, order-bound ZIP in memory."""
    product = PRODUCTS[snapshot.product_id]
    if set(artifacts) != set(product.required_payloads):
        missing = sorted(set(product.required_payloads) - set(artifacts))
        extra = sorted(set(artifacts) - set(product.required_payloads))
        raise PackageBuildError(f"payload mismatch; missing={missing}, unexpected={extra}")
    for logical_name, artifact in artifacts.items():
        if artifact.filename != logical_name:
            raise PackageBuildError(
                f"artifact {logical_name} must use the canonical filename {logical_name!r}, got {artifact.filename!r}"
            )

    providers = validate_provider_records(provider_records, provider_cap=snapshot.provider_cap)
    if snapshot.product_id == "territory-opportunity-brief" and not providers:
        raise ProviderSelectionError("a Territory Opportunity Brief cannot contain an empty provider selection")
    if snapshot.product_id == "weekly-digest" and providers:
        raise ProviderSelectionError("a Weekly Digest cannot contain Territory Brief provider records")
    if snapshot.product_id == "territory-opportunity-brief":
        _reconcile_provider_csv(
            artifacts["providers.csv"],
            providers,
            provider_cap=snapshot.provider_cap or 0,
        )
        pdf_text = _pdf_text(artifacts["brief.pdf"].data, "brief.pdf")
        roster_hash = provider_roster_sha256(providers)
        if f"Provider roster SHA-256: {roster_hash}" not in pdf_text:
            raise ProviderSelectionError("brief.pdf does not carry the validated provider roster hash")
        if snapshot.order_reference not in pdf_text:
            raise PackageBindingError("brief.pdf does not match the selected order reference")
    else:
        _validate_digest_csv(artifacts["digest.csv"])
    researched = [row for row in providers if row["qualification_status"] == "Researched"]
    incomplete = [row for row in providers if row["qualification_status"] == "Qualification incomplete"]
    evidence_payload = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "selection_sha256": snapshot.sha256,
        "provider_count": len(providers),
        "researched_shortlist_count": len(researched),
        "qualification_incomplete_count": len(incomplete),
        "researched_shortlist": researched,
        "candidate_register": incomplete,
        "product_evidence": dict(evidence or {}),
        "research_limit": (
            "A historic rating does not establish a current deficiency, budget, need or buying intention. "
            "Qualification incomplete records are candidates for research, not premium dossiers."
        ),
    }
    selection_payload = {**snapshot.payload(), "selection_sha256": snapshot.sha256}
    payloads: dict[str, bytes] = {name: artifact.data for name, artifact in artifacts.items()}
    payloads["selection-confirmation.pdf"] = _selection_confirmation_pdf(
        snapshot,
        len(providers),
        len(researched),
        len(incomplete),
    )
    payloads["selection.json"] = _canonical_json(selection_payload)
    payloads["evidence.json"] = _canonical_json(evidence_payload)

    file_entries = [
        {"name": name, "bytes": len(data), "sha256": _sha256(data)}
        for name, data in sorted(payloads.items())
    ]
    content_sha256 = _sha256(_canonical_json(file_entries))
    version = f"{snapshot.selection_version}-{snapshot.sha256[:8]}-{content_sha256[:8]}"
    manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "package_version": version,
        "product": asdict(product),
        "order_reference": snapshot.order_reference,
        "customer_reference": snapshot.customer_reference,
        "payment_reference": snapshot.payment_reference,
        "selection_sha256": snapshot.sha256,
        "content_sha256": content_sha256,
        "preview": snapshot.preview,
        "counts": {
            "providers": len(providers),
            "researched_shortlist": len(researched),
            "qualification_incomplete": len(incomplete),
        },
        "files": file_entries,
    }
    payloads["manifest.json"] = _canonical_json(manifest)
    if set(payloads) != set(snapshot.requested_files):
        raise PackageBuildError(
            "built files do not match the confirmed request: "
            f"built={sorted(payloads)}, requested={sorted(snapshot.requested_files)}"
        )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payloads[name])
    return BuiltPackage(
        zip_bytes=output.getvalue(),
        manifest=manifest,
        selection=selection_payload,
        evidence=evidence_payload,
        version=version,
    )


def publish_package_atomically(
    built: BuiltPackage,
    *,
    root: Path,
    order_reference: str,
    customer_reference: str,
    fail_before_publish: bool = False,
) -> Path:
    """Publish one complete version with an atomic directory rename.

    Existing matching versions are revalidated and reused.  A conflicting
    version is treated as tampering rather than overwritten.
    """
    if built.manifest.get("order_reference") != order_reference:
        raise PackageBindingError("package order_reference does not match its publication target")
    if built.manifest.get("customer_reference") != customer_reference:
        raise PackageBindingError("package customer_reference does not match its publication target")
    safe_order = "".join(c if c.isalnum() or c in "-_" else "-" for c in order_reference).strip("-")
    if not safe_order:
        raise PackageBindingError("order_reference cannot produce a safe package path")
    order_root = root / safe_order
    final_dir = order_root / built.version
    zip_name = f"caregist-{safe_order}-{built.version}.zip"

    def reuse_existing() -> Path:
        manifest_path = final_dir / "manifest.json"
        zip_path = final_dir / zip_name
        try:
            current = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PackageBindingError(f"existing package {final_dir} is incomplete or unreadable") from exc
        if (
            current != json.loads(_canonical_json(built.manifest))
            or current.get("order_reference") != order_reference
            or current.get("selection_sha256") != built.manifest["selection_sha256"]
            or current.get("customer_reference") != customer_reference
            or not zip_path.exists()
            or _sha256(zip_path.read_bytes()) != built.sha256
        ):
            raise PackageBindingError(f"existing package {final_dir} conflicts with this order/customer build")
        return zip_path

    if final_dir.exists():
        return reuse_existing()

    order_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=order_root))
    try:
        with zipfile.ZipFile(io.BytesIO(built.zip_bytes)) as archive:
            archive.extractall(stage / "payload")
        (stage / "manifest.json").write_bytes(_canonical_json(built.manifest))
        (stage / zip_name).write_bytes(built.zip_bytes)
        if fail_before_publish:
            raise PackageBuildError("simulated interruption before atomic publish")
        try:
            os.replace(stage, final_dir)
        except OSError:
            # Another worker may have published this immutable version after
            # our initial existence check. Revalidate and reuse only an exact
            # match; every other failure remains fatal.
            if final_dir.exists():
                shutil.rmtree(stage, ignore_errors=True)
                return reuse_existing()
            raise
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return final_dir / zip_name


def verified_snapshot(
    *,
    order_reference: str,
    customer_reference: str,
    product_id: str,
    payment_reference: str | None,
    template_version: str,
    source_version: str,
    geography: str,
    service_types: Iterable[str] = (),
    rating_context_criteria: Iterable[str] = (),
    provider_cap: int | None = None,
    buyer_objective: str | None = None,
    requested_files: Iterable[str] | None = None,
    confirmed_at: datetime | None = None,
    preview: bool = False,
) -> SelectionSnapshot:
    product = PRODUCTS.get(product_id)
    if not product:
        raise PackageBuildError(f"unsupported product_id {product_id!r}")
    files = tuple(requested_files or (*product.required_payloads, *STANDARD_PAYLOADS))
    when = confirmed_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise PackageBuildError("confirmed_at must include a timezone")
    return SelectionSnapshot(
        order_reference=_clean_text(order_reference, "order_reference") or "",
        customer_reference=_clean_text(customer_reference, "customer_reference") or "",
        product_id=product_id,
        payment_reference=_clean_text(payment_reference, "payment_reference", required=not preview),
        selection_version=1,
        template_version=_clean_text(template_version, "template_version") or "",
        source_version=_clean_text(source_version, "source_version") or "",
        geography=_clean_text(geography, "geography") or "",
        service_types=tuple(sorted({_clean_text(item, "service_type") or "" for item in service_types})),
        rating_context_criteria=tuple(
            sorted({_clean_text(item, "rating_context_criterion") or "" for item in rating_context_criteria})
        ),
        provider_cap=provider_cap,
        buyer_objective=_clean_text(buyer_objective, "buyer_objective", required=False),
        requested_files=files,
        confirmed_at=when.astimezone(timezone.utc).isoformat(),
        preview=preview,
    )
