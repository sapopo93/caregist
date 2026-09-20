"""One corpus, both classification authorities.

``api/services/rating_states.py`` (Python) and
``db/migrations/061_provider_rating_state.sql`` (the executed migration) both
classify rating text. Two authorities that are only *supposed* to agree is
exactly the drift the reviewer found: ``'Excellent'``, ``'Suspended'`` and
``'Under review'`` came back ``'rated'`` through the payload classifier and
``'unknown'`` through the stored one.

Both sides are therefore driven over the same corpus, so a divergence is a test
failure rather than a disagreement between two green suites:

* :data:`CORPUS` -- values a stored ``overall_rating`` can hold, including the
  shapes the reviewed ``ELSE 'rated'`` catch-all got wrong. Consumed by
  ``tests/integration/test_migration_061_rating_state.py`` (the migration, run
  against real PostgreSQL) and by ``tests/test_rating_states.py`` (Python).
* :data:`NON_EMPTY_CORPUS` -- the values where the payload classifier
  (:func:`api.services.rating_states.assess_location_rating`) and the stored
  classifier (:func:`api.services.rating_states.classify_stored_rating`) must
  agree value for value. The empty/absent shapes are excluded because the two
  classifiers deliberately differ there, and that difference is asserted
  explicitly instead of being hidden: an empty *payload* field means the source
  publishes no current rating (``not_published``), while an empty *stored*
  column means storage says nothing about what the source published
  (``unknown``).
"""

from __future__ import annotations

#: Values a stored ``overall_rating`` can legitimately hold, plus the shapes that
#: made the reviewed ``ELSE 'rated'`` catch-all wrong.
CORPUS: tuple[str | None, ...] = (
    "Outstanding",
    "Good",
    "requires improvement",
    "INADEQUATE",
    "  Good  ",
    "Requires  improvement",
    "Not Yet Inspected",
    "not inspected",
    "Awaiting inspection",
    "No Published Rating",
    "Not published",
    "No rating",
    "Rating not published",
    "Inspected but not rated",
    "Not rated",
    "Unrated",
    "UNRATED",
    "Not applicable",
    "N/A",
    "n/a",
    "",
    "   ",
    None,
    # Unrecognised: neither a rating nor a known sentinel. Must not be 'rated'.
    "Suspended",
    "Pending",
    "Not registered",
    "Deregistered",
    "Under review",
    "??",
)

#: The corpus values where the payload classifier and the stored classifier are
#: the same authority: everything non-empty.
NON_EMPTY_CORPUS: tuple[str, ...] = tuple(
    value for value in CORPUS if isinstance(value, str) and value.strip()
)
