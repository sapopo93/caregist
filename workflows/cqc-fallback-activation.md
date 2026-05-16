# Runbook: CQC Fallback Activation

**Applies to:** CQC data ingestion pipeline on `caregist.co.uk`
**Related runbooks:** [`workflows/run-feed-cycle.md`](run-feed-cycle.md)

---

## Background

Caregist normally ingests CQC provider changes via the `/changes/location` diff endpoint, which returns only providers changed since a given timestamp. This is efficient and fast.

When the `/changes/location` endpoint is unavailable, returning errors, or producing incomplete results, the system can fall back to a **list-scan**: iterating over the full CQC provider list page by page and comparing each record against the database. List-scan is complete but significantly slower — expect a full cycle to take several hours rather than minutes.

---

## When to Activate Fallback

Activate the list-scan fallback when:

- `/changes/location` is returning HTTP 5xx responses.
- `/changes/location` returns HTTP 200 but with an empty or malformed body.
- You suspect the diff feed missed changes (e.g. after a CQC-side incident that was later acknowledged).
- A scheduled feed cycle has not completed within twice the expected window and the logs show diff-endpoint errors.
- CQC publishes an advisory that the diff endpoint is temporarily unavailable.

---

## Pre-flight (5 min)

1. **Confirm the diff endpoint is actually failing** — do not switch to fallback unnecessarily:
   ```bash
   # Test the CQC diff endpoint directly
   curl -sv "https://api.service.nhs.uk/cqc/v1/changes/location?startTimestamp=<ISO_TIMESTAMP>" \
     -H "Ocp-Apim-Subscription-Key: <CQC_API_KEY>"
   # Expected: 200 with a JSON body containing a list of changes.
   # Failure: 5xx, 0 results when changes are expected, or malformed JSON.
   ```
2. **Check `pipeline_alert_log`** for any existing alert about diff endpoint failures:
   ```sql
   SELECT event, detail, created_at
   FROM pipeline_alert_log
   WHERE event LIKE '%cqc%' OR event LIKE '%feed%' OR event LIKE '%diff%'
   ORDER BY created_at DESC
   LIMIT 20;
   ```
3. **Check the feed cycle log**:
   ```bash
   tail -50 /var/log/caregist/feed-cycle.log
   ```
4. **Estimate list-scan duration** — a full list-scan typically takes 2–6 hours depending on the total provider count and API rate limits. Schedule it when low traffic is expected and you have time to monitor it.

---

## Activating the Fallback

### Method A: Environment variable flag (if implemented)

If the application supports a `CQC_FORCE_LIST_SCAN=true` environment variable:

1. SSH to EC2:
   ```bash
   ssh ubuntu@<EC2_IP>
   ```
2. Add the flag to `.env`:
   ```bash
   sudo nano /home/caregist/CareGist/.env
   # Add: CQC_FORCE_LIST_SCAN=true
   # Save and close.
   ```
3. Restart the service:
   ```bash
   sudo systemctl restart caregist-api
   ```
4. Trigger a feed cycle manually (see [`workflows/run-feed-cycle.md`](run-feed-cycle.md)):
   ```bash
   cd /home/caregist/CareGist
   source .venv/bin/activate
   python tools/run_feed_cycle.py --mode list-scan
   ```

### Method B: Direct script invocation with flag

If the feed runner accepts a CLI flag:

```bash
ssh ubuntu@<EC2_IP>
cd /home/caregist/CareGist
source .venv/bin/activate
python tools/run_feed_cycle.py --fallback-list-scan
```

> **Check the actual flag name in `tools/run_feed_cycle.py` or `workflows/run-feed-cycle.md` before running.**

### Method C: Code-level override (last resort)

If no flag exists, check `run-feed-cycle.md` for the feed runner's entry point and comment out the diff endpoint call, replacing it with the list-scan path. **Do not commit this change to main.** Revert after the recovery cycle completes.

---

## Monitoring Progress

List-scan produces log output as it pages through the CQC provider list. Monitor in real time:

```bash
tail -f /var/log/caregist/feed-cycle.log
```

Key log lines to look for:
- `Starting list-scan — total pages estimated: N` — confirms fallback mode is active.
- `Page N/M processed — N providers upserted, N unchanged` — progress indicator.
- `List-scan complete — N providers processed, N changes detected` — successful completion.
- Any `ERROR` or `CQCAPIError` lines — page-level failures (the runner should retry automatically).

Also monitor `pipeline_alert_log`:

```sql
SELECT event, detail, created_at
FROM pipeline_alert_log
ORDER BY created_at DESC
LIMIT 10;
```

---

## Validating Completeness Post-Recovery

After the list-scan completes, verify it ingested a realistic number of records:

```sql
-- Total active providers in database
SELECT COUNT(*) FROM providers WHERE active = TRUE;

-- Providers updated in the last cycle (adjust time window)
SELECT COUNT(*) FROM providers WHERE last_synced_at > NOW() - INTERVAL '8 hours';

-- Any providers that were NOT updated (possible gaps)
SELECT COUNT(*) FROM providers WHERE last_synced_at < NOW() - INTERVAL '8 hours' AND active = TRUE;
```

Cross-reference the total provider count against the [CQC API documentation](https://api.service.nhs.uk/cqc/v1/) or the CQC published statistics. If the database total is significantly lower than CQC's published total, the list-scan may have been interrupted — run it again.

Also check that provider changes are generating events correctly:

```sql
-- Recent change events created by the feed cycle
SELECT event_type, COUNT(*), MAX(created_at)
FROM provider_change_events
WHERE created_at > NOW() - INTERVAL '8 hours'
GROUP BY event_type
ORDER BY COUNT(*) DESC;
```

---

## Deactivating the Fallback

After the diff endpoint is confirmed healthy:

1. If Method A was used, remove `CQC_FORCE_LIST_SCAN=true` from `.env` and restart the service.
2. Run one more feed cycle in normal diff mode to confirm it works:
   ```bash
   python tools/run_feed_cycle.py
   # Should use the diff endpoint automatically.
   ```
3. Verify `feed-cycle.log` shows `Using diff mode — fetching changes since <timestamp>` (or similar).

---

## Recording the Incident

If the fallback was needed due to a CQC API failure, record it:

1. Add an entry to `pipeline_alert_log`:
   ```sql
   INSERT INTO pipeline_alert_log (event, detail, created_at)
   VALUES (
     'cqc_fallback_activated',
     'Diff endpoint unavailable from HH:MM UTC to HH:MM UTC. List-scan completed. N providers re-synced.',
     NOW()
   );
   ```
2. If the outage was >4 hours, file a post-mortem note at `docs/incidents/YYYY-MM-DD-cqc-diff-outage.md` using the template in [`workflows/incident-response.md`](incident-response.md).

---

## Escalation

If the list-scan fails to complete after two attempts, or if the CQC API is returning errors for both the diff endpoint and the list endpoint:

- Check the [CQC API status](https://api.service.nhs.uk/cqc/v1/) and any CQC developer advisories.
- Contact the CQC API support team if the outage is prolonged.
- Escalate internally with the full content of `feed-cycle.log` and the output of the pipeline alert log query.
