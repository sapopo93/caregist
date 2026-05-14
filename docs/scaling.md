# Scaling Caregist Beyond One Worker

This document explains the current capacity profile, the signals that indicate you need
to scale, and the concrete steps to reintroduce Redis when that moment arrives.

---

## 1. Current capacity profile

Caregist runs a **single uvicorn worker** managed by PM2 in fork mode on a single EC2 t3.medium.

Rate limiting is implemented as **in-memory token buckets** (sliding-window burst + DB-backed
daily/7-day/monthly quotas). Because there is exactly one worker process, every request goes
through the same bucket — there is no per-worker drift, no Redis dependency, and no additional
ops surface to maintain.

This configuration is intentional. At launch traffic volumes a t3.medium with one uvicorn
worker has headroom to spare. The simplicity is the feature.

A startup assertion in `api/middleware/rate_limit.py` and a fail-fast check in `api/main.py`
will raise a `RuntimeError` at boot if `UVICORN_WORKERS != "1"` or if `REDIS_URL` is set,
so any accidental misconfiguration surfaces immediately rather than silently degrading
rate-limit correctness.

---

## 2. When to scale beyond one worker

Monitor the following signals. When **any one** is sustained, revisit this document and
follow the steps in section 3.

| Signal | Threshold |
|---|---|
| CPU utilisation (uvicorn process) | > 70 % averaged over 15 minutes |
| p95 API response latency | > 500 ms |
| Business-tier customer onboarded | First customer with a high-traffic webhook subscription |
| Memory | Worker RSS approaching the PM2 `max_memory_restart` limit (512 MB) |

A CloudWatch alarm on the EC2 instance CPU metric is the easiest first step. Set the
threshold to 70 % with a 15-minute evaluation period and route alerts to `ops@caregist.co.uk`.

---

## 3. How to reintroduce Redis

Follow these steps **in order** before raising the worker count above 1.

### 3.1 Provision Redis

Use ElastiCache Serverless (no cluster to manage, pay per GB-hour) or a managed Redis on
Railway/Render. Record the connection string — it will look like
`redis://:<password>@<host>:6379/0` or `rediss://...` for TLS.

### 3.2 Restore the Redis branches in `rate_limit.py`

The deleted Redis code (lazy client init, `_get_redis`, `_QUOTA_LUA`, `_redis_burst_check`,
`_redis_quota_check`, and the dual-path `check_rate_limit`) was last present at the commit
immediately **before** the merge SHA of the PR that introduced this document
(`prod-ready/drop-redis-single-worker`). Check out that SHA to recover it verbatim:

```bash
git show <merge-SHA-of-prod-ready/drop-redis-single-worker>^:api/middleware/rate_limit.py
```

Restore those functions, wire `_get_redis` to `settings.redis_url`, and remove the
`_assert_single_worker()` call and `UVICORN_WORKERS` guard at the top of the file.

### 3.3 Remove the startup assertion in `api/main.py`

Delete the block that raises `RuntimeError` when `REDIS_URL` is set.

### 3.4 Set `REDIS_URL` in the production `.env`

```
REDIS_URL=redis://:<password>@<host>:6379/0
```

### 3.5 Update `ecosystem.config.cjs`

Change `instances` and add `--workers` to match:

```js
instances: 2,          // or more
exec_mode: "cluster",
args: "api.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=*",
```

Remove `UVICORN_WORKERS: "1"` from the `env` block, or update it to match.

### 3.6 Redeploy

```bash
pm2 reload ecosystem.config.cjs --update-env
```

Verify that the health endpoint responds from both workers and that rate-limit headers
show consistent remaining counts across requests.

### 3.7 Add a Redis health check

Add a `/api/v1/health` probe for the Redis connection so PM2/CloudWatch can detect Redis
outages before they silently degrade rate limiting back to the in-memory fallback.
