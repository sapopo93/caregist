"""Classify CQC registration endings: closure, re-registration, dormant, unresolved.

A deregistered CQC location is not necessarily a closed service. CQC also ends
a registration when the same service changes owner (new provider, legal-entity
or partnership change, NHS transfer) or moves address, and links the old and new
locations through ``relationships`` (``HSCA Successor`` on the old location,
``HSCA Predecessor`` on the new one). Counting every deregistration as a
closure therefore overstates market exits.

Classes:

``re_registration``
    CQC links the ended location to a successor location (either side of the
    relationship). ``kind`` is ``ownership_change`` or ``location_move``.
``dormant``
    The location was dormant (no one using it or its regulated activity) when
    its registration ended; no service stopped operating.
``unresolved``
    The data cannot confirm a closure: the end date is missing, or an unlinked
    location with the same name and postcode registered within
    :data:`UNLINKED_SUCCESSOR_DAYS` days of the ending.
``confirmed_closure``
    Deregistered, dated, not dormant, no successor link and no unlinked
    look-alike successor.

Movement counts use ``confirmed_closure`` only. Pure: callers supply rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Iterable

CONFIRMED_CLOSURE = "confirmed_closure"
RE_REGISTRATION = "re_registration"
DORMANT = "dormant"
UNRESOLVED = "unresolved"
ENDING_CLASSES = (CONFIRMED_CLOSURE, RE_REGISTRATION, DORMANT, UNRESOLVED)

UNLINKED_SUCCESSOR_DAYS = 120

_OWNERSHIP_REASONS = {"New Provider", "Legal Entity Change", "Partnership Change", "NHS Transfer"}


def _day(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text or "").casefold())


@dataclass(frozen=True)
class Ending:
    location_id: str
    ending_class: str
    end_date: date | None
    kind: str | None = None
    reason: str = ""
    successor_ids: tuple[str, ...] = field(default_factory=tuple)
    successors_in_data: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class EndingIndex:
    """Lookups built once over a full export (registered and deregistered rows)."""

    ids: set[str] = field(default_factory=set)
    #: ended location id -> [(successor id, reason)] from the successor's side.
    successors_by_predecessor: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    #: (normalised name, normalised postcode) -> [(location id, registration date)].
    by_name_postcode: dict[tuple[str, str], list[tuple[str, date | None]]] = field(default_factory=dict)

    @classmethod
    def build(cls, rows: Iterable[dict[str, Any]]) -> "EndingIndex":
        idx = cls()
        for row in rows:
            lid = str(row.get("locationId") or "")
            if not lid:
                continue
            idx.ids.add(lid)
            for rel in row.get("relationships") or []:
                if isinstance(rel, dict) and rel.get("type") == "HSCA Predecessor" and rel.get("relatedLocationId"):
                    idx.successors_by_predecessor.setdefault(rel["relatedLocationId"], []).append(
                        (lid, str(rel.get("reason") or ""))
                    )
            key = (_norm(row.get("name")), _norm(row.get("postalCode")))
            if all(key):
                idx.by_name_postcode.setdefault(key, []).append((lid, _day(row.get("registrationDate"))))
        return idx


def classify_ending(row: dict[str, Any], index: EndingIndex) -> Ending | None:
    """Classify one location's registration ending; ``None`` if it has not ended."""
    if row.get("registrationStatus") != "Deregistered":
        return None
    lid = str(row.get("locationId") or "")
    end = _day(row.get("deregistrationDate"))

    links: list[tuple[str, str]] = [
        (str(rel["relatedLocationId"]), str(rel.get("reason") or ""))
        for rel in row.get("relationships") or []
        if isinstance(rel, dict) and rel.get("type") == "HSCA Successor" and rel.get("relatedLocationId")
    ]
    links += index.successors_by_predecessor.get(lid, [])
    if links:
        ids = tuple(sorted({sid for sid, _ in links}))
        reasons = {reason for _, reason in links}
        kind = "location_move" if reasons == {"Location Move"} else (
            "ownership_change" if reasons & _OWNERSHIP_REASONS else "linked_successor"
        )
        return Ending(
            location_id=lid, ending_class=RE_REGISTRATION, end_date=end, kind=kind,
            reason="CQC links a successor location: " + ", ".join(sorted(r for r in reasons if r)),
            successor_ids=ids, successors_in_data=tuple(i for i in ids if i in index.ids),
        )
    if str(row.get("dormancy") or "").upper() == "Y":
        return Ending(lid, DORMANT, end, reason="Location was dormant when its registration ended")
    if end is None:
        return Ending(lid, UNRESOLVED, None, reason="Deregistered with no deregistration date")

    key = (_norm(row.get("name")), _norm(row.get("postalCode")))
    if all(key):
        lookalikes = tuple(sorted(
            other for other, registered in index.by_name_postcode.get(key, [])
            if other != lid and registered and abs((registered - end).days) <= UNLINKED_SUCCESSOR_DAYS
        ))
        if lookalikes:
            return Ending(
                lid, UNRESOLVED, end,
                reason=(f"Same name and postcode registered within {UNLINKED_SUCCESSOR_DAYS} days "
                        "without a CQC successor link"),
                successor_ids=lookalikes, successors_in_data=lookalikes,
            )
    return Ending(lid, CONFIRMED_CLOSURE, end, reason="Deregistered with no successor and not dormant")


def classifier_for_export(rows: Iterable[dict[str, Any]]) -> Callable[[dict[str, Any]], str]:
    """Return ``row -> class name`` for movement counting over one export."""
    index = EndingIndex.build(rows)

    def classify(row: dict[str, Any]) -> str:
        ending = classify_ending(row, index)
        return ending.ending_class if ending else "not_ended"

    return classify
