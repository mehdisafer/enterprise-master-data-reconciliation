"""Small, context-local correlation contract with allowlisted structured logs.

Durable audit/outbox JSON is the source of correlation evidence. Logs are a
sanitized diagnostic projection, not a transaction ledger or tracing provider.
"""
from __future__ import annotations

import json
import logging
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from uuid import UUID, uuid4

TRACE_VERSION = "correlation.v1"


@dataclass(frozen=True)
class CorrelationContext:
    correlation_id: str
    origin_correlation_id: str
    run_id: str | None = None


_context: ContextVar[CorrelationContext | None] = ContextVar("mdm_correlation", default=None)
logger = logging.getLogger("mdm.events")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def uuid_value(value) -> str | None:
    """Accept only opaque UUIDs; never copy arbitrary caller text into a trace."""
    if not isinstance(value, (str, UUID)):
        return None
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError):
        return None


def current_context() -> CorrelationContext | None:
    return _context.get()


@contextmanager
def correlation_scope(*, new: bool = False, run_id: str | None = None,
                      origin_correlation_id: str | None = None):
    """Restore the exact previous context on success, exception or cancellation.

    HTTP entry points use ``new=True``; ordinary nested operations inherit the
    current request. Explicit pipeline run IDs provide a durable retry join key.
    """
    previous = current_context()
    correlation_id = str(uuid4()) if new or previous is None else previous.correlation_id
    run = uuid_value(run_id) if run_id is not None else (previous.run_id if previous and not new else None)
    if run_id is not None and run is None:
        raise ValueError("run correlation requires a UUID")
    origin = uuid_value(origin_correlation_id)
    if origin_correlation_id is not None and origin is None:
        raise ValueError("origin correlation requires a UUID")
    origin = origin or (previous.origin_correlation_id if previous and not new else correlation_id)
    context = CorrelationContext(correlation_id, origin, run)
    token = _context.set(context)
    try:
        yield context
    finally:
        _context.reset(token)


def metadata(parent: dict | None = None, *, decision_id=None, event_id=None, run_id=None) -> dict:
    """Safe additive JSON metadata; legacy payloads may have no trace at all."""
    context = current_context()
    correlation = context.correlation_id if context else str(uuid4())
    parent = parent if isinstance(parent, dict) else {}
    origin = (uuid_value(parent.get("origin_correlation_id")) or uuid_value(parent.get("correlation_id"))
              or (context.origin_correlation_id if context else correlation))
    result = {"trace_version": TRACE_VERSION, "correlation_id": correlation, "origin_correlation_id": origin}
    run = uuid_value(run_id) or (context.run_id if context else None) or uuid_value(parent.get("run_id"))
    if run:
        result["run_id"] = run
    for name, value in (("decision_id", decision_id), ("event_id", event_id)):
        valid = uuid_value(value)
        if valid:
            result[name] = valid
    return result


_UUID_FIELDS = frozenset({
    "decision_id", "event_id", "aggregate_id", "run_id", "origin_correlation_id",
    "producer_correlation_id", "producer_run_id",
})
_COUNT_FIELDS = frozenset({
    "received", "accepted", "duplicates", "groups_rebuilt", "records", "candidates",
    "new_evidence", "automatic_merges", "review", "reject", "group_conflicts",
    "policy_blocked_candidates", "processed", "remaining", "expanded_for_atomic_corrections",
    "attempts", "aggregate_version",
})
_STATUS_VALUES = frozenset({
    "running", "succeeded", "degraded", "failed", "pending", "approved", "executed", "rejected", "replayed",
})


def emit(event: str, **fields) -> None:
    """Allowlist metadata: no actor, token, reason, body, source key or SQL text."""
    if not re.fullmatch(r"[a-z][a-z0-9_.]{1,79}", event):
        raise ValueError("event name must be a reviewed static label")
    item = {"event": event, **metadata()}
    for name, value in fields.items():
        if name in _UUID_FIELDS:
            valid = uuid_value(value)
            if valid:
                item[name] = valid
        elif name in _COUNT_FIELDS and type(value) is int and 0 <= value <= 10**18:
            item[name] = value
        elif name == "duration_ms" and type(value) in {int, float} and 0 <= value < 10**12:
            item[name] = round(value, 3)
        elif name in {"operation", "error_type"} and isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]{0,79}", value):
            item[name] = value
        elif name == "consumer" and isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", value):
            item[name] = value
        elif name == "status" and ((type(value) is int and 100 <= value <= 599)
                                   or (isinstance(value, str) and value in _STATUS_VALUES)):
            item[name] = value
        elif name == "phase" and isinstance(value, str) and value in {"ingestion", "reconciliation", "publication", "complete"}:
            item[name] = value
        elif name == "method" and isinstance(value, str) and value in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "OTHER"}:
            item[name] = value
        elif name == "route" and isinstance(value, str) and (
            value == "unmatched" or re.fullmatch(r"/[A-Za-z0-9/{}_\-.]{0,179}", value)
        ):
            item[name] = value
    # A diagnostic sink must not turn an already committed operation into a
    # business failure. Correlation remains in the transactional JSON ledgers.
    try:
        logger.info(json.dumps(item, sort_keys=True, separators=(",", ":")))
    except Exception:
        return


def correlated_operation(operation: str):
    """Scope synchronous CLI/service work; completion follows transaction exit."""
    if not re.fullmatch(r"[a-z][a-z0-9_.]{1,79}", operation):
        raise ValueError("operation name must be a reviewed static label")

    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with correlation_scope():
                started = time.monotonic()
                emit("operation.started", operation=operation)
                try:
                    result = function(*args, **kwargs)
                except BaseException as exc:
                    if isinstance(exc, SystemExit) and exc.code in (None, 0):
                        emit("operation.succeeded", operation=operation,
                             duration_ms=(time.monotonic() - started) * 1000)
                    else:
                        emit("operation.failed", operation=operation, error_type=type(exc).__name__,
                             duration_ms=(time.monotonic() - started) * 1000)
                    raise
                summary = {}
                if isinstance(result, dict):
                    summary = {key: value for key, value in result.items()
                               if key in _COUNT_FIELDS | {"decision_id", "run_id", "status"}}
                emit("operation.succeeded", operation=operation, duration_ms=(time.monotonic() - started) * 1000,
                     **summary)
                return result
        return wrapped
    return decorate
