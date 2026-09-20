"""Finding (1) read-path proof: no public read can serve a stale rating.

The reviewed revision classified an unfamiliar current-rating string as
``unknown`` (``classify_rating``) and then wrote no rating column at all
(``apply_rating_write_policy``), while every public read selected
``care_providers.overall_rating`` without consulting ``rating_state``
(``api/queries/providers.py``). A location whose current payload publishes
wording this build cannot read -- CQC does publish such wording ('Suspended',
'Under review') -- therefore kept being served the rating its *previous* payload
published, and the same stale value stayed reachable through the rating filter
and the rating facet.

Nothing in this module is mocked and no helper-level assertion is reused. Each
test applies the complete schema to a throwaway PostgreSQL database, runs the
real ingestion write path (``clean_location`` -> ``upsert_provider``), and then
reads the location back through the application's own HTTP endpoints: the real
router, its real SQL text and its real field serialiser, pointed at that
database. A reintroduced stale rating fails on the response body.

Every test carries a positive control -- the same location, while its payload
still publishes a readable rating -- so that "no rating was served" cannot pass
because the location was invisible to the read path, because the tier hid the
field, or because the row was never returned at all.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import psycopg2
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

import api.routers.providers as providers_router
from api.main import app
from api.middleware import rate_limit as rate_limit_module
from incremental_update import clean_location, upsert_provider
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


def _reset_rate_limit_windows() -> None:
    """Clear the in-memory plan windows, as ``tests/test_rate_limit.py`` does.

    The limiter is not what these tests are about, and its free-tier burst
    window is per client address, so a test that drives the public endpoint
    dozens of times would otherwise be refused rather than served.
    """
    rate_limit_module._burst_requests.clear()
    rate_limit_module._daily_counts.clear()
    rate_limit_module._rolling_7d_counts.clear()
    rate_limit_module._monthly_counts.clear()


@pytest.fixture(autouse=True)
def _clean_rate_limit_windows():
    _reset_rate_limit_windows()
    yield
    _reset_rate_limit_windows()

LOCATION_ID = "1-8880401"
PROVIDER_ID = "1-8880400"
LOCATION_NAME = "Ratings Serving House"

#: Rating text this build has no rule for. CQC publishes all three.
UNREADABLE_TEXTS = ("Excellent", "Suspended", "Under review")

#: Sentinel strings that are not ratings at all.
SENTINEL_TEXTS = ("Not Yet Inspected", "Unrated")

SEARCH_URL = "/api/v1/providers/search"


def _payload(*, overall_rating: object = None) -> dict:
    """A CQC location-detail payload shaped like the public API's.

    ``overall_rating`` sits inside ``currentRatings.overall.rating`` when given;
    ``None`` means the payload's overall block carries no rating value, and an
    empty string means the field is present but blank.
    """
    overall: dict[str, object] = {}
    if overall_rating is not None:
        overall["rating"] = overall_rating
    return {
        "locationId": LOCATION_ID,
        "providerId": PROVIDER_ID,
        "organisationType": "Location",
        "type": "Social Care Org",
        "name": LOCATION_NAME,
        "registrationStatus": "Registered",
        "registrationDate": "2007-04-05",
        "postalAddressTownCity": "Henley-on-Thames",
        "postalCode": "RG9 1AB",
        "region": "South East",
        "localAuthority": "Oxfordshire",
        "lastUpdated": "2026-09-01",
        "currentRatings": {"overall": overall},
    }


class _Location:
    """The real write path, plus the two ways a row can hold a rating."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def ingest(self, payload: dict) -> None:
        """``clean_location`` -> ``upsert_provider`` -- the production merge."""
        record = clean_location(payload)
        assert record is not None, "clean_location rejected a valid CQC payload"
        conn = psycopg2.connect(self._dsn)
        try:
            with conn, conn.cursor() as cur:
                action = upsert_provider(cur, record)
                assert action in {"inserted", "updated"}
        finally:
            conn.close()

    def write_rating_the_way_the_unmigrated_ingestion_did(self, rating: str) -> None:
        """The pre-061 write: the rating column, and nothing else.

        The un-migrated ingestion path has no ``rating_state`` to update, so a
        rating it writes leaves the state at whatever the last new-code run
        recorded. A guard that reads only the state cannot see this row; only
        the value actually in the column can be classified.
        """
        conn = psycopg2.connect(self._dsn)
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE care_providers SET overall_rating = %s WHERE id = %s",
                    (rating, LOCATION_ID),
                )
                assert cur.rowcount == 1, "the row under test was not there to update"
        finally:
            conn.close()


async def _location(fresh_db: str) -> _Location:
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
    finally:
        await conn.close()
    return _Location(fresh_db)


@asynccontextmanager
async def _public_api(dsn: str):
    """The real ASGI app, reading the real database through its own SQL."""
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    @asynccontextmanager
    async def _connection():
        async with pool.acquire() as conn:
            yield conn

    try:
        with patch.object(providers_router, "get_connection", _connection):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                yield client
    finally:
        await pool.close()


async def _search(client: AsyncClient, **params) -> dict:
    """Search the real endpoint with the limiter's in-process window reset.

    The free tier allows 2 requests per second, and these tests deliberately
    drive the real endpoint rather than mocking the limiter out. The window is
    reset with the same counters ``tests/test_rate_limit.py`` resets, so the
    limiter keeps enforcing and a 429 is still waited out, never accepted.
    """
    for _ in range(6):
        _reset_rate_limit_windows()
        response = await client.get(SEARCH_URL, params=params)
        if response.status_code == 429:
            await asyncio.sleep(1.05)
            continue
        assert response.status_code == 200, response.text
        return response.json()
    raise AssertionError("the public endpoint never served this search")


def _rows_named(body: dict) -> list[dict]:
    return [row for row in body["data"] if row.get("name") == LOCATION_NAME]


def _served_rating(body: dict) -> object:
    """The rating the public response actually carries for this location."""
    rows = _rows_named(body)
    assert len(rows) == 1, f"expected this location exactly once, got {rows}"
    return rows[0]["overall_rating"]


async def test_public_reads_serve_a_rating_the_current_payload_publishes(
    fresh_db: str,
) -> None:
    """Positive control -- passes with and without the fix.

    Without it, "no rating was served" below could pass because the location was
    never visible to the read path in the first place.
    """
    location = await _location(fresh_db)
    location.ingest(_payload(overall_rating="Good"))

    async with _public_api(fresh_db) as client:
        assert _served_rating(await _search(client, q=LOCATION_NAME)) == "Good"
        assert _served_rating(await _search(client, q=LOCATION_ID)) == "Good"
        assert (
            _served_rating(await _search(client, q=LOCATION_NAME, rating="good"))
            == "Good"
        )
        facets = (await _search(client, q=LOCATION_NAME, facets=True))["facets"]
        assert facets["ratings"] == {"Good": 1}


@pytest.mark.parametrize(
    "published",
    [
        pytest.param(UNREADABLE_TEXTS[0], id="unfamiliar-text-excellent"),
        pytest.param(UNREADABLE_TEXTS[1], id="unfamiliar-text-suspended"),
        pytest.param(UNREADABLE_TEXTS[2], id="unfamiliar-text-under-review"),
        pytest.param(None, id="rating-field-absent"),
        pytest.param("", id="rating-field-blank"),
        pytest.param(SENTINEL_TEXTS[0], id="sentinel-not-yet-inspected"),
        pytest.param(SENTINEL_TEXTS[1], id="sentinel-unrated"),
    ],
)
async def test_public_reads_never_serve_a_rating_the_current_payload_did_not_publish(
    fresh_db: str, published: object
) -> None:
    """A rating the current payload does not publish must not be readable."""
    location = await _location(fresh_db)

    # The location was rated, and the read path did serve that rating.
    location.ingest(_payload(overall_rating="Good"))
    async with _public_api(fresh_db) as client:
        assert _served_rating(await _search(client, q=LOCATION_NAME)) == "Good"

    # The current payload stops publishing a rating (or publishes wording this
    # build cannot read). The read path must serve no rating at all.
    location.ingest(_payload(overall_rating=published))

    async with _public_api(fresh_db) as client:
        assert _served_rating(await _search(client, q=LOCATION_NAME)) is None, (
            "text search served a rating the current payload did not publish"
        )
        assert _served_rating(await _search(client, q=LOCATION_ID)) is None, (
            "CQC-id lookup served a rating the current payload did not publish"
        )
        for wanted in ("good", "outstanding"):
            assert _rows_named(
                await _search(client, q=LOCATION_NAME, rating=wanted)
            ) == [], f"the rating={wanted} filter still matched a non-published rating"
        facets = (await _search(client, q=LOCATION_NAME, facets=True))["facets"]
        assert facets["ratings"] == {}, (
            "the rating facet advertised a rating no payload published"
        )


async def test_public_reads_mask_a_rating_left_by_a_writer_that_left_the_state_alone(
    fresh_db: str,
) -> None:
    """The un-migrated writer's rating, with the state still saying 'rated'.

    The recorded state was true when the last new-code run wrote it, so the row
    is not protected by the state alone: the value in the column is what decides
    whether anything may be rendered.
    """
    location = await _location(fresh_db)
    location.ingest(_payload(overall_rating="Good"))
    location.write_rating_the_way_the_unmigrated_ingestion_did("Suspended")

    async with _public_api(fresh_db) as client:
        assert _served_rating(await _search(client, q=LOCATION_NAME)) is None
        assert _served_rating(await _search(client, q=LOCATION_ID)) is None
        assert _rows_named(await _search(client, q=LOCATION_NAME, rating="suspended")) == []
        facets = (await _search(client, q=LOCATION_NAME, facets=True))["facets"]
        assert facets["ratings"] == {}
