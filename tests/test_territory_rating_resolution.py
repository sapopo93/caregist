"""Frozen audit acceptance checks: no network/database writes."""
import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from api.services.territory_rating import resolve_rating
from api.services.territory_brief import (
    PurchaseContext, generate_brief_from_rows, brief_to_csv, _provider_group_event,
    _location_events,
)
from api.services.territory_brief_render import render_brief_pdf

PACKET = Path(__file__).resolve().parents[1] / 'artifacts/rating-resolution/2026-10-29'
FIXTURES = json.loads((PACKET / 'fixtures.json').read_text())
UNRESOLVED = {'1-16491295796', '1-19886383752'}
CONFLICTS = {'1-152721284', '1-22160036426', '1-390976877', '1-552527797'}


@pytest.mark.parametrize('row', FIXTURES, ids=lambda r: r['locationId'])
def test_frozen_fixture(row):
    resolved = resolve_rating(row)
    ident = row['locationId']
    assert len(resolved['evidence']) >= 2
    assert resolved['evidence'][1]['value'] == row['file_overall_rating']
    assert resolved['evidence'][1]['sha256'] == row['file_rating_source_sha256']
    if ident in UNRESOLVED:
        assert resolved['status'] == 'unresolved' and resolved['value'] is None
        assert _provider_group_event(row, 'inadequate', as_of=date(2026,10,22)) is None
        assert _provider_group_event(row, 'not_yet_inspected', as_of=date(2026,10,22)) is None
    elif ident in CONFLICTS:
        assert resolved['value'] == row['file_overall_rating']
        assert resolved['publication_date'] >= row['file_overall_rating_date']
        assert 'CQC' in resolved['source']
    elif ident == '1-125730630':
        assert resolved['value'] == 'Requires improvement'
        assert resolved['source'] == 'CQC website'
        assert resolved['publication_date'] == '2026-10-13'
    elif row['file_overall_rating']:
        assert resolved['value'] == row['file_overall_rating']
        assert resolved['source'] == 'CQC ratings file'
        assert resolved['publication_date'] == row['file_overall_rating_date']
    else:
        assert resolved['status'] == 'unrated' and resolved['value'] is None


def test_conflicts_dates_and_api_only():
    row = {'currentRatings': {'overall': {'rating': 'Good'}, 'reportDate': '2026-10-29'}}
    assert resolve_rating(row)['source'] == 'CQC API'
    row.update(file_overall_rating='Inadequate', file_overall_rating_date='2025-01-01')
    assert resolve_rating(row)['value'] == 'Inadequate'
    assert resolve_rating(row)['publication_date'] == '2025-01-01'
    row['file_overall_rating_date'] = None
    assert resolve_rating(row)['source'] == 'CQC ratings file'
    assert resolve_rating(row)['publication_date'] is None


def test_file_observation_never_creates_history():
    row = {'locationId':'test', 'file_overall_rating':'Good',
           'file_overall_rating_date':'2026-10-22'}
    assert _location_events(row, window_start=date(2026,10,1),
                            window_end=date(2026,10,22), as_of=date(2026,10,22)) == []


def build_fixture_brief():
    rows = [{**r, 'localAuthority':'Fixture County', 'region':'Fixture Region',
             'registrationDate':'2026-10-20', 'providerId':r['locationId']+'-provider'} for r in FIXTURES]
    return generate_brief_from_rows(
        {'kind':'local_authority','name':'Fixture County','shortlist_target':30},
        PurchaseContext(order_reference='rating-fixtures', generated_at=datetime(2026,10,29,tzinfo=timezone.utc)),
        location_rows=rows, provider_names={r['providerId']:r['name'] for r in rows},
        locations_label='frozen-rating-audit-2026-10-22', providers_label='fixture-only',
        source_as_of=date(2026,10,22))


def test_output_consistency():
    brief = build_fixture_brief()
    exported = list(csv.DictReader(io.StringIO(brief_to_csv(brief))))
    assert len(exported) == len(brief.shortlist) == 30
    for row, org in zip(exported, brief.shortlist, strict=True):
        assert json.loads(row['rating_provenance_json']) == org.to_json()['rating_resolution']
        assert row['current_rating'] == (org.rating_resolution['value'] or '')
        assert row['rating_status'] == org.rating_resolution['status']
    assert render_brief_pdf(brief).startswith(b'%PDF')


def test_invalid_status_and_explicit_inherited():
    row = {'currentRatings': {'overall': {'rating': 'Good'}, 'reportDate':'2026-01-01'},
           'api_rating_status':'currnet', 'file_overall_rating':'Inadequate',
           'file_overall_rating_date':'2025-01-01'}
    assert resolve_rating(row)['status'] == 'unresolved'
    row.pop('file_overall_rating')
    row['api_rating_status'] = 'inherited'
    assert resolve_rating(row)['status'] == 'inherited'
    assert resolve_rating(row)['value'] is None


@pytest.mark.parametrize('changes', [{'registrationStatus':'Deregistered'}, {'dormancy':'Y'}])
def test_inactive_not_in_rating_scope(changes):
    row = {**FIXTURES[0], **changes, 'file_overall_rating':'Inadequate'}
    assert _provider_group_event(row, 'inadequate', as_of=date(2026,10,22)) is None


@pytest.mark.parametrize('file_date,web_date,expected_source,expected_value', [
    ('2026-01-01', None, 'CQC ratings file', 'Good'),
    ('2026-01-01', '2025-01-01', 'CQC ratings file', 'Good'),
    ('2026-01-01', '2026-02-01', 'CQC website', 'Inadequate'),
    (None, '2026-02-01', 'CQC website', 'Inadequate'),
])
def test_publication_precedence(file_date, web_date, expected_source, expected_value):
    row = {'file_overall_rating':'Good', 'file_overall_rating_date':file_date,
           'rating_website_evidence':{'value':'Inadequate', 'publication_date':web_date, 'status':'current'},
           'currentRatings':{'overall':{'rating':'Outstanding'}, 'reportDate':'2026-10-29'}}
    r = resolve_rating(row)
    assert r['source'] == expected_source and r['value'] == expected_value
    assert r['evidence'][0]['publication_date'] == '2026-10-29'


def test_undated_website_fills_gap_before_api():
    row = {'rating_website_evidence':{'value':'Good','status':'current'},
           'currentRatings':{'overall':{'rating':'Inadequate'},'reportDate':'2026-10-29'}}
    r = resolve_rating(row)
    assert r['source'] == 'CQC website' and r['publication_date'] is None
    from api.services.territory_rating import rating_label
    assert 'publication date unavailable' in rating_label(r)


@pytest.mark.parametrize('stamp', ['2026-01-01', None])
def test_unresolvable_publication_conflicts_keep_candidates(stamp):
    row = {'file_overall_rating':'Good','file_overall_rating_date':stamp,
           'rating_website_evidence':{'value':'Inadequate','publication_date':stamp,'status':'current'}}
    r = resolve_rating(row)
    assert r['status'] == 'unresolved' and r['value'] is None
    assert {e['value'] for e in r['evidence'][1:]} == {'Good','Inadequate'}


def test_undated_rating_group_never_invents_publication_date():
    row = {'locationId':'undated','providerId':'provider','name':'Undated fixture',
           'registrationStatus':'Registered','localAuthority':'Fixture County',
           'file_overall_rating':'Inadequate','lastInspection':{'date':'2025-01-01'}}
    brief = generate_brief_from_rows(
        {'kind':'local_authority','name':'Fixture County','shortlist_target':10},
        PurchaseContext(order_reference='undated',generated_at=datetime(2026,10,29,tzinfo=timezone.utc)),
        location_rows=[row],provider_names={'provider':'Fixture'},locations_label='test',
        providers_label='test',source_as_of=date(2026,10,22),provider_group='inadequate')
    org = brief.shortlist[0]
    assert 'publication date unavailable' in org.reason
    assert 'published 01 Jan 2025' not in org.reason
    assert 'Currently rated' not in org.reason
    exported = next(csv.DictReader(io.StringIO(brief_to_csv(brief))))
    assert exported['rating_evidence_date'] == ''
    assert exported['rating_source'] == 'CQC ratings file'
    assert org.to_json()['rating_resolution']['publication_date'] is None
    assert render_brief_pdf(brief).startswith(b'%PDF')
