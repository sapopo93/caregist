"""Plain-dict views of Stripe SDK objects.

From stripe-python 13, ``StripeObject`` is no longer a ``dict``: ``obj.get(...)``
raises ``AttributeError``. Billing code reads Stripe payloads with ``.get``
throughout, so every object it inspects is converted once, where it enters the
code, rather than at each read. Attribute access (``session.url``) on objects
that are not converted keeps working.
"""

from __future__ import annotations

from typing import Any


def stripe_dict(obj: Any) -> Any:
    """Recursively convert a Stripe object (or plain value) to builtin types."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict) and not isinstance(obj, dict):
        return stripe_dict(to_dict())
    if isinstance(obj, dict):
        return {key: stripe_dict(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [stripe_dict(value) for value in obj]
    return obj
