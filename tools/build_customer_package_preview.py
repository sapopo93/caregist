#!/usr/bin/env python3
"""Build an explicit admin-only preview of the shared customer package.

This command never reads or writes order/payment state and never delivers a
file.  The required --preview switch is intentionally noisy: unpaid output is
watermarked in the selection confirmation and manifest.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from api.services import customer_package as packages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--preview", action="store_true", required=True)
    parser.add_argument("--product", choices=tuple(packages.PRODUCTS), required=True)
    parser.add_argument("--order-ref", required=True)
    parser.add_argument("--customer-ref", required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--geography", required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--provider-cap", type=int)
    parser.add_argument("--buyer-objective")
    parser.add_argument("--out", type=Path, default=Path(".tmp/customer-package-previews"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.product == "territory-opportunity-brief":
        if args.provider_cap is None:
            raise SystemExit("--provider-cap is required for a Territory Opportunity Brief preview")
        template = packages.TERRITORY_TEMPLATE_VERSION
        names = ("brief.pdf", "providers.csv")
        providers = packages.provider_records_from_csv(
            args.csv.read_text(encoding="utf-8"), provider_cap=args.provider_cap
        )
    else:
        if args.provider_cap is not None:
            raise SystemExit("--provider-cap is only valid for a Territory Opportunity Brief preview")
        template = packages.WEEKLY_DIGEST_TEMPLATE_VERSION
        names = ("digest.pdf", "digest.csv")
        providers = []
    snapshot = packages.verified_snapshot(
        order_reference=args.order_ref,
        customer_reference=args.customer_ref,
        product_id=args.product,
        payment_reference=None,
        template_version=template,
        source_version=args.source_version,
        geography=args.geography,
        provider_cap=args.provider_cap,
        buyer_objective=args.buyer_objective,
        confirmed_at=datetime.now(timezone.utc),
        preview=True,
    )
    built = packages.build_package_bytes(
        snapshot,
        {
            names[0]: packages.PackageArtifact(names[0], args.pdf.read_bytes(), "application/pdf"),
            names[1]: packages.PackageArtifact(
                names[1], args.csv.read_bytes(), "text/csv; charset=utf-8"
            ),
        },
        provider_records=providers,
    )
    package = packages.publish_package_atomically(
        built,
        root=args.out,
        order_reference=args.order_ref,
        customer_reference=args.customer_ref,
    )
    print(json.dumps({"preview": True, "package": str(package), "sha256": built.sha256}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
