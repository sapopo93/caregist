# State of Care benchmark

Closure logic: **classified**. Reference values as supplied in .warroom/REPORT_READINESS_BRIEF.md: ~13,500 homecare (Apr 2026), >4,500 supported living, large homes 23% of care homes holding 70% of beds. Not independently re-checked against the State of Care publication in this run.

| Metric | CQC reference | cqc_register_apr | caregist_now | caregist_apr | caregist_db_now |
|---|---:|---:|---:|---:|---:|
| care_homes | - | 14702 | 14756 | 14692 | 14898 |
| homecare | 13500 | 13507 (+7) | 13605 (+105) | 13574 (+74) | 14489 (+989) |
| supported_living | 4500 | 4574 (+74) | 4808 (+308) | 4794 (+294) | 5068 (+568) |
| large_home_share_of_homes | 0.23 | 0.2432 (+0.0132) | 0.2509 (+0.0209) | 0.245 (+0.015) | 0.2499 (+0.0199) |
| large_home_share_of_beds | 0.7 | 0.5216 (-0.1784) | 0.5315 (-0.1685) | 0.5241 (-0.1759) | 0.5315 (-0.1685) |
| care_homes_1-10 | - | 4145 | 4118 | 4139 | 4201 |
| care_homes_11-49 | - | 6979 | 6933 | 6951 | 6972 |
| care_homes_50+ | - | 3575 | 3702 | 3599 | 3722 |
| care_homes_unknown | - | 3 | 3 | 3 | 3 |

Gap in brackets = column value minus CQC reference.

## Movement, 12 months to export

- care_homes: 1001 registrations, 835 registration endings, 250 confirmed closures (2025-10-17 to 2026-10-16); endings by class {'confirmed_closure': 250, 'dormant': 51, 're_registration': 509, 'unresolved': 25}
- homecare: 938 registrations, 1027 registration endings, 442 confirmed closures (2025-10-17 to 2026-10-16); endings by class {'confirmed_closure': 442, 'dormant': 455, 're_registration': 120, 'unresolved': 10}

## Limitations

- caregist_apr applies dormancy as at the export date; a service dormant in April but active by October (or the reverse) is misclassified.
- caregist_db_now cannot exclude dormant services: care_providers stores no dormancy flag.
- CareGist columns do not reduce dual registrations; only cqc_register_apr applies CQC's Primary ID rule.
- No earlier CareGist snapshot than the 20 Oct 2026 export is held, so April values are a reconstruction from registration/deregistration dates, not a stored snapshot.
