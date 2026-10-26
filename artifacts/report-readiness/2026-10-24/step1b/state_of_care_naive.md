# State of Care benchmark

Closure logic: **naive**. Reference values as supplied in .warroom/REPORT_READINESS_BRIEF.md: ~13,500 homecare (Apr 2026), >4,500 supported living, large homes 23% of care homes holding 70% of beds. Not independently re-checked against the State of Care publication in this run.

| Metric | CQC reference | cqc_register_apr | caregist_now | caregist_apr | caregist_db_now |
|---|---:|---:|---:|---:|---:|
| care_homes | - | 14382 | 14756 | 14692 | 14896 |
| homecare | 13500 | 13507 (+7) | 13605 (+105) | 13574 (+74) | 14488 (+988) |
| supported_living | 4500 | 4574 (+74) | 4808 (+308) | 4794 (+294) | 5068 (+568) |
| large_home_share_of_homes | 0.23 | 0.2287 (-0.0013) | 0.2509 (+0.0209) | 0.245 (+0.015) | 0.2499 (+0.0199) |
| large_home_share_of_beds | 0.7 | 0.5006 (-0.1994) | 0.5315 (-0.1685) | 0.5241 (-0.1759) | 0.5315 (-0.1685) |
| care_homes_1-10 | - | 4145 | 4118 | 4139 | 4199 |
| care_homes_11-49 | - | 6946 | 6933 | 6951 | 6972 |
| care_homes_50+ | - | 3288 | 3702 | 3599 | 3722 |
| care_homes_unknown | - | 3 | 3 | 3 | 3 |

Gap in brackets = column value minus CQC reference.

## Movement, 12 months to export

- care_homes: 998 registrations, 832 registration endings, 832 confirmed closures (2025-10-21 to 2026-10-20); endings by class {'confirmed_closure': 832}
- homecare: 930 registrations, 1018 registration endings, 1018 confirmed closures (2025-10-21 to 2026-10-20); endings by class {'confirmed_closure': 1018}

## Limitations

- caregist_apr applies dormancy as at the export date; a service dormant in April but active by October (or the reverse) is misclassified.
- caregist_db_now cannot exclude dormant services: care_providers stores no dormancy flag.
- CareGist columns do not reduce dual registrations; only cqc_register_apr applies CQC's Primary ID rule.
- No earlier CareGist snapshot than the 20 Oct 2026 export is held, so April values are a reconstruction from registration/deregistration dates, not a stored snapshot.
