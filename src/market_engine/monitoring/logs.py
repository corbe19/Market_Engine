"""Structured logging with a per-run correlation ID.

Why this exists (``plan.md`` invariants 3 and 9):

* Data-quality incidents — gaps, reconnects, crossed books — must be
  *surfaced*, not just printed. JSON-per-line output is the substrate that
  metrics and drift alerts get built on later; free-text logs are not.
* A run ID joins one execution's logs, artifacts, and manifest into a single
  traceable thing. It lives in a :mod:`contextvars` variable so async tasks
  spawned by the ingestion layer inherit it without plumbing.

Usage::

    configure_logging(level="INFO", fmt="json")
    with run_context() as run_id:
        log = logging.getLogger(__name__)
        log.warning("sequence gap", extra={"expected": 41, "received": 44})

Extra fields passed via ``extra=`` appear as top-level keys in JSON output and
as ``key=value`` pairs in console output.
"""

from __future__ import annotations

import contextlib
import json
import logging
import secrets
import sys
from collections.abc import Iterator
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Literal, TextIO

LogFormat = Literal["console", "json"]

_run_id: ContextVar[str | None] = ContextVar("market_engine_run_id", default=None)

# Attributes every LogRecord carries. Anything else on the record came from
# ``extra=`` and should be emitted as a structured field.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | frozenset({"message", "asctime", "run_id"})


def new_run_id(now: datetime | None = None) -> str:
    """Return a run ID that sorts chronologically and is unique in practice.

    Format ``YYYYMMDDTHHMMSSZ-xxxxxx``: UTC to the second, then 24 random bits.
    Sortable so directory listings of artifacts read in execution order; short
    enough to type; enough entropy that two runs in the same second on the
    same machine do not collide.
    """
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(3)}"


def current_run_id() -> str | None:
    return _run_id.get()


@contextlib.contextmanager
def run_context(run_id: str | None = None) -> Iterator[str]:
    """Bind ``run_id`` (a fresh one if ``None``) for the duration of the block."""
    rid = run_id or new_run_id()
    token = _run_id.set(rid)
    try:
        yield rid
    finally:
        _run_id.reset(token)


class _RunIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = current_run_id()
        return True


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {k: v for k, v in record.__dict__.items() if k not in _STANDARD_RECORD_ATTRS}


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Field order is stable so diffs are readable."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="microseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
        }
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


class ConsoleFormatter(logging.Formatter):
    """Compact human-readable line; same information as the JSON form."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, UTC).strftime("%H:%M:%S.%f")[:-3]
        rid = getattr(record, "run_id", None) or "-"
        line = f"{ts} {record.levelname:<7} [{rid}] {record.name}: {record.getMessage()}"
        extras = _extra_fields(record)
        if extras:
            line += " " + " ".join(f"{k}={v!r}" for k, v in extras.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging(
    *,
    level: str = "INFO",
    fmt: LogFormat = "console",
    stream: TextIO | None = None,
) -> None:
    """Install a single root handler. Safe to call more than once.

    Existing root handlers are removed so that repeated configuration (tests,
    notebooks, CLI re-entry) cannot produce duplicated lines.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter() if fmt == "json" else ConsoleFormatter())
    handler.addFilter(_RunIdFilter())
    root.addHandler(handler)
    root.setLevel(level)
