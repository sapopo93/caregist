"""Canonical classification of CQC rating values.

CQC publishes three different shapes through the same field
(``currentRatings.overall.rating``):

* a real published rating ("Outstanding", "Good", "Requires improvement",
  "Inadequate"),
* a sentinel string that is *not* a rating ("Not Yet Inspected",
  "No Published Rating", "Inspected but not rated", ...),
* nothing at all -- the block, the field, or the string is absent/blank.

Only the first shape is a rating. Treating the other two as rating values is
what wrote blanks and sentinels into ``care_providers.overall_rating`` and
produced ~24k ``rating_changed`` ledger events whose destination was empty:
representation churn (sentinel vs omitted field) was being read as rating
movement.

This module is pure -- no I/O, no database, no network -- so ingestion can
classify a payload before any SQL runs and every rule is unit-testable.
Callers decide what to write; these functions only decide what the source
said.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RATED = "rated"
NOT_YET_INSPECTED = "not_yet_inspected"
NOT_PUBLISHED = "not_published"
UNRATED = "unrated"
NOT_APPLICABLE = "not_applicable"
UNKNOWN = "unknown"

#: Every state :func:`classify_rating` may return.
RATING_STATES = frozenset(
    {
        RATED,
        NOT_YET_INSPECTED,
        NOT_PUBLISHED,
        UNRATED,
        NOT_APPLICABLE,
        UNKNOWN,
    }
)

#: States that mean "there is no current published rating".
NON_RATED_STATES = frozenset(
    {NOT_YET_INSPECTED, NOT_PUBLISHED, UNRATED, NOT_APPLICABLE}
)

#: Normalised texts of CQC's real published ratings. This is the *only* set of
#: values that may be read as "a rating". It is the shared authority referenced
#: by db/migrations/061_provider_rating_state.sql (asserted by
#: tests/test_migration_governance.py), so SQL and Python cannot drift.
PUBLISHED_RATING_VALUES = frozenset(
    {"outstanding", "good", "requires improvement", "inadequate"}
)

#: Sentinel strings CQC publishes instead of a rating, keyed by their
#: normalised form. Every one of these is "not a rating"; none is a rating
#: problem, a hold, or a pending inspection to be guessed at.
_SENTINEL_STATES: dict[str, str] = {
    "not yet inspected": NOT_YET_INSPECTED,
    "not inspected": NOT_YET_INSPECTED,
    "awaiting inspection": NOT_YET_INSPECTED,
    "no published rating": NOT_PUBLISHED,
    "not published": NOT_PUBLISHED,
    "no rating": NOT_PUBLISHED,
    "rating not published": NOT_PUBLISHED,
    "inspected but not rated": UNRATED,
    "not rated": UNRATED,
    "unrated": UNRATED,
    "not applicable": NOT_APPLICABLE,
    "n/a": NOT_APPLICABLE,
}

#: States only a sentinel string can produce. ``not_published`` is excluded
#: because an omitted ratings block reaches it as well; callers that care
#: about the difference must inspect the raw payload.
SENTINEL_STATES = frozenset({NOT_YET_INSPECTED, UNRATED, NOT_APPLICABLE})

#: Public read-only view of the sentinel vocabulary. The migration governance
#: test reads it (with :data:`PUBLISHED_RATING_VALUES`) to prove that SQL
#: migration 061 classifies stored values exactly the way this module does.
SENTINEL_STATE_BY_TEXT: dict[str, str] = _SENTINEL_STATES


def normalize_rating_text(raw_value: Any) -> str | None:
    """Casefold and whitespace-collapse a value for comparison.

    Returns ``None`` for anything absent, non-textual or blank, which is how
    "missing" and "empty" stay equivalent without ever inventing a value.
    """
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        raw_value = str(raw_value)
    text = " ".join(raw_value.split()).casefold()
    return text or None


def classify_rating(
    raw_value: Any,
    current_ratings_present: bool,
    historic_rating_present: bool,
) -> tuple[str, str | None]:
    """Classify one CQC rating field into ``(state, published_value_or_None)``.

    ``raw_value`` is the raw ``currentRatings.overall.rating`` value (or
    ``None`` when the field/block is absent).
    ``current_ratings_present`` is True when the payload carried a
    ``currentRatings`` block at all (a present-but-valueless block is an
    evidence gap, not a statement that no rating exists).
    ``historic_rating_present`` is True when the payload carried historic
    ratings only.

    The second element is a published rating value *only* for the ``rated``
    state; every sentinel, blank, missing or historic-only value returns
    ``None``. Historic ratings are never reported as the current value.
    """
    normalized = normalize_rating_text(raw_value)
    if normalized is None:
        if current_ratings_present:
            # The block exists but carries no usable value: we cannot claim a
            # rating and cannot claim there is none either.
            return (UNKNOWN, None)
        # No published rating. ``historic_rating_present`` is accepted as
        # evidence that a rating existed in the past, which is exactly why it
        # must never be reported as the current value: the state is
        # 'not_published' either way and the value stays None.
        return (NOT_PUBLISHED, None)

    sentinel_state = _SENTINEL_STATES.get(normalized)
    if sentinel_state is not None:
        # A sentinel is not a rating and carries no rating value.
        return (sentinel_state, None)

    return (RATED, str(raw_value).strip())


def is_published_value(state: str) -> bool:
    """True only for a real published rating. Sentinels are not ratings."""
    return state == RATED


def is_sentinel_rating_text(raw_value: Any) -> bool:
    """True when a non-empty value is a CQC sentinel rather than a rating."""
    normalized = normalize_rating_text(raw_value)
    return normalized is not None and normalized in _SENTINEL_STATES


def classify_stored_rating(raw_value: Any) -> tuple[str, str | None]:
    """Classify a value that is *stored* in ``care_providers.overall_rating``.

    Stricter than :func:`classify_rating`, deliberately:

    * :func:`classify_rating` reads a CQC *payload field*
      (``currentRatings.overall.rating``), where an unfamiliar string is still
      CQC's own text in CQC's own rating field;
    * a stored column has no such provenance -- older code wrote blanks and
      sentinels there -- so an unrecognised value resolves to ``unknown`` (the
      honest answer) instead of being asserted as a rating.

    Only a value in :data:`PUBLISHED_RATING_VALUES` yields ``rated``. That is
    what makes an ``ELSE 'rated'`` catch-all unnecessary in SQL migration 061
    and keeps the two classifiers in step. A blank or absent value is
    ``unknown`` here because the caller is reading storage, not a payload.
    """
    normalized = normalize_rating_text(raw_value)
    if normalized is None:
        return (UNKNOWN, None)
    if normalized in PUBLISHED_RATING_VALUES:
        return (RATED, str(raw_value).strip())
    sentinel_state = _SENTINEL_STATES.get(normalized)
    if sentinel_state is not None:
        return (sentinel_state, None)
    return (UNKNOWN, None)


def stored_rating_is_published(raw_value: Any) -> bool:
    """True when a stored column value is a published rating.

    Used to decide whether an existing ``care_providers.overall_rating`` is
    real evidence (never treat it as a current rating from an absence) or
    representation garbage left by the old ``""``-on-missing behaviour (safe to
    clear). Uses :func:`classify_stored_rating`, so an unrecognised value such
    as ``"Suspended"`` is not read as a published rating.
    """
    state, value = classify_stored_rating(raw_value)
    return is_published_value(state) and value is not None


def _latest_historic_overall(payload: dict[str, Any]) -> tuple[Any, Any]:
    """Return ``(raw_overall_rating, date)`` for the newest historic rating.

    CQC publishes ``historicRatings`` as a list whose first entry is the most
    recent. A historic rating is evidence about the past only; it is never
    returned as a current value.
    """
    historic = payload.get("historicRatings")
    candidates: list[Any] = []
    if isinstance(historic, list):
        candidates = historic
    elif isinstance(historic, dict):
        candidates = [historic]
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        overall = entry.get("overall")
        raw_value = overall.get("rating") if isinstance(overall, dict) else None
        if raw_value is None or str(raw_value).strip() == "":
            continue
        entry_date = (
            entry.get("date")
            or entry.get("reportDate")
            or entry.get("publishedDate")
            or entry.get("effectiveDate")
        )
        return (raw_value, entry_date)
    return (None, None)


@dataclass(frozen=True)
class LocationRatingAssessment:
    """What one CQC location payload says about the location's rating.

    ``state`` is always one of :data:`RATING_STATES`. ``value`` is a published
    rating only for the ``rated`` state. ``evidenced`` is False when the
    payload does not support the state it produced (an evidence gap), which
    callers must surface as an incomplete destination rather than a blank or
    null one.
    """

    state: str
    value: str | None
    evidenced: bool
    evidence: str
    historic_rating: str | None
    historic_rating_state: str | None
    historic_rating_date: Any | None
    report_date: Any | None


def assess_location_rating(payload: dict[str, Any]) -> LocationRatingAssessment:
    """Classify the rating of a whole CQC location payload.

    This is the single place that decides what a payload says, so the
    ``currentRatings`` shape, the sentinel strings and the historic evidence
    are all interpreted together instead of in three different call sites.
    """
    current_ratings = payload.get("currentRatings")
    current_present = isinstance(current_ratings, dict)
    overall = current_ratings.get("overall") if current_present else None
    overall_present = isinstance(overall, dict)
    raw_value = overall.get("rating") if overall_present else None

    historic_raw, historic_date = _latest_historic_overall(payload)
    historic_state: str | None = None
    historic_value: str | None = None
    if historic_raw is not None:
        historic_state, historic_value = classify_rating(
            historic_raw,
            current_ratings_present=False,
            historic_rating_present=True,
        )

    state, value = classify_rating(
        raw_value,
        current_ratings_present=current_present,
        historic_rating_present=historic_raw is not None,
    )
    evidence = "cqc.currentRatings.overall.rating"
    evidenced = True
    if state == UNKNOWN:
        if historic_raw is not None:
            # The ratings block carries no current overall value while the
            # source still publishes a historic rating: the location has no
            # *current* published rating. That is a source-supported state, not
            # an evidence gap.
            state = NOT_PUBLISHED
            evidence = "cqc.currentRatings (no overall) + cqc.historicRatings"
        else:
            evidence = "cqc.currentRatings (no overall, no historic evidence)"
            evidenced = False
    elif is_published_value(state):
        evidence = "cqc.currentRatings.overall.rating"
    elif is_sentinel_rating_text(raw_value):
        evidence = "cqc.currentRatings.overall.rating (sentinel)"
    elif not current_present:
        evidence = "cqc.currentRatings absent"

    report_date = None
    if current_present:
        report_date = current_ratings.get("reportDate")
    if report_date is None and overall_present:
        report_date = overall.get("reportDate") or overall.get("date")
    if report_date is None:
        report_date = historic_date

    return LocationRatingAssessment(
        state=state,
        value=value if is_published_value(state) else None,
        evidenced=evidenced or is_published_value(state),
        evidence=evidence,
        historic_rating=historic_raw,
        historic_rating_state=historic_state,
        historic_rating_date=historic_date,
        report_date=report_date,
    )

