"""Provenance-aware resolved-current-rating contract.

CQC publishes a location's rating through more than one channel, and they do
not always agree:

* the public API (``currentRatings``), mirrored in ``care_providers.overall_rating``
  with its report date in ``last_published_rating_date``;
* the published "Latest ratings" file (``ratings.ods``), mirrored in the
  ``file_overall_rating*`` columns (migration 068) and carrying an explicit
  ``Inherited Rating (Y/N)`` column;
* optionally, a dated observation of what CQC's own location page showed.

The 22 Oct 2026 rating audit (``artifacts/rating-audit/2026-10-22``) showed that
neither channel can be preferred wholesale: four API values predate newer file
and website ratings, while two locations (Check House, Tillingham) carry
ratings inherited from a predecessor registration that the page does not show
as a current inspection. This module therefore resolves one rating *domain*
(overall, Well-led, ...) for one location from every piece of evidence, keeps
all of it, and reports a status:

``current``
    One published value is the most recent and was earned by this registration.
``inherited``
    The value was published before this registration (or is flagged inherited
    by the source). It is a fact about the predecessor, never a verified
    current inspection, and rating-based scope decisions must not use it.
``unresolved``
    The evidence conflicts in a way the data cannot settle (undated conflict,
    same-date conflict, or an inherited value contradicted by a current one).
    Outputs omit the value; nothing is guessed.
``none``
    No channel publishes a rating value (not inspected, inspected but not
    rated, or nothing at all).

Pure: no I/O. Callers load the evidence; :func:`resolve_rating` decides.
A file observation is never a rating-change event: this module only states
which value is current, not when it changed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Iterable

from api.services.rating_states import PUBLISHED_RATING_VALUES, normalize_rating_text

CURRENT = "current"
INHERITED = "inherited"
UNRESOLVED = "unresolved"
NONE = "none"

RESOLUTION_STATUSES = frozenset({CURRENT, INHERITED, UNRESOLVED, NONE})

#: Statuses whose value may be shown. ``unresolved`` and ``none`` show nothing.
DISPLAYABLE_STATUSES = frozenset({CURRENT, INHERITED})

SOURCE_API = "cqc_api"
SOURCE_FILE = "cqc_ratings_file"
SOURCE_WEBSITE = "cqc_website"

_CANONICAL = {
    "outstanding": "Outstanding",
    "good": "Good",
    "requires improvement": "Requires improvement",
    "inadequate": "Inadequate",
}


def canonical_rating(raw: Any) -> str | None:
    """Return CQC's spelling of a published rating, or ``None`` for anything else.

    Sentinels ("Not yet inspected", "Inspected but not rated") and unfamiliar
    text are not ratings and resolve to ``None``.
    """
    text = normalize_rating_text(raw)
    if text is None or text not in PUBLISHED_RATING_VALUES:
        return None
    return _CANONICAL[text]


@dataclass(frozen=True)
class RatingEvidence:
    """One channel's statement about one rating domain of one location."""

    source: str
    value: str | None
    publication_date: date | None = None
    #: True/False when the source says so explicitly; ``None`` when it is silent.
    inherited_flag: bool | None = None
    #: Content hash of the file edition the value came from (file evidence only).
    source_sha256: str | None = None
    #: Edition/as-at date of the file or snapshot the value came from.
    edition_date: date | None = None
    #: When a website observation was made (website evidence only).
    observed_on: date | None = None
    #: Raw text as published, kept so sentinels stay visible in the record.
    raw_value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for key in ("publication_date", "edition_date", "observed_on"):
            if out[key] is not None:
                out[key] = out[key].isoformat()
        return out


@dataclass(frozen=True)
class ResolvedRating:
    domain: str
    status: str
    value: str | None
    source: str | None
    publication_date: date | None
    reason: str
    evidence: tuple[RatingEvidence, ...] = field(default_factory=tuple)
    #: True when the chosen evidence is dated after the ratings-file edition,
    #: i.e. it postdates the snapshot the file represents.
    newer_than_file_edition: bool = False

    @property
    def displayable(self) -> bool:
        return self.status in DISPLAYABLE_STATUSES

    @property
    def is_current(self) -> bool:
        """Only a ``current`` value may drive rating-based scope decisions."""
        return self.status == CURRENT

    def evidence_for(self, source: str) -> RatingEvidence | None:
        return next((e for e in self.evidence if e.source == source), None)

    def to_dict(self) -> dict[str, Any]:
        api = self.evidence_for(SOURCE_API)
        file = self.evidence_for(SOURCE_FILE)
        website = max(
            (e for e in self.evidence if e.source == SOURCE_WEBSITE),
            key=lambda e: (
                e.observed_on or date.min, e.publication_date or date.min, e.raw_value or e.value or "",
                str(e.inherited_flag),
            ),
            default=None,
        )
        return {
            "domain": self.domain,
            "status": self.status,
            "value": self.value if self.displayable else None,
            "source": self.source if self.displayable else None,
            "publication_date": (
                self.publication_date.isoformat()
                if self.publication_date and self.displayable else None
            ),
            "reason": self.reason,
            "newer_than_file_edition": self.newer_than_file_edition,
            "api_value": api.value if api else None,
            "api_raw_value": api.raw_value if api else None,
            "api_publication_date": _iso(api.publication_date) if api else None,
            "file_value": file.value if file else None,
            "file_publication_date": _iso(file.publication_date) if file else None,
            "file_inherited_flag": file.inherited_flag if file else None,
            "file_sha256": file.source_sha256 if file else None,
            "file_edition_date": _iso(file.edition_date) if file else None,
            "website_value": website.value if website else None,
            "website_raw_value": website.raw_value if website else None,
            "website_publication_date": _iso(website.publication_date) if website else None,
            "website_observed_on": _iso(website.observed_on) if website else None,
        }


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _is_inherited(ev: RatingEvidence, registration_date: date | None) -> bool:
    if ev.inherited_flag:
        return True
    return bool(
        registration_date and ev.publication_date and ev.publication_date < registration_date
    )


def _newer_than_edition(ev: RatingEvidence, file_edition: date | None) -> bool:
    return bool(file_edition and ev.publication_date and ev.publication_date > file_edition)


#: Deterministic tie-break between channels that publish the same value on the
#: same date, so evidence order never changes the result.
_SOURCE_ORDER = {SOURCE_FILE: 0, SOURCE_API: 1, SOURCE_WEBSITE: 2}


def _pick_newest(candidates: list[RatingEvidence], registration_date: date | None) -> tuple[RatingEvidence, bool]:
    """Newest dated candidate (order-independent) and whether it is inherited.

    Inheritance is reconciled across every candidate that publishes the same
    value on the same date: if any of them is flagged inherited or predates the
    registration, the result is inherited. Conflicting metadata resolves to the
    conservative answer.
    """
    dated = [e for e in candidates if e.publication_date]
    pool = dated or candidates
    newest = max((e.publication_date for e in dated), default=None)
    tied = [e for e in pool if e.publication_date == newest] if dated else pool
    chosen = min(tied, key=lambda e: (_SOURCE_ORDER.get(e.source, 9), e.source))
    same = [e for e in tied if e.value == chosen.value]
    return chosen, any(_is_inherited(e, registration_date) for e in same)


def _page_inheritance(observations: list[RatingEvidence], value: str | None, publication: date | None) -> bool | None:
    """The page's inheritance verdict for one rating value and publication.

    Only flags that describe that publication count: an explicit flag on a page
    stating the same publication date, or -- conservatively -- an undated page
    saying ``inherited``. An undated ``not inherited`` cannot clear anything,
    because nothing ties it to this publication. The most recently observed
    relevant flag wins; ``inherited`` wins a same-day tie. ``None`` when no page
    says anything about this publication.
    """
    relevant = [
        o for o in observations
        if o.value == value and o.inherited_flag is not None and (
            (publication is not None and o.publication_date == publication)
            or (o.publication_date is None and o.inherited_flag is True)
        )
    ]
    if not relevant:
        return None
    last = max(o.observed_on for o in relevant)
    return True in {o.inherited_flag for o in relevant if o.observed_on == last}


def _apply_page_flag(
    inherited: bool, page_flag: bool | None, publication: date | None, registration_date: date | None
) -> bool:
    """Combine the source-derived inheritance with a page verdict on the same publication.

    A page ``inherited`` always applies (conservative). A page ``not inherited``
    clears a source annotation only when the publication is on or after the
    registration: it cannot make a rating published before this registration
    existed into one this registration earned.
    """
    if page_flag is True:
        return True
    if page_flag is False:
        predates = bool(registration_date and publication and publication < registration_date)
        return predates
    return inherited


def _observation_applies(obs: RatingEvidence, others: list[RatingEvidence]) -> bool:
    """A page observation decides only if it postdates every competing value.

    Every candidate with a different value must be dated on or before the
    observation day; otherwise the observation may be stale (a later rating was
    published after it) or the timing cannot be established.
    """
    for e in others:
        if e.value == obs.value:
            continue
        if e.publication_date is None or e.publication_date > obs.observed_on:
            return False
    return True


def resolve_rating(
    evidence: Iterable[RatingEvidence],
    *,
    registration_date: date | None,
    domain: str = "overall",
) -> ResolvedRating:
    """Resolve one rating domain from every channel's evidence.

    Rules, in order:

    1. Only published values (Outstanding/Good/Requires improvement/Inadequate)
       are candidates. Sentinels and blanks are kept in ``evidence`` but never
       chosen.
    2. A dated CQC page observation showing *no* rating (``value=None``) makes
       the result ``unresolved`` unless a rating was published after it (then it
       is stale and kept only as evidence) or a later page observation shows a
       rating. An undated published value cannot be placed against it, so it
       is also ``unresolved``.
    3. A dated CQC page observation showing a rating is CQC's statement at that
       time: the most recently observed one decides the value and its inherited
       flag the status, but only when every competing value is dated on or
       before the observation. Same-day observations that disagree are
       ``unresolved``. When it confirms or restates a dated API/file value,
       that value's source and date are kept and inheritance is reconciled
       across all of it; an absent page flag never clears an inherited file
       flag or an earlier page's explicit flag on the same rating and
       publication, only an explicit flag does. Otherwise it is weighed by its
       publication date like any other candidate.
    4. No candidate -> ``none``.
    5. All candidates agree -> the most recently published one is chosen
       (ties broken by a fixed channel order); ``inherited`` if any candidate
       with that value and date predates the registration or is flagged
       inherited.
    6. Candidates disagree:
       * any undated candidate -> ``unresolved``;
       * an inherited candidate contradicted by a non-inherited one ->
         ``unresolved`` (the page may still show the inherited rating);
       * the newest publication date is shared by different values ->
         ``unresolved``;
       * otherwise the strictly newest value is ``current``.
    """
    items = tuple(evidence)
    file_ev = next((e for e in items if e.source == SOURCE_FILE), None)
    file_edition = file_ev.edition_date if file_ev else None

    def result(status: str, chosen: RatingEvidence | None, reason: str) -> ResolvedRating:
        return ResolvedRating(
            domain=domain,
            status=status,
            value=chosen.value if chosen else None,
            source=chosen.source if chosen else None,
            publication_date=chosen.publication_date if chosen else None,
            reason=reason,
            evidence=items,
            newer_than_file_edition=bool(chosen and _newer_than_edition(chosen, file_edition)),
        )

    candidates = [e for e in items if e.value is not None]

    observations = [e for e in candidates if e.source == SOURCE_WEBSITE and e.observed_on]
    absences = [e for e in items if e.source == SOURCE_WEBSITE and e.value is None and e.observed_on]
    if absences and candidates:
        absent = max(absences, key=lambda e: e.observed_on)
        if not any(o.observed_on > absent.observed_on for o in observations):
            published = [e.publication_date for e in candidates if e.source != SOURCE_WEBSITE]
            if not published or None in published or max(published) <= absent.observed_on:
                return result(
                    UNRESOLVED, None,
                    f"CQC location page observed {absent.observed_on.isoformat()} showed no rating, "
                    "after every published value",
                )
            # A rating published after the page check supersedes it; the check stays in evidence.

    if observations:
        newest_published = max(
            (e.publication_date for e in candidates if e.source != SOURCE_WEBSITE and e.publication_date),
            default=None,
        )
        if newest_published and newest_published > max(o.observed_on for o in observations):
            # Every page check predates the newest API/file publication, so none
            # of them can speak to it -- whether they agree, conflict or are one
            # of many. As with a negative check, keep them as evidence and
            # reconcile the published channels normally, including conflicts.
            candidates = [e for e in candidates if e.source != SOURCE_WEBSITE]
            observations = []

    if observations:
        latest_day = max(o.observed_on for o in observations)
        latest = [o for o in observations if o.observed_on == latest_day]
        if len({o.value for o in latest}) > 1:
            # Nothing orders same-day observations against each other.
            return result(
                UNRESOLVED, None,
                f"CQC location page observations on {latest_day.isoformat()} show different ratings",
            )
        chosen = max(latest, key=lambda e: (e.publication_date or date.min, _SOURCE_ORDER.get(e.source, 9)))
        others = [e for e in candidates if e.source != SOURCE_WEBSITE]
        if _observation_applies(chosen, others):
            note = f"CQC location page observed {chosen.observed_on.isoformat()}"
            confirming = [e for e in others if e.value == chosen.value and e.publication_date]
            newest_confirmed = max((e.publication_date for e in confirming), default=None)
            if confirming and (chosen.publication_date is None or chosen.publication_date <= newest_confirmed):
                # The page confirms (or restates) a dated published value: keep
                # that value's source and date, then read every page flag about
                # *that* publication (never one about another publication).
                picked, inherited = _pick_newest(confirming, registration_date)
                page_flag = _page_inheritance(observations, chosen.value, picked.publication_date)
                inherited = _apply_page_flag(inherited, page_flag, picked.publication_date, registration_date)
                return result(INHERITED if inherited else CURRENT, picked, f"Confirmed by {note}")
            page_flag = _page_inheritance(observations, chosen.value, chosen.publication_date)
            inherited = _apply_page_flag(
                _is_inherited(RatingEvidence(**{**chosen.__dict__, "inherited_flag": None}), registration_date),
                page_flag, chosen.publication_date, registration_date,
            )
            return result(INHERITED if inherited else CURRENT, chosen, f"{note} decides the current value")
        candidates = others + [chosen]

    if not candidates:
        return result(NONE, None, "No channel publishes a rating value")

    values = {e.value for e in candidates}
    if len(values) == 1:
        chosen, inherited = _pick_newest(candidates, registration_date)
        if inherited:
            return result(INHERITED, chosen, "Published before this registration or flagged inherited")
        return result(CURRENT, chosen, "All channels agree")

    if any(e.publication_date is None for e in candidates):
        return result(UNRESOLVED, None, "Channels disagree and at least one value is undated")

    inherited = [e for e in candidates if _is_inherited(e, registration_date)]
    if inherited and len(inherited) < len(candidates):
        return result(
            UNRESOLVED,
            None,
            "An inherited value is contradicted by a value earned under this registration",
        )

    newest = max(e.publication_date for e in candidates)
    at_newest = {e.value for e in candidates if e.publication_date == newest}
    if len(at_newest) > 1:
        return result(UNRESOLVED, None, "Different values share the newest publication date")

    chosen, inherited = _pick_newest(candidates, registration_date)
    return result(INHERITED if inherited else CURRENT, chosen, "Most recently published value across channels")


def evidence_from_provider_row(row: dict[str, Any], *, file_edition_date: date | None) -> list[RatingEvidence]:
    """Build overall-rating evidence from a ``care_providers`` row.

    Uses ``overall_rating``/``last_published_rating_date`` for the API channel
    and the migration-068 ``file_*`` columns for the file channel. The file's
    inherited flag is not stored in the table, so it is ``None`` here and the
    registration-date rule alone detects inheritance.
    """
    api_raw = row.get("overall_rating")
    out = [
        RatingEvidence(
            source=SOURCE_API,
            value=canonical_rating(api_raw),
            publication_date=row.get("last_published_rating_date"),
            raw_value=api_raw,
        )
    ]
    file_raw = row.get("file_overall_rating")
    if file_raw:
        out.append(
            RatingEvidence(
                source=SOURCE_FILE,
                value=canonical_rating(file_raw),
                publication_date=row.get("file_overall_rating_date"),
                source_sha256=row.get("file_rating_source_sha256"),
                edition_date=file_edition_date,
                raw_value=file_raw,
            )
        )
    return out
