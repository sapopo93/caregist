# Workflow: Prometheus Metrics

CareGist exposes a `/metrics` endpoint in the standard Prometheus text format.
This document covers the scrape configuration and recommended alerting rules.

---

## Metrics Exposed

### Counters

| Metric | Labels | Description |
|---|---|---|
| `caregist_requests_total` | `method`, `endpoint`, `status` | Every HTTP request handled by the API |
| `caregist_rate_limit_rejections_total` | — | Requests rejected by the rate limiter |
| `caregist_webhook_failures_total` | — | Webhook delivery failures |

### Histograms

| Metric | Labels | Description |
|---|---|---|
| `caregist_request_duration_seconds` | `method`, `endpoint` | Latency per request; buckets 5 ms → 10 s |

### Gauges

| Metric | Description |
|---|---|
| `caregist_email_queue_depth` | Rows in `pending_emails` not yet sent |
| `caregist_pipeline_freshness_seconds` | Seconds since the new-registration pipeline last completed successfully |

---

## Prometheus Scrape Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: caregist_api
    scrape_interval: 30s
    scrape_timeout: 10s
    static_configs:
      - targets:
          - '<ec2-private-ip>:8000'   # Replace with actual EC2 private IP
    # Optional: basic relabelling to add environment context
    relabel_configs:
      - target_label: environment
        replacement: production
      - target_label: service
        replacement: caregist-api
```

Verify the endpoint manually:
```bash
curl http://localhost:8000/metrics | head -40
```

---

## Recommended Alerting Rules

Add to a `caregist.rules.yml` file loaded by your Prometheus / Alertmanager setup:

```yaml
groups:
  - name: caregist
    rules:

      # --- Email queue depth -----------------------------------------------
      - alert: CareGistEmailQueueHigh
        expr: caregist_email_queue_depth > 100
        for: 5m
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "CareGist email queue depth is high ({{ $value }} pending)"
          description: >
            The pending_emails queue has exceeded 100 rows for 5+ minutes.
            Check the flush-email-queue timer and Resend API status.
          runbook: https://github.com/sapopo93/caregist/blob/main/workflows/deploy-ec2.md

      # --- Pipeline freshness -----------------------------------------------
      - alert: CareGistPipelineStale
        expr: caregist_pipeline_freshness_seconds > 604800  # 7 days
        for: 1h
        labels:
          severity: critical
          team: ops
        annotations:
          summary: "CareGist new-registration pipeline has not run in > 7 days"
          description: >
            Pipeline freshness is {{ $value | humanizeDuration }}.
            Check caregist-feed-cycle.timer and caregist-pipeline-watchdog.timer.
          runbook: https://github.com/sapopo93/caregist/blob/main/workflows/deploy-ec2.md

      # --- Error rate -------------------------------------------------------
      - alert: CareGistHighErrorRate
        expr: >
          (
            rate(caregist_requests_total{status=~"5.."}[5m])
            /
            rate(caregist_requests_total[5m])
          ) > 0.05
        for: 2m
        labels:
          severity: critical
          team: ops
        annotations:
          summary: "CareGist API 5xx error rate > 5% ({{ $value | humanizePercentage }})"
          description: >
            More than 5% of API requests are returning 5xx status codes.
            Check Sentry at https://sentry.io and API logs via journalctl.
          runbook: https://github.com/sapopo93/caregist/blob/main/workflows/deploy-ec2.md

      # --- Rate-limit spike --------------------------------------------------
      - alert: CareGistRateLimitSpike
        expr: rate(caregist_rate_limit_rejections_total[5m]) > 10
        for: 2m
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "CareGist rate-limit rejections spiking ({{ $value | humanize }}/s)"
          description: >
            More than 10 rate-limit rejections per second for 2+ minutes.
            May indicate an abusive client or a misconfigured integration.

      # --- Webhook failures --------------------------------------------------
      - alert: CareGistWebhookFailures
        expr: increase(caregist_webhook_failures_total[10m]) > 5
        labels:
          severity: warning
          team: ops
        annotations:
          summary: "CareGist webhook failures: {{ $value }} in last 10 min"
          description: >
            Check webhook_delivery_log and verify subscriber endpoint health.
```

---

## Updating Pipeline Freshness from Tools

To keep `caregist_pipeline_freshness_seconds` accurate, push the gauge value from
within the pipeline script after a successful run. Example pattern (add to
`tools/run_new_registration_feed_cycle.py` if you want push-based updates):

```python
# Option A — push gateway (if you run a Prometheus Pushgateway)
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import time

registry = CollectorRegistry()
g = Gauge(
    "caregist_pipeline_freshness_seconds",
    "Seconds since last successful run",
    registry=registry,
)
g.set(0)  # just ran
push_to_gateway("http://localhost:9091", job="caregist_feed_cycle", registry=registry)
```

Alternatively, the API-side gauge can be set by an internal endpoint called by the
tool, or via a shared Redis key read by the `/metrics` scrape handler.

---

## Grafana Dashboard (starter)

Import the following panel queries into Grafana pointing at your Prometheus data source:

```
# Request rate (req/s)
rate(caregist_requests_total[1m])

# P95 latency
histogram_quantile(0.95, rate(caregist_request_duration_seconds_bucket[5m]))

# Error rate
rate(caregist_requests_total{status=~"5.."}[5m]) / rate(caregist_requests_total[5m])

# Email queue depth
caregist_email_queue_depth

# Pipeline freshness (hours)
caregist_pipeline_freshness_seconds / 3600
```
