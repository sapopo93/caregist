"""Build a bounded, source-dated territory review pack. No production writes."""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.titles, self.skip, self.in_title = [], [], 0, False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.in_title:
                self.titles.append(data)

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'source'
EDITION = '2026-09-01'
RETRIEVED = '2026-09-08'
MONTHLY = SOURCE / 'converted/2026-09-01-active-locations-HSCA_Active_Locations.csv'
WEEKLY = SOURCE / '2026-09-02-directory.csv'
URLS = {
    '2026-09-01-active-locations.ods': 'https://www.cqc.org.uk/system/files/2026-09/01_September_2026_HSCA_Active_Locations.ods',
    '2026-09-02-directory.csv': 'https://www.cqc.org.uk/system/files/2026-09/02_september_2026_CQC_directory.csv',
}


def iso(value):
    return datetime.strptime(value, '%d/%m/%Y').date().isoformat() if value else ''


def safe(value):
    text = str(value)
    return "'" + text if text.startswith(('=', '+', '-', '@')) else text


def save_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: safe(v) for k, v in row.items()} for row in rows)


def norm(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def check_page(row):
    folder = SOURCE / 'location-pages'
    folder.mkdir(exist_ok=True)
    path = folder / (row['location_id'] + '.html')
    try:
        if path.exists():
            body = path.read_bytes()
            status, url = 200, row['cqc_url']
        else:
            req = urllib.request.Request(row['cqc_url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                body = response.read()
                status, url = response.status, response.url
            path.write_bytes(body)
        parser = PageText()
        parser.feed(body.decode('utf-8', errors='replace'))
        text = ' '.join(parser.parts)
        title = ' '.join(parser.titles)
        name_seen = norm(row['location_name']) in norm(text)
        archived = bool(re.search(r'Archived:|This service was archived|This location was archived', text, re.I))
        result = {
            'location_id': row['location_id'], 'url': url, 'http_status': status,
            'checked_at': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            'sha256': hashlib.sha256(body).hexdigest(), 'title': title,
            'location_name_found': name_seen, 'archived_notice_found': archived,
            'result': 'MATCH' if status == 200 and name_seen and not archived else 'REVIEW',
        }
    except Exception as exc:
        result = {'location_id': row['location_id'], 'url': row['cqc_url'], 'result': 'ERROR', 'error': str(exc)}
    return result


def main():
    with MONTHLY.open(encoding='utf-8-sig', newline='') as f:
        monthly = list(csv.DictReader(f))
    assert len({r['Location ID'] for r in monthly}) == len(monthly)
    with WEEKLY.open(encoding='utf-8-sig', newline='') as f:
        raw = list(csv.reader(f))
    assert '02 September 2026' in raw[2][0]
    header_i = next(i for i, r in enumerate(raw) if 'CQC Location ID (for office use only)' in r)
    weekly = [dict(zip(raw[header_i], r)) for r in raw[header_i + 1:] if any(r)]
    weekly_by = {r['CQC Location ID (for office use only)']: r for r in weekly}
    assert len(weekly_by) == len(weekly)
    counts_all = Counter(r['Provider ID'] for r in monthly if r['Service type - Domiciliary care service'] == 'Y' and r['Dormant (Y/N)'] == 'N')
    records = []
    for source_row, r in enumerate(monthly, start=2):
        if r['Location Local Authority'] not in ('Birmingham', 'Solihull') or r['Service type - Domiciliary care service'] != 'Y' or r['Dormant (Y/N)'] != 'N':
            continue
        w = weekly_by.get(r['Location ID'])
        assert w, ('missing_weekly_id', r['Location ID'])
        assert w['CQC Provider ID (for office use only)'] == r['Provider ID']
        assert w['Local authority'] == r['Location Local Authority']
        services = [k.removeprefix('Service type - ') for k, v in r.items() if k.startswith('Service type - ') and v == 'Y']
        bands = [k.removeprefix('Service user band - ') for k, v in r.items() if k.startswith('Service user band - ') and v == 'Y']
        records.append({
            'location_id': r['Location ID'], 'location_name': r['Location Name'],
            'provider_id': r['Provider ID'], 'provider_name': r['Provider Name'],
            'local_authority': r['Location Local Authority'], 'postcode': r['Location Postal Code'],
            'registration_date': iso(r['Location HSCA start date']),
            'rating_as_published': r['Location Latest Overall Rating'],
            'rating_publication_date': iso(r['Publication Date']),
            'inherited_rating': r['Inherited Rating (Y/N)'],
            'service_types': '; '.join(services), 'service_user_bands': '; '.join(bands),
            'supported_living': 'Y' if 'Supported living service' in services else 'N',
            'provider_country_domiciliary_locations': counts_all[r['Provider ID']],
            'provider_territory_locations': 0, 'cqc_url': w['Location URL'],
            'provider_website': r['Provider Web Address'],
            'source_edition': EDITION, 'weekly_crosscheck_edition': '2026-09-02',
            'source_retrieved_date': RETRIEVED, 'monthly_source_row': source_row,
        })
    territory_count = Counter(r['provider_id'] for r in records)
    for r in records:
        r['provider_territory_locations'] = territory_count[r['provider_id']]
    groups = defaultdict(list)
    for r in records:
        groups[r['provider_id']].append(r)
    # Distinct review routes, not a demand score: coordinate multi-location accounts,
    # then inspect the newest single-location registrations. No buyer agreement claimed.
    multi = sorted((p for p, rs in groups.items() if len(rs) > 1), key=lambda p: (-len(groups[p]), groups[p][0]['provider_name']))
    chosen = [(p, 'Coordinate local locations') for p in multi[:15]]
    used = {p for p, _ in chosen}
    new = sorted((p for p in groups if p not in used), key=lambda p: (max(r['registration_date'] for r in groups[p]), p), reverse=True)
    chosen += [(p, 'Review recent registration') for p in new[:25 - len(chosen)]]
    shortlist = []
    for rank, (p, route) in enumerate(chosen, start=1):
        locations = sorted(groups[p], key=lambda r: (r['registration_date'], r['location_id']), reverse=True)
        rep = locations[0]
        authorities = ', '.join(sorted({r['local_authority'] for r in locations}))
        services = 'Domiciliary care + supported living' if any(r['supported_living'] == 'Y' for r in locations) else 'Domiciliary care'
        if route == 'Coordinate local locations':
            fact = f"{len(locations)} non-dormant domiciliary locations in {authorities} share this provider ID; {rep['provider_country_domiciliary_locations']} appear across England."
            reason = f"Assign one account owner to review {rep['provider_name']} across these {len(locations)} local locations before splitting research by branch."
            question = f"For {rep['location_name']} and the other local locations, is supplier selection handled by the provider or each location?"
        else:
            fact = f"{rep['location_name']} in {rep['local_authority']} records a registration date of {rep['registration_date']}; {rep['provider_country_domiciliary_locations']} domiciliary location(s) share this provider ID across England."
            reason = f"Check whether {rep['location_name']} belongs in the buyer's account list and whether the published service mix fits the buyer's staffing specialisms."
            question = f"Is {rep['location_name']} operating the listed service mix, and how does it source its workforce?"
        if any(r['supported_living'] == 'Y' for r in locations):
            question += ' Confirm whether separate supported-living and homecare staffing arrangements apply.'
        shortlist.append({
            'review_order': rank, 'review_route': route, 'provider_name': rep['provider_name'], 'provider_id': p,
            'representative_location': rep['location_name'], 'location_id': rep['location_id'],
            'authorities': authorities, 'local_locations': len(locations),
            'england_domiciliary_locations': rep['provider_country_domiciliary_locations'],
            'service_mix': services, 'published_fact': fact, 'reason_for_review': reason,
            'qualification_question': question,
            'uncertainty': 'No vacancy, staffing shortage, purchasing budget or buying intent is established. Source updates may lag.',
            'cqc_url': rep['cqc_url'], 'all_local_location_ids': '; '.join(r['location_id'] for r in locations),
            'source_edition': EDITION, 'web_check_date': '', 'web_check_result': '',
        })
    assert len(shortlist) == len({r['provider_id'] for r in shortlist}) == 25
    reps = [{**r, 'location_name': r['representative_location']} for r in shortlist]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(check_page, reps))
    checks_by = {r['location_id']: r for r in checks}
    for r in shortlist:
        c = checks_by[r['location_id']]
        r['web_check_date'] = c.get('checked_at', '')[:10]
        r['web_check_result'] = c['result']
    records.sort(key=lambda r: (r['local_authority'], r['provider_name'], r['location_id']))
    metadata = {
        'source_edition': EDITION, 'retrieved_date': RETRIEVED, 'source_rows': len(monthly),
        'weekly_source_rows': len(weekly), 'qualifying_locations': len(records),
        'distinct_providers': len(groups), 'authorities': dict(Counter(r['local_authority'] for r in records)),
        'multi_location_providers': len(multi), 'shortlist_providers': len(shortlist),
        'routes': dict(Counter(r['review_route'] for r in shortlist)),
        'web_checks': dict(Counter(r['result'] for r in checks)),
        'supported_living_locations': sum(r['supported_living'] == 'Y' for r in records),
        'ratings': dict(Counter(r['rating_as_published'] or 'Not supplied' for r in records)),
        'source_manifest': [{
            'file': name, 'url': url, 'http_status': 200,
            'retrieved_at': datetime.fromtimestamp((SOURCE / name).stat().st_mtime, timezone.utc).isoformat(),
            'bytes': (SOURCE / name).stat().st_size,
            'sha256': hashlib.sha256((SOURCE / name).read_bytes()).hexdigest(),
        } for name, url in URLS.items()],
        'limits': 'Current published editions, not real-time state. No full history or demand inference. Selection criteria are illustrative for a homecare staffing buyer, not yet buyer-agreed.',
    }
    (BASE / 'pack-data.json').write_text(json.dumps({'metadata': metadata, 'dataset': records, 'shortlist': shortlist, 'web_checks': checks}, indent=2))
    save_csv(BASE / 'territory-dataset.csv', records)
    save_csv(BASE / 'shortlist-25.csv', shortlist)
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
