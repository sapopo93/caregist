# Proof brief 2 — deterministic change workflows

Status: ready for Human Gate 1 review; internal only.

## Proposition

CareGist can derive replay-safe registration, rating, status, ownership and group
movement events and drive monitor/digest/export/webhook workflows without sending
anything during the proof.

## Controlled proof

- Apply a synthetic old/new provider state pair for each event class.
- Replay each pair and prove stable deduplication.
- Exercise monitor and digest selection in dry-run mode.
- Deliver a webhook only to a mocked transport and verify signature/log/idempotency.
- Generate CSV bytes in memory and assert schema/escaping without returning a download.

## Acceptance evidence

- Migration 040 and `api/services/provider_state_events.py`.
- Focused monitor, digest, export, cron and webhook tests.
- Checkout, lead intake and export delivery remain default-off.

## Human Gate 1 decision requested

Approve or reject only the non-network test protocol and name operations/security
owners. Do not approve paid monitoring, customer export delivery, webhook
registration/delivery, billing or price changes.

## Residuals

Deployment egress, retry saturation, queue recovery and recipient suppression need
an operations exercise before any live delivery.
