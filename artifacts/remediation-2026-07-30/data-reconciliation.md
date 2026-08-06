# CQC data reconciliation

Observed on 30 July 2026 using read-only production queries and CQC's official
current-directory/API surfaces.

| Measure | Count | Unit / interpretation |
|---|---:|---|
| Historical quoted baseline | 55,818 | Older CareGist location-row count; not a current provider count |
| Database total | 56,743 | `care_providers` location rows, active and inactive |
| Database active | 56,742 | Active location rows |
| Unique location IDs | 56,743 | Distinct CQC location identifiers |
| Provider organisations | 36,944 | Distinct non-empty CQC provider organisation IDs represented by those locations |
| Named groups | 10,236 | CareGist group-name aggregation; not CQC provider organisations |
| Official directory publication | 56,976 | Active CQC location IDs in the 29 July 2026 CSV |
| New to CareGist baseline | 1,705 | Official active IDs absent from current database |
| Candidate deactivations | 1,471 | Database-active IDs absent from official active snapshot; must be detail-verified |
| Reconciliation union | 58,447 | IDs requiring presence comparison/detail handling, not a published provider total |

The values 55,818, 56,742 and 56,743 are therefore different snapshots or
different inclusion states of the same location-row unit. None is a count of
provider organisations or groups.

The production database's latest source update was 28 March 2026, so it is stale
relative to the official 29 July 2026 directory. The code can reconcile the gap,
but no paid/expanded staging import or production mutation was authorised in this
assessment. Freshness must remain degraded until a controlled import is approved
and completed.

Primary source: [CQC — Using CQC data](https://www.cqc.org.uk/about-us/transparency/using-cqc-data).
