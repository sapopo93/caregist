"""Current-state rating evidence. Never supplies rating-change history.

Evidence is pinned into a Brief source edition; no mutable directory joins or
network requests are made while generating an order. Dates mean publication,
not retrieval. `current` describes the supplied evidence, not a live guarantee.
"""
from datetime import date

NUMERICAL = {'Outstanding', 'Good', 'Requires improvement', 'Inadequate'}
VERSION = 1
FILE_HASH = 'aba66fd8ca207828a4f6325e7329d98eec3b82aee12a0bfdbceddd58da0c59cd'


def publication(value):
    try:
        return date.fromisoformat(str(value)[:10]).isoformat() if value else None
    except ValueError:
        return None


def resolve_rating(row):
    current = row.get('currentRatings') or {}
    if not isinstance(current, dict):
        current = {}
    overall = current.get('overall') or {}
    if not isinstance(overall, dict):
        overall = {}
    api = dict(source='CQC API', value=overall.get('rating'),
               publication_date=publication(current.get('reportDate') or overall.get('reportDate') or overall.get('date')),
               edition=row.get('source_edition'), sha256=row.get('source_snapshot_sha256'),
               url=row.get('source_url'), status=row.get('api_rating_status', overall.get('status', 'current')))
    file_hash = row.get('file_rating_source_sha256')
    file = dict(source='CQC ratings file', value=row.get('file_overall_rating'),
                publication_date=publication(row.get('file_overall_rating_date')),
                edition=('CQC download edition 2 October 2026; data cutoff unverified'
                         if file_hash == FILE_HASH else row.get('file_rating_edition')),
                sha256=file_hash, url=row.get('file_rating_source'),
                status=row.get('file_rating_status', 'current'))
    website = row.get('rating_website_evidence')
    evidence = [api, file]
    if website:
        evidence.append({**website, 'source': 'CQC website',
                         'publication_date': publication(website.get('publication_date'))})
    numerical = [e for e in evidence if e.get('value') in NUMERICAL]
    result = dict(contract_version=VERSION, value=None, publication_date=None,
                  source=None, status='unrated', evidence=evidence,
                  reason='No numerical location overall rating in supplied evidence')
    if any(e.get('status') not in {'current', 'inherited', 'unresolved', 'unrated'} for e in evidence):
        return {**result, 'status': 'unresolved', 'reason': 'Unsupported evidence status'}
    if any(e.get('value') in NUMERICAL and e.get('status') == 'unrated' for e in evidence):
        return {**result, 'status': 'unresolved', 'reason': 'Numerical evidence has unrated status'}
    # A provider/context conflict cannot be resolved by sorting publication dates.
    if any(e.get('status') == 'unresolved' for e in evidence):
        return {**result, 'status': 'unresolved', 'reason': 'Current-provider evidence is unresolved'}
    eligible = [e for e in numerical if e.get('status') == 'current']
    if not eligible:
        return {**result, 'status': 'inherited' if numerical else 'unrated'}
    # Different values require comparable publication dates on every candidate.
    values = {e['value'] for e in eligible}
    if len(values) > 1 and any(not e.get('publication_date') for e in eligible):
        return {**result, 'status': 'unresolved', 'reason': 'Conflicting values with missing publication dates'}
    newest = max((e.get('publication_date') or '' for e in eligible))
    latest = [e for e in eligible if (e.get('publication_date') or '') == newest]
    if len({e['value'] for e in latest}) > 1:
        return {**result, 'status': 'unresolved', 'reason': 'Conflicting values at the same publication date'}
    # Co-equal sources are labelled together; no hidden API/file tie-break.
    return {**result, 'value': latest[0]['value'], 'publication_date': newest or None,
            'source': ' + '.join(e['source'] for e in latest), 'status': 'current',
            'reason': 'Newest comparable current-provider publication in supplied evidence'}


def rating_scope_eligible(row):
    return (str(row.get('registrationStatus') or '').strip().casefold() == 'registered'
            and not str(row.get('dormancy') or '').strip().upper().startswith('Y'))


def rating_label(resolution):
    return (f"{resolution['value'] or resolution['status']} [{resolution['status']}]; "
            f"{resolution['source'] or 'no accepted current source'}; "
            f"published {resolution['publication_date'] or 'date unavailable'}")
