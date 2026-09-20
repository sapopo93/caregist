"""Canonical classification of CQC rating values.

CQC publishes three different shapes through the same field
(``currentRatings.overall.rating``):

* a real published rating ("Outstanding", "Good", "Requires improvement",
  "Inadequate"),
* a sentinel string that is *not* a rating ("Not Yet Inspected",
  "No Published Rating", "Inspected but not rated", ...),
* nothing at all -- the block, the field, or the string is absent/blank.

Only the first shape is a rating. "Nothing at all" is a statement the source
makes about a payload that *was* read: the location publishes no current overall
rating. It is not an evidence gap and it is not licence to keep asserting the
previous rating, so it resolves to ``not_published`` and clears the column. An
unfamiliar non-empty string is the only payload shape that resolves to
``unknown`` (see :func:`classify_rating`): this build cannot read it, so the
state asserts nothing either way -- it is never treated as a rating. Because an
unknown state must not keep a previous rating publicly served, ingestion's
write policy clears the served rating column for it exactly as it does for the
other non-rated states, while the stored state stays ``unknown`` so the row and
the ledger still record that the wording was unreadable rather than absent.
Treating the other shapes as rating values is
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
#: values that may be read as "a rating", on both sides of the boundary: the
#: payload classifier and db/migrations/061_provider_rating_state.sql both take
#: their published-rating vocabulary from here. The migration half is checked
#: behaviourally -- tests/integration/test_migration_061_rating_state.py executes
#: migration 061 over the shared corpus and fails if any stored value classifies
#: differently there than it does through this module.
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

#: Public read-only view of the sentinel vocabulary. The real-Postgres corpus
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
    ``currentRatings`` block at all.
    ``historic_rating_present`` is True when the payload carried historic
    ratings only.

    The second element is a published rating value *only* for the ``rated``
    state; every sentinel, blank, missing or historic-only value returns
    ``None``. Historic ratings are never reported as the current value.

    Which payload shape maps to which state, and why (this is the contract the
    rating columns and the ledger depend on):

    * the ``rating`` field is ABSENT (no ``currentRatings`` block, no
      ``overall`` block, or no ``rating`` key) -> ``not_published``. A payload
      that was read successfully and carries no current overall rating is the
      source saying there is none; keeping the previous rating in the column
      asserted a rating the source no longer publishes.
    * the ``rating`` field is BLANK (``""``, ``"   "``) -> ``not_published``,
      for the same reason: :func:`normalize_rating_text` makes blank and absent
      the same shape, because whitespace is an empty field rather than a value.
    * a sentinel string -> its sentinel state (``not_yet_inspected``,
      ``not_published``, ``unrated``, ``not_applicable``); never ``rated``.
    * a value in :data:`PUBLISHED_RATING_VALUES` (casefolded, whitespace
      collapsed) -> ``rated``, with the source's own spelling as the value.
    * any other non-empty string -> ``unknown``. This is the only way a
      successfully read payload reaches ``unknown`` here, and it is deliberate:
      unfamiliar text in CQC's own rating field is a value this build cannot
      read, so it is neither asserted as a rating (the reviewed revision's
      ``ELSE 'rated'`` behaviour for ``"Suspended"``/``"Under review"``) nor
      allowed to leave a previous rating standing as the current one: the write
      policy clears the served rating column for it, exactly as for the other
      non-rated states. ``UNKNOWN`` stays the honest answer for input
      this code cannot interpret; it is not the answer for a field the source
      left empty.

    ``current_ratings_present`` and ``historic_rating_present`` remain part of
    the signature (callers pass the payload shape, and the shapes above are
    named after them) but no longer change the state; depending on them is
    exactly what left the previous rating in place for an absent or blank
    field. ``assess_location_rating`` still uses the payload shape for the
    evidence label.
    """
    del current_ratings_present, historic_rating_present

    normalized = normalize_rating_text(raw_value)
    if normalized is None:
        # Absent or blank: a payload that was read successfully and publishes no
        # current overall rating. Not an evidence gap.
        return (NOT_PUBLISHED, None)

    sentinel_state = _SENTINEL_STATES.get(normalized)
    if sentinel_state is not None:
        # A sentinel is not a rating and carries no rating value.
        return (sentinel_state, None)

    if normalized in PUBLISHED_RATING_VALUES:
        return (RATED, str(raw_value).strip())

    # Unfamiliar text: neither a published rating nor a known sentinel. Refusing
    # to guess is the whole point -- one authority, no catch-all.
    return (UNKNOWN, None)


def is_published_value(state: str) -> bool:
    """True only for a real published rating. Sentinels are not ratings."""
    return state == RATED


def is_sentinel_rating_text(raw_value: Any) -> bool:
    """True when a non-empty value is a CQC sentinel rather than a rating."""
    normalized = normalize_rating_text(raw_value)
    return normalized is not None and normalized in _SENTINEL_STATES


def classify_stored_rating(raw_value: Any) -> tuple[str, str | None]:
    """Classify a value that is *stored* in ``care_providers.overall_rating``.

    Same authority as :func:`classify_rating`, one difference of subject:

    * :func:`classify_rating` reads a CQC *payload field*
      (``currentRatings.overall.rating``). There, an absent or blank field is
      the source publishing no current rating -> ``not_published``, and an
      unfamiliar non-empty string is text in CQC's own rating field that this
      build cannot read -> ``unknown``.
    * a stored column has no such provenance -- older code wrote blanks and
      sentinels there -- so a blank or absent value resolves to ``unknown`` (the
      honest answer: storage says nothing about what the source published)
      instead of ``not_published``.

    Both classifiers accept the *same* rating vocabulary: only a value in
    :data:`PUBLISHED_RATING_VALUES` yields ``rated``, and unrecognised text is
    ``unknown`` in both. That equality is what the corpus test over the real
    migration asserts; a catch-all in either language would break it.
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
    null one. An absent or blank current overall rating IS supported by a
    successfully read payload (``not_published``, ``evidenced=True``); only
    unfamiliar text (``unknown``) is not.
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
        # Only unfamiliar non-empty text reaches 'unknown' now: absent and blank
        # are 'not_published' by contract (see classify_rating), and a payload
        # that could not be fetched or parsed never reaches this function -- the
        # caller fails closed before any write. Unrecognised text is a value this
        # build cannot read, so it is an evidence gap: nothing is asserted about
        # the rating, in either direction.
        evidence = "cqc.currentRatings.overall.rating (unrecognised text)"
        evidenced = False
    elif is_published_value(state):
        evidence = "cqc.currentRatings.overall.rating"
    elif is_sentinel_rating_text(raw_value):
        evidence = "cqc.currentRatings.overall.rating (sentinel)"
    elif normalize_rating_text(raw_value) is None:
        # Absent or blank current overall rating in a payload that WAS read: the
        # source publishes no current rating, and the payload supports that, so
        # the state is evidenced rather than a gap. The four shapes are named
        # separately because they are different evidence, not different states.
        if not current_present:
            evidence = "cqc.currentRatings absent"
        elif not overall_present:
            evidence = (
                "cqc.currentRatings (no overall) + cqc.historicRatings"
                if historic_raw is not None
                else "cqc.currentRatings (no overall, no historic evidence)"
            )
        elif raw_value is None:
            # overall present, no 'rating' key at all.
            evidence = "cqc.currentRatings.overall.rating absent"
        else:
            # overall present, 'rating' is whitespace-only text.
            evidence = "cqc.currentRatings.overall.rating blank"

    report_date = None
    if current_present:
        report_date = current_ratings.get("reportDate")
    if report_date is None and overall_present:
        report_date = overall.get("reportDate") or overall.get("date")
    if report_date is None and not is_published_value(state):
        # A historic rating's date dates that historic rating. It may inform a
        # non-rated state (there is no current published rating for it to
        # mis-date), but it must never be attached to a current published rating
        # it does not describe: that is what paired 'Outstanding' with a
        # historic 'Good' date. Callers gate on the state for the same reason
        # (see apply_rating_write_policy).
        report_date = historic_date

    return LocationRatingAssessment(
        state=state,
        value=value if is_published_value(state) else None,
        evidenced=evidenced,
        evidence=evidence,
        historic_rating=historic_raw,
        historic_rating_state=historic_state,
        historic_rating_date=historic_date,
        report_date=report_date,
    )

