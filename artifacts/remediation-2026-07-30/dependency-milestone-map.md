# Dependency and milestone map

| Seq | Required outcome | Implemented evidence | Exit condition |
|---:|---|---|---|
| 1 | Remove `quality_score` misuse | `data_completeness_score/tier`, migration 038, ranking and sample-copy corrections | Active code uses completeness only for record completeness; CQC rating drives care-quality filters |
| 2 | Reconcile CQC ingestion | Official-directory discovery, validated full-snapshot fallback, detail verification and atomic abort | No partial baseline mutation; source failure records failed run |
| 3 | Publish watermark/freshness | Migration 039, health service, `/health/freshness`, `/data-status` | Source publication and ingestion times are distinct and SLA state is explicit |
| 4 | Reconcile counts/units | `data-reconciliation.md`, pipeline health dimensions | Location rows, active locations, provider organisations and named groups never share one label |
| 5 | Repair routes | Provider/region/service/city and sharded sitemap fixes | Missing entities return real 404; sitemap base and shard bounds are stable |
| 6 | Canonicalise taxonomy | Shared JSON registry, Python/TypeScript exact-alias mapping | 31 canonical services and 57 observed aliases resolve deterministically |
| 7 | Reliable events | Migration 040 and deterministic provider state event service | Registration, rating, status, ownership and group movement dedupe on stable identity |
| 8 | E2E controlled workflows | Monitor/digest/export/webhook tests with mocked delivery and dry-run boundaries | No external delivery in tests; idempotency and delivery logs verified |
| 9 | Provider authority | Migrations 041–042, verified-account binding, evidence fingerprints, legacy-proof removal and independent moderation | No activation without current identity + authority evidence and a separate moderator |
| 10 | Security review | `security-review.md`, dependency upgrade, remote-media/intake gates, output escaping | Production dependency audit has no known vulnerability; dangerous mutations fail closed |
| 11 | Legal/governance blockers | Controlled terms/privacy copy, retention enforcement, UK baseline and blocker register | Unknowns are explicit, assigned to a gate and cannot silently activate features |
| 12 | Human Gate 1 briefs | Three briefs in this directory | Human decides scope/entity/budget; briefs themselves cause no external action |

Dependencies are sequential: later workflow evidence does not waive an earlier
data, security or governance condition.
