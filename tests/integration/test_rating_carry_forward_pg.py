"""Real merge-path proof for the carried-forward rating defect (FIX 1).

The reviewed revision left the previous published rating in
``care_providers.overall_rating`` whenever the current payload published no
current overall rating, and the event classifier read that column *before* the
recorded ``rating_state``. The real transition (rated -> not currently rated)
was therefore suppressed, and a later genuine rating was reported as a movement
*from* the stale value.

This module drives the real path against a throwaway PostgreSQL database:

    clean_location(payload) -> upsert_provider(cur, record)

``upsert_provider`` is the production merge: it selects the existing row,
merges the cleaned record, builds the state events and writes them to
``trusted_event_ledger``. Nothing here reconstructs that merge by hand, so a
reintroduced carry-forward fails on the rows the database actually stored.
"""

from __future__ import annotations

import psycopg2
import pytest

from api.services.provider_state_events import RATING_STATUS_EVENT
from incremental_update import clean_location, upsert_provider
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio

LOCATION_ID = "1-8880001"
PROVIDER_ID = "1-8880000"
PUBLICATION_DATE = "2026-01-05"
#: A date on a payload that publishes no rating: not a rating date at all.
LATER_REPORT_DATE = "2026-06-30"
#: The date CQC published a historic rating with. It dates that rating only.
HISTORIC_DATE = "2025-06-01"

RATING_EVENT_TYPES = (RATING_STATUS_EVENT, "rating_changed")

ROW_COLUMNS = (
    "id",
    "provider_id",
    "name",
    "status",
    "overall_rating",
    "rating_state",
    "rating_state_source",
    "last_published_rating",
    "last_published_rating_date",
    "last_updated",
)


def _payload(*, overall_rating: object = None, report_date: str | None = PUBLICATION_DATE) -> dict:
    """A CQC location-detail payload shaped like the public API's.

    ``overall_rating`` sits inside ``currentRatings.overall.rating`` when given;
    ``None`` means the payload's overall block carries no rating value.
    """
    overall: dict[str, object] = {}
    if overall_rating is not None:
        overall["rating"] = overall_rating
    if report_date is not None:
        overall["reportDate"] = report_date
    return {
        "locationId": LOCATION_ID,
        "providerId": PROVIDER_ID,
        "organisationType": "Location",
        "type": "Social Care Org",
        "name": "Henley House",
        "registrationStatus": "Registered",
        "registrationDate": "2007-04-05",
        "postalAddressTownCity": "Henley-on-Thames",
        "postalCode": "RG9 1AB",
        "region": "South East",
        "localAuthority": "Oxfordshire",
        "lastUpdated": "2026-09-01",
        "currentRatings": {"overall": overall},
    }


def _historic_payload(*, historic_rating: str, historic_date: str) -> dict:
    """A payload publishing no current overall rating, with historic evidence only."""
    payload = _payload(overall_rating=None, report_date=None)
    payload["historicRatings"] = [
        {"overall": {"rating": historic_rating}, "date": historic_date}
    ]
    return payload


def _read_row(cur) -> dict:
    cur.execute(
        f"SELECT {', '.join(ROW_COLUMNS)} FROM care_providers WHERE id = %s",
        (LOCATION_ID,),
    )
    row = cur.fetchone()
    assert row is not None, "the real merge path did not write a care_providers row"
    return dict(zip(ROW_COLUMNS, row, strict=True))


def _read_rating_events(cur) -> list[dict]:
    """Rating-scoped rows the production merge wrote to trusted_event_ledger."""
    cur.execute(
        """
        SELECT event_type, old_value, new_value, metadata
          FROM trusted_event_ledger
         WHERE location_id = %s
           AND event_type = ANY(%s)
         ORDER BY id
        """,
        (LOCATION_ID, list(RATING_EVENT_TYPES)),
    )
    return [
        {
            "event_type": event_type,
            "old_value": old_value,
            "new_value": new_value,
            "metadata": metadata,
        }
        for event_type, old_value, new_value, metadata in cur.fetchall()
    ]


class _Ledger:
    """The real merge path plus the rows it wrote, readable per step."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def ingest(self, payload: dict) -> dict:
        record = clean_location(payload)
        assert record is not None, "clean_location rejected a valid CQC payload"
        conn = psycopg2.connect(self._dsn)
        try:
            with conn, conn.cursor() as cur:
                action = upsert_provider(cur, record)
                assert action in {"inserted", "updated"}
                self._row = _read_row(cur)
                self._events = _read_rating_events(cur)
        finally:
            conn.close()
        return self._row

    @property
    def row(self) -> dict:
        return self._row

    @property
    def events(self) -> list[dict]:
        return self._events


async def _ledger(fresh_db: str) -> _Ledger:
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
    finally:
        await conn.close()
    return _Ledger(fresh_db)


async def test_source_that_stops_publishing_a_rating_clears_the_column_and_records_the_transition(
    fresh_db: str,
) -> None:
    ledger = await _ledger(fresh_db)

    rated = ledger.ingest(_payload(overall_rating="Good"))
    assert rated["overall_rating"] == "Good"
    assert rated["rating_state"] == "rated"
    assert rated["last_published_rating"] == "Good"

    # The current payload publishes no current overall rating (historic evidence
    # only): the column must stop asserting one and the previous value must
    # survive as its own labelled evidence field, with its own date.
    current = ledger.ingest(
        _historic_payload(historic_rating="Good", historic_date=PUBLICATION_DATE)
    )
    assert current["overall_rating"] is None, (
        "a payload that publishes no current rating must never leave "
        "overall_rating asserting one"
    )
    assert current["rating_state"] == "not_published"
    assert current["rating_state_source"] == "pipeline"
    assert current["last_published_rating"] == "Good"
    assert current["last_published_rating_date"] is not None

    assert [event["event_type"] for event in ledger.events] == [RATING_STATUS_EVENT], (
        "the rated -> not-currently-rated transition must be recorded, not suppressed"
    )
    event = ledger.events[0]
    assert (event["old_value"], event["new_value"]) == ("rated", "not_published")
    assert event["metadata"]["rating_movement_eligible"] is False
    assert event["metadata"]["previous_rating"] == "Good"
    assert event["metadata"]["previous_rating_source"] == "care_providers.overall_rating"


async def test_a_later_genuine_rating_is_not_reported_as_a_false_movement(
    fresh_db: str,
) -> None:
    ledger = await _ledger(fresh_db)

    ledger.ingest(_payload(overall_rating="Good"))
    between = ledger.ingest(
        _historic_payload(historic_rating="Good", historic_date=PUBLICATION_DATE)
    )
    rated_again = ledger.ingest(_payload(overall_rating="Requires improvement"))
    assert rated_again["overall_rating"] == "Requires improvement"
    assert rated_again["rating_state"] == "rated"
    assert rated_again["last_published_rating"] == "Requires improvement"

    assert [event["event_type"] for event in ledger.events] == [
        RATING_STATUS_EVENT,
        RATING_STATUS_EVENT,
    ], "no rating_changed movement may be invented across the unrated interval"
    transition = ledger.events[1]
    assert (transition["old_value"], transition["new_value"]) == ("not_published", "rated")
    assert transition["metadata"]["rating_movement_eligible"] is False
    # The value being left behind is retained as labelled last-published
    # evidence, never re-asserted as a current rating.
    assert transition["metadata"]["previous_rating"] == "Good"
    assert (
        transition["metadata"]["previous_rating_source"]
        == "care_providers.last_published_rating"
    )
    assert transition["metadata"]["previous_rating_date"] is not None

    # A genuine movement between two published ratings is still reported.
    ledger.ingest(_payload(overall_rating="Inadequate"))
    movement = ledger.events[2]
    assert movement["event_type"] == "rating_changed"
    assert (movement["old_value"], movement["new_value"]) == (
        "Requires improvement",
        "Inadequate",
    )
    assert movement["metadata"]["rating_movement_eligible"] is True
    assert between["rating_state"] == "not_published"


async def test_sentinel_payload_also_clears_the_column_and_is_recorded(
    fresh_db: str,
) -> None:
    ledger = await _ledger(fresh_db)

    ledger.ingest(_payload(overall_rating="Inadequate"))
    sentinel = ledger.ingest(_payload(overall_rating="Not Yet Inspected"))

    assert sentinel["overall_rating"] is None
    assert sentinel["rating_state"] == "not_yet_inspected"
    assert sentinel["last_published_rating"] == "Inadequate"
    assert str(sentinel["last_published_rating_date"]) == PUBLICATION_DATE

    assert [event["event_type"] for event in ledger.events] == [RATING_STATUS_EVENT]
    event = ledger.events[0]
    assert (event["old_value"], event["new_value"]) == ("rated", "not_yet_inspected")
    assert event["metadata"]["destination_rating"] is None


async def test_absent_current_overall_rating_field_clears_the_column_and_is_recorded(
    fresh_db: str,
) -> None:
    """HIGH (`incremental_update.py:1137`): the field is *absent*, not sentinel.

    Which shape maps to which state, and why:

    * ``currentRatings`` present, ``overall`` present, ``rating`` key **absent**
      inside it -> the payload was read successfully and it publishes no current
      rating -> ``'not_published'``. Not a sentinel (CQC published no sentinel
      text), and *not* ``'unknown'``: ``'unknown'`` is reserved for payloads this
      build could not read, and a payload that was read fine must not leave an
      unreadable-looking state behind - that is what let the previous rating stay
      asserted.

    The later ``reportDate`` (``LATER_REPORT_DATE``) is deliberately different
    from the rated row's date: the date of a payload that publishes no rating is
    not a rating date, so it must not be attached to the retained ``Good``
    evidence either.
    """

    ledger = await _ledger(fresh_db)

    rated = ledger.ingest(_payload(overall_rating="Good"))
    assert rated["overall_rating"] == "Good"
    assert str(rated["last_published_rating_date"]) == PUBLICATION_DATE

    absent = ledger.ingest(_payload(overall_rating=None, report_date=LATER_REPORT_DATE))

    assert absent["overall_rating"] is None, (
        "a successfully read payload with no current overall rating must clear "
        "overall_rating, not leave the previous rating asserted"
    )
    assert absent["rating_state"] == "not_published", (
        "absent current rating is 'not_published'; 'unknown' is reserved for a "
        "payload this build could not read"
    )
    assert absent["rating_state_source"] == "pipeline"
    assert absent["last_published_rating"] == "Good"
    assert str(absent["last_published_rating_date"]) == PUBLICATION_DATE, (
        "the retained evidence keeps its own date; the wordless payload's "
        "reportDate must not be paired with it"
    )

    assert [event["event_type"] for event in ledger.events] == [RATING_STATUS_EVENT], (
        "the transition must be a recorded state event, not a rating_changed movement"
    )
    event = ledger.events[0]
    assert (event["old_value"], event["new_value"]) == ("rated", "not_published")
    assert event["metadata"]["rating_movement_eligible"] is False
    assert event["metadata"]["previous_rating"] == "Good"


async def test_blank_current_overall_rating_field_clears_the_column_and_is_recorded(
    fresh_db: str,
) -> None:
    """HIGH (`incremental_update.py:1137`): the field is *blank*, not absent.

    ``currentRatings.overall.rating`` is present but carries only whitespace.
    That is the same statement as an absent field - the source publishes no
    current rating - so it maps to ``'not_published'`` and clears the column, for
    the same reason: a payload that was read successfully is never ``'unknown'``
    and never leaves the previous rating asserted.
    """

    ledger = await _ledger(fresh_db)

    ledger.ingest(_payload(overall_rating="Good"))
    blank = ledger.ingest(_payload(overall_rating="   ", report_date=LATER_REPORT_DATE))

    assert blank["overall_rating"] is None, (
        "a blank current overall rating must clear overall_rating, not leave the "
        "previous rating asserted"
    )
    assert blank["rating_state"] == "not_published"
    assert blank["rating_state_source"] == "pipeline"
    assert blank["last_published_rating"] == "Good"
    assert str(blank["last_published_rating_date"]) == PUBLICATION_DATE

    assert [event["event_type"] for event in ledger.events] == [RATING_STATUS_EVENT], (
        "blank text is a state transition, not a rating movement"
    )
    event = ledger.events[0]
    assert (event["old_value"], event["new_value"]) == ("rated", "not_published")
    assert event["metadata"]["rating_movement_eligible"] is False


async def test_a_new_rating_with_no_new_report_date_does_not_keep_the_previous_date(
    fresh_db: str,
) -> None:
    """MEDIUM (`incremental_update.py:1130`), case one.

    The reviewer reproduced ``'Requires improvement'`` paired with the old
    ``'Good'`` date. The date on the row belongs to the value it was stored with;
    when the row's last-published rating is replaced by a rating the payload gave
    no date for, the old date must be cleared rather than reused.
    """

    ledger = await _ledger(fresh_db)

    rated = ledger.ingest(_payload(overall_rating="Good"))
    assert str(rated["last_published_rating_date"]) == PUBLICATION_DATE

    # A new published rating, and no report date anywhere in the payload.
    changed = ledger.ingest(_payload(overall_rating="Requires improvement", report_date=None))

    assert changed["overall_rating"] == "Requires improvement"
    assert changed["rating_state"] == "rated"
    assert changed["last_published_rating"] == "Requires improvement"
    assert changed["last_published_rating_date"] is None, (
        "the previous rating's date must be cleared, not paired with a different "
        "rating"
    )

    assert [event["event_type"] for event in ledger.events] == ["rating_changed"]
    movement = ledger.events[0]
    assert (movement["old_value"], movement["new_value"]) == (
        "Good",
        "Requires improvement",
    )


async def test_a_historic_rating_date_is_never_attached_to_a_different_current_rating(
    fresh_db: str,
) -> None:
    """MEDIUM (`incremental_update.py:1130`), case two.

    The reviewer reproduced ``'Outstanding'`` paired with a historic ``'Good'``
    date. A historic rating's date dates that historic rating; it is never the
    date of a different current rating, and there is no column that may claim it
    is.
    """

    ledger = await _ledger(fresh_db)

    ledger.ingest(_payload(overall_rating="Good"))

    payload = _payload(overall_rating="Outstanding", report_date=None)
    payload["historicRatings"] = [
        {"overall": {"rating": "Good"}, "date": HISTORIC_DATE},
    ]
    current = ledger.ingest(payload)

    assert current["overall_rating"] == "Outstanding"
    assert current["rating_state"] == "rated"
    assert current["last_published_rating"] == "Outstanding"
    assert current["last_published_rating_date"] is None, (
        "a historic 'Good' date must not be stored as the date of the current "
        "'Outstanding' rating"
    )
    assert HISTORIC_DATE not in {
        str(value) for value in current.values() if value is not None
    }
