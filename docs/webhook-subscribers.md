# CareGist Webhook Subscriber Guide

This document explains how to subscribe to CareGist webhooks and verify that
incoming webhook payloads are authentic.

---

## Overview

CareGist signs every webhook delivery using **HMAC-SHA256**. The signature is
included in the `X-CareGist-Signature` header. You should verify this signature
before processing any payload.

### Headers sent with every webhook

| Header | Example value | Description |
|---|---|---|
| `X-CareGist-Signature` | `sha256=abc123...` | HMAC-SHA256 of the raw request body |
| `X-CareGist-Event` | `provider.rating_changed` | The event type |
| `Content-Type` | `application/json` | Always JSON |
| `User-Agent` | `CareGist-Webhooks/1.0` | Fixed identifier |

---

## Signature verification

The signature is computed as:

```
HMAC-SHA256(key=shared_secret, message=raw_request_body_bytes)
```

The header value is `sha256=<hex-digest>`.

> **Important:** Always use the **raw bytes** of the request body, not a
> re-serialised version of the parsed JSON. JSON serialisation is not
> deterministic across libraries and will produce a different hash.

---

## Python verification

```python
import hashlib
import hmac

def verify_caregist_signature(
    shared_secret: str,
    raw_body: bytes,            # request.body — do NOT parse as JSON first
    signature_header: str,      # value of X-CareGist-Signature
) -> bool:
    """Return True if the webhook signature is authentic."""
    expected = hmac.new(
        shared_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected}"
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_header, signature_header)
```

### Flask example

```python
from flask import Flask, request, abort

app = Flask(__name__)
CAREGIST_WEBHOOK_SECRET = "your-shared-secret"

@app.route("/caregist-hook", methods=["POST"])
def handle_caregist_webhook():
    sig = request.headers.get("X-CareGist-Signature", "")
    if not verify_caregist_signature(CAREGIST_WEBHOOK_SECRET, request.data, sig):
        abort(403, "Invalid signature")

    payload = request.get_json()
    event = payload.get("event")
    # ... handle the event
    return "", 200
```

### FastAPI example

```python
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
CAREGIST_WEBHOOK_SECRET = "your-shared-secret"

@app.post("/caregist-hook")
async def handle_caregist_webhook(request: Request):
    raw_body = await request.body()
    sig = request.headers.get("x-caregist-signature", "")
    if not verify_caregist_signature(CAREGIST_WEBHOOK_SECRET, raw_body, sig):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")
    # ... handle the event
    return {"ok": True}
```

---

## Node.js / TypeScript verification

```javascript
const crypto = require('crypto');

/**
 * Verify a CareGist webhook signature.
 *
 * @param {string} sharedSecret   Your webhook shared secret
 * @param {Buffer} rawBody        The raw request body bytes (do NOT re-serialise)
 * @param {string} signatureHeader  Value of the X-CareGist-Signature header
 * @returns {boolean}
 */
function verifyCareGistSignature(sharedSecret, rawBody, signatureHeader) {
  const expected = 'sha256=' + crypto
    .createHmac('sha256', sharedSecret)
    .update(rawBody)
    .digest('hex');

  // Use timingSafeEqual to prevent timing attacks
  const a = Buffer.from(expected);
  const b = Buffer.from(signatureHeader);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}
```

### Express example

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
const CAREGIST_WEBHOOK_SECRET = process.env.CAREGIST_WEBHOOK_SECRET;

app.post(
  '/caregist-hook',
  express.raw({ type: 'application/json' }),  // IMPORTANT: raw body, not JSON-parsed
  (req, res) => {
    const sig = req.headers['x-caregist-signature'] || '';
    if (!verifyCareGistSignature(CAREGIST_WEBHOOK_SECRET, req.body, sig)) {
      return res.status(403).json({ error: 'Invalid signature' });
    }

    const payload = JSON.parse(req.body);
    const event = payload.event;
    // ... handle the event
    res.status(200).json({ ok: true });
  }
);
```

---

## Retry behaviour

CareGist retries failed deliveries up to **3 times** with exponential backoff:

| Attempt | Delay before attempt |
|---|---|
| 1 | Immediate |
| 2 | 1 second |
| 3 | 2 seconds |
| 4 | 4 seconds |

After **10 consecutive failures** the subscription is automatically disabled and
the subscription owner receives an email notification.

Your endpoint should:
- Return a **2xx** status code within **10 seconds** to acknowledge receipt.
- Return **non-2xx** if you want CareGist to retry (e.g. your database is
  temporarily unavailable).
- Process events idempotently — the same event may be delivered more than once.

---

## Events reference

| Event | Description |
|---|---|
| `provider.rating_changed` | A provider's CQC or overall rating changed |
| `provider.status_changed` | A provider's registration status changed |

---

## Security best practices

1. **Verify signatures on every request** before touching the payload.
2. **Use the raw body bytes**, not re-serialised JSON.
3. **Use a constant-time comparison** (`hmac.compare_digest` / `crypto.timingSafeEqual`).
4. **Store your shared secret securely** (environment variable, secrets manager).
5. **Respond quickly**: accept the webhook, then process asynchronously.
