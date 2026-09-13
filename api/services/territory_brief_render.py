"""Render a :class:`TerritoryBrief` to a professional multi-page PDF.

Kept separate from the generator so the document toolchain can be swapped
without touching ranking or reason logic. Uses the dependency-free
:mod:`api.services.pdf_writer`.
"""

from __future__ import annotations

from datetime import date

from api.services.pdf_writer import PdfBuilder
from api.services.territory_brief import TerritoryBrief

_DISCLAIMER = (
    "CareGist is independent of the Care Quality Commission. This brief is compiled from the "
    "published CQC register and is provided for business research. It is not regulatory, legal, "
    "financial, or investment advice, and it makes no statement about any provider's quality, "
    "solvency, or intentions. Opportunity signals indicate where a buyer may wish to investigate "
    "first. Verify every organisation's current status directly with CQC before acting. "
    "Contains public sector information licensed under the Open Government Licence v3.0."
)


def _fmt_date(value: date) -> str:
    return value.strftime("%d %B %Y")


def render_brief_pdf(brief: TerritoryBrief) -> bytes:
    scope = brief.scope
    es = brief.executive_summary
    pdf = PdfBuilder(
        title="Territory Opportunity Brief",
        footer=f"CareGist  |  {scope.name}  |  Confidential to order {brief.purchase_context.order_reference}",
    )

    pdf.title_block(
        subtitle=f"{scope.name} ({scope.kind.replace('_', ' ')}) - generated {_fmt_date(brief.as_of_date)}",
        meta_lines=[
            f"Prepared for order {brief.purchase_context.order_reference}",
            f"Opportunity window: {_fmt_date(brief.window_start)} to {_fmt_date(brief.window_end)} "
            f"({scope.window_days} days)",
            f"Organisations considered: {brief.considered_locations}   "
            f"Shortlisted: {len(brief.shortlist)}   "
            f"Territory locations in source: {brief.territory_locations}",
            f"Source: CQC public register edition {brief.as_of_date.isoformat()}. "
            f"Product: Territory Opportunity Brief (GBP {brief.purchase_context.price_gbp}).",
            "Contents: sections 1-2 and 4-7 are the executive brief; Appendix A carries the "
            "reason and evidence for every shortlisted organisation.",
        ],
    )

    # 1. Executive summary
    pdf.heading("1. Executive summary")
    pdf.paragraph(es["headline"])
    pdf.key_values(
        [
            ("Territory", f'{es["territory"]} ({es["territory_kind"]})'),
            ("Date generated", es["date_generated"]),
            ("Window", es["window"]),
            ("Opportunity set", str(es["opportunity_set_size"])),
            ("Shortlisted & ranked", str(es["shortlisted"])),
            ("Movement in window", es["movement_summary"]),
        ]
    )
    pdf.spacer(2)
    pdf.paragraph("Strongest areas of movement:")
    pdf.bullets(list(es["strongest_opportunities"]) or ["No shortlisted organisations in this window."])
    pdf.paragraph(f"Limitations: {es['limitations']}", muted=True)

    # 2. Ranked shortlist
    pdf.heading("2. Ranked opportunity shortlist")
    pdf.paragraph(
        "Ranked by a deterministic opportunity score (see section 5). Every row carries a stated "
        "reason and links to the underlying CQC record. The same source data always produces this "
        "same order."
    )
    rows = []
    for o in brief.shortlist:
        rows.append(
            [
                o.rank,
                f"{o.organisation_name}\n{o.location_name}",
                o.local_authority or o.region,
                f"{o.primary_signal}\n{o.most_recent_event_date.isoformat() if o.most_recent_event_date else ''}",
                f"{o.score:.0f}",
            ]
        )
    pdf.table(
        ["#", "Organisation / location", "Area", "Primary signal", "Score"],
        rows,
        widths=[0.32, 2.5, 1.15, 1.5, 0.5],
    )

    # 3. How to read the shortlist (short; detail is in Appendix A)
    pdf.heading("3. How the shortlist was built")
    pdf.paragraph(
        "Each organisation reached this list because of at least one supported event in the "
        "window: a new CQC registration, an overall rating change, or a newly published "
        "inspection report. The opportunity score combines the event type, how recent it is, "
        "the direction of any rating move, the size of the location, and whether the same "
        "provider has several locations moving at once. Appendix A gives the full reason and "
        "the evidence for every organisation, in rank order."
    )

    # 4. Territory insights
    pdf.heading("4. Territory insights")
    ins = brief.territory_insights
    pdf.paragraph("Aggregate view of the whole opportunity set (not just the shortlist).")
    pdf.key_values(
        [
            ("Events by type", ", ".join(f"{k}: {v}" for k, v in ins["events_by_type"].items()) or "none"),
            ("Rating moves", f"{ins['rating_moves']['declines']} downgrades, "
                             f"{ins['rating_moves']['improvements']} upgrades"),
            ("New beds entering market", str(ins["new_beds_entering_market"])),
        ]
    )
    if ins["activity_by_sub_area"]:
        pdf.spacer(2)
        pdf.paragraph("Activity by sub-area:")
        pdf.table(
            ["Area", "Qualifying events"],
            [[a["area"], a["events"]] for a in ins["activity_by_sub_area"]],
            widths=[3, 1],
        )
    if ins["service_type_mix"]:
        pdf.paragraph("Service-type mix in the opportunity set:")
        pdf.table(
            ["Service type", "Organisations"],
            [[s["service_type"], s["organisations"]] for s in ins["service_type_mix"]],
            widths=[3, 1],
        )
    if ins["most_active_providers"]:
        pdf.paragraph("Providers with more than one location moving (account-level opportunities):")
        pdf.bullets(
            [f"{p['provider']} - {p['locations_moving']} locations" for p in ins["most_active_providers"]]
        )
    else:
        pdf.paragraph("No single provider has more than one location moving in this window.", muted=True)

    # 5. Recommended next actions
    pdf.heading("5. Recommended next actions")
    pdf.paragraph(
        "Practical, evidence-bounded. These are based on the signals in this brief and do not "
        "assume any provider is in difficulty or seeking a supplier."
    )
    pdf.bullets(list(brief.next_actions), ordered=True)

    # 6. Methodology and data notes
    pdf.heading("6. Methodology and data notes")
    pdf.bullets(list(brief.methodology_notes))

    # 7. Limitations and disclaimer
    pdf.heading("7. Limitations and disclaimer")
    pdf.bullets(list(brief.data_caveats))
    pdf.spacer(4)
    pdf.paragraph(_DISCLAIMER, italic=True, muted=True)
    pdf.spacer(4)
    prov = brief.source_provenance
    pdf.paragraph(
        f"Provenance: {prov['locations_snapshot']} + {prov['providers_snapshot']}, "
        f"edition {prov['snapshot_edition_date']}. Source page: {prov['source_page']}. "
        f"Licence: {prov['licence_url']}",
        muted=True,
    )

    # Appendix A - reason + evidence for every shortlisted organisation.
    # Flows straight on from the executive brief rather than forcing a blank
    # tail page; the heading marks the boundary.
    pdf.spacer(6)
    pdf.rule()
    pdf.heading("Appendix A. Reason and evidence, by rank")
    pdf.paragraph(
        "One entry per shortlisted organisation, in the same order as section 2. Every entry "
        "has a non-empty, evidence-bound reason and links to the underlying CQC record.",
        muted=True,
    )
    for o in brief.shortlist:
        meta = [o.local_authority or o.region]
        if o.postcode:
            meta.append(o.postcode)
        if o.service_types:
            meta.append(o.service_types[0])
        if o.number_of_beds:
            meta.append(f"{o.number_of_beds} beds")
        if o.current_rating:
            meta.append(f"rating {o.current_rating}")
        meta.append(f"score {o.score:.0f}")
        pdf.spacer(3)
        pdf.paragraph(f"{o.rank}. {o.organisation_name} - {o.location_name}")
        pdf.paragraph("   " + "  |  ".join(m for m in meta if m), muted=True)
        pdf.paragraph("   " + o.reason)
        ev = "; ".join(f"{e['effective_date']} {e['detail']}" for e in o.evidence)
        pdf.paragraph(f"   Evidence: {ev}", muted=True)
        pdf.paragraph(f"   CQC record: {_cqc_url(o.location_id)}", muted=True)

    return pdf.build()


def _cqc_url(location_id: str) -> str:
    return f"https://api.service.cqc.org.uk/public/v1/locations/{location_id}"
