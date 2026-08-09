"""Structured JSON logging for production, human-readable for development."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar

# Set per-request by the request-id middleware; read by RequestIdFilter so every
# log line emitted while handling a request carries the same correlation id (F-39).
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Attach the current request id (if any) to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class JSONFormatter(logging.Formatter):
    """Outputs log records as single-line JSON for log aggregation services."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_entry["request_id"] = request_id
        return json.dumps(log_entry, default=str)


def setup_logging(*, json_output: bool = False) -> None:
    """Configure root logger.

    Args:
        json_output: Use JSON formatter (for production). Falls back to
                     human-readable format for local development.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicate output
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s")
        )
    handler.addFilter(RequestIdFilter())

    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
