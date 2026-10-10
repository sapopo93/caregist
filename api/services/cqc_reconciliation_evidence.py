"""Bounded, explicit exceptions to authoritative detail coverage."""

import json
import os

DETAIL_UNAVAILABLE_CAP = int(os.getenv("CQC_DETAIL_UNAVAILABLE_CAP", "25"))
if DETAIL_UNAVAILABLE_CAP < 0:
    raise ValueError("CQC_DETAIL_UNAVAILABLE_CAP must be non-negative")


def detail_unavailable_evidence(row) -> dict:
    state = row.get("checkpoint_state") or {}
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except (ValueError, TypeError):
            return {}
    return state if isinstance(state, dict) else {}


def bounded_detail_unavailable(row) -> bool:
    state = detail_unavailable_evidence(row)
    ids = state.get("detailUnavailableIds")
    count = state.get("detail_unavailable")
    cap = state.get("detailUnavailableCap")
    return bool(
        state.get("fullCoverage") is True
        and type(count) is int
        and type(cap) is int
        and 0 < count <= cap <= DETAIL_UNAVAILABLE_CAP
        and count == row["failure_count"]
        and isinstance(ids, list)
        and all(isinstance(value, str) and value for value in ids)
        and len(ids) == count
        and len(set(ids)) == count
    )


# Match the Python validator without casting untrusted JSON values. CASE keeps
# malformed arrays from throwing instead of failing closed.
BOUNDED_DETAIL_UNAVAILABLE_SQL = f"""
  failure_count > 0 AND failure_count <= {DETAIL_UNAVAILABLE_CAP}
  AND checkpoint_state -> 'fullCoverage' = 'true'::jsonb
  AND checkpoint_state -> 'detail_unavailable' = to_jsonb(failure_count)
  AND (checkpoint_state ->> 'detail_unavailable') ~ '^[0-9]+$'
  AND (checkpoint_state ->> 'detailUnavailableCap') ~ '^[0-9]+$'
  AND jsonb_typeof(checkpoint_state -> 'detailUnavailableCap') = 'number'
  AND checkpoint_state -> 'detailUnavailableCap' >= to_jsonb(failure_count)
  AND checkpoint_state -> 'detailUnavailableCap' <= to_jsonb({DETAIL_UNAVAILABLE_CAP})
  AND (
    SELECT COUNT(*) = failure_count AND COUNT(DISTINCT value) = failure_count
      AND BOOL_AND(jsonb_typeof(value) = 'string' AND value <> '\"\"'::jsonb)
    FROM jsonb_array_elements(CASE
      WHEN jsonb_typeof(checkpoint_state -> 'detailUnavailableIds') = 'array'
      THEN checkpoint_state -> 'detailUnavailableIds' ELSE '[]'::jsonb END)
  )
"""
