# CQC Data Quality Report – New Providers (1 Jan 2026 – 28 Apr 2026)

**Generated:** 2026-04-28T10:26:56.917089
**Total records harvested:** 691

## 1. Coverage per field

| Field | Filled | Coverage % |
|-------|--------|------------|
| providerId | 691 | 100.0% |
| legalName | 691 | 100.0% |
| registrationDate | 691 | 100.0% |
| fullAddress | 691 | 100.0% |
| primaryServiceType | 691 | 100.0% |
| totalNumberOfLocations | 691 | 100.0% |
| ownershipStructure | 691 | 100.0% |
| latestInspectionRating | 691 | 100.0% |
| cqcRegistrationStatus | 691 | 100.0% |
| postalCode | 691 | 100.0% |
| region | 690 | 99.9% |
| localAuthority | 690 | 99.9% |
| mainPhoneNumber | 679 | 98.3% |
| registeredManagerName | 548 | 79.3% |
| companiesHouseNumber | 513 | 74.2% |
| website | 354 | 51.2% |
| tradingNames | 0 | 0.0% |
| companyIncorporationDate | 0 | 0.0% |
| companyStatus | 0 | 0.0% |
| directorNames | 0 | 0.0% |

## 2. Geographic distribution

### By Region (top 10)

| Region | Count |
|--------|-------|
| London | 137 |
| South East | 115 |
| North West | 97 |
| East | 89 |
| West Midlands | 83 |
| East Midlands | 62 |
| Yorkshire & Humberside | 49 |
| South West | 41 |
| North East | 16 |
| Wales | 1 |

### By Local Authority (top 10)

| Local Authority | Count |
|-----------------|-------|
| Essex | 30 |
| Hertfordshire | 27 |
| Hampshire | 26 |
| Birmingham | 24 |
| Kent | 17 |
| Westminster | 17 |
| Lancashire | 17 |
| Manchester | 15 |
| Surrey | 14 |
| Cheshire West and Chester | 12 |

## 3. Service type distribution (top 10)

| Service Type | Count |
|--------------|-------|
| Dentists | 216 |
| Independent consulting doctors | 98 |
| Community based adult social care services | 97 |
| Residential social care | 83 |
| Community health - NHS & Independent | 36 |
| GP Practices | 32 |
| Acute hospital - Independent specialist | 27 |
| Independent Healthcare Org | 19 |
| Primary Dental Care | 18 |
| Social Care Org | 17 |

## 4. Registration month distribution

| Month | Count |
|-------|-------|
| 2026-01 | 142 |
| 2026-02 | 176 |
| 2026-03 | 240 |
| 2026-04 | 133 |

## 5. Ownership structure distribution

| Ownership | Count |
|-----------|-------|
| Independent / Small group | 534 |
| partnership | 88 |
| Individual proprietor | 60 |
| Small-medium group | 9 |

## 6. Missing-data hotspots

- **tradingNames**: 0.0% (0/691) – significant gap
- **companyIncorporationDate**: 0.0% (0/691) – significant gap
- **companyStatus**: 0.0% (0/691) – significant gap
- **directorNames**: 0.0% (0/691) – significant gap

## 7. Anomalies & API limitations

- 1 providers have zero linked locations (may indicate pending registrations or data lag).
- 178 providers lack a Companies House number.
- Companies House enrichment failed for 513 of 513 attempts (likely API auth required).

## 8. Methodology notes

- **Primary source:** CQC Public API (`api.service.cqc.org.uk`) plus local snapshot `_providers_detail.ndjson` (dated 2026-02-24).
- **API fetches:** 739 missing provider IDs scanned; 739 detail records retrieved; 432 fell inside the target window.
- **Companies House:** Attempted via `api.company-information.service.gov.uk` without an API key. All requests returned 401 / auth errors. Enrichment limited to `companiesHouseNumber` already present in CQC data.
- **Location counts:** Derived from `provider.locationIds` array in CQC provider detail. Cross-referenced with `_locations_detail.ndjson` for service-type enrichment.
- **Date window:** registrationDate >= 2026-01-01 and <= 2026-04-28.
