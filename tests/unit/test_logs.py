from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from market_engine.monitoring.logs import (
    configure_logging,
    current_run_id,
    new_run_id,
    run_context,
)

RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{6}$")


@pytest.fixture(autouse=True)
def _reset_root_logger() -> Iterator[None]:
    """Leave the root logger the way we found it."""
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    yield
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in saved_handlers:
        root.addHandler(h)
    root.setLevel(saved_level)


def _capture(fmt: str, level: str = "DEBUG") -> io.StringIO:
    buf = io.StringIO()
    configure_logging(level=level, fmt=fmt, stream=buf)  # type: ignore[arg-type]
    return buf


# --- run IDs -----------------------------------------------------------------


def test_run_id_format() -> None:
    assert RUN_ID_RE.match(new_run_id())


def test_run_id_sorts_chronologically() -> None:
    earlier = new_run_id(datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC))
    later = new_run_id(datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC))
    assert earlier < later


def test_run_ids_are_unique_within_a_second() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert len({new_run_id(now) for _ in range(200)}) == 200


def test_run_context_binds_and_restores() -> None:
    assert current_run_id() is None
    with run_context("fixed-id") as rid:
        assert rid == "fixed-id"
        assert current_run_id() == "fixed-id"
        with run_context() as inner:
            assert inner != "fixed-id"
            assert current_run_id() == inner
        assert current_run_id() == "fixed-id"
    assert current_run_id() is None


def test_run_context_restores_after_exception() -> None:
    with pytest.raises(RuntimeError), run_context("x"):
        raise RuntimeError
    assert current_run_id() is None


def test_run_id_propagates_into_async_tasks() -> None:
    """Ingestion (M1) is async; spawned tasks must inherit the run ID."""

    async def child() -> str | None:
        await asyncio.sleep(0)
        return current_run_id()

    async def main() -> str | None:
        with run_context("async-run"):
            return await asyncio.create_task(child())

    assert asyncio.run(main()) == "async-run"


# --- JSON output -------------------------------------------------------------


def test_json_line_has_core_fields_and_run_id() -> None:
    buf = _capture("json")
    with run_context("r1"):
        logging.getLogger("t.core").info("hello %s", "world")
    rec = json.loads(buf.getvalue())
    assert rec["msg"] == "hello world"
    assert rec["level"] == "INFO"
    assert rec["logger"] == "t.core"
    assert rec["run_id"] == "r1"
    datetime.fromisoformat(rec["ts"])  # parseable


def test_json_extra_fields_become_top_level_keys() -> None:
    buf = _capture("json")
    logging.getLogger("t").warning("gap", extra={"expected": 41, "received": 44})
    rec = json.loads(buf.getvalue())
    assert rec["expected"] == 41
    assert rec["received"] == 44


def test_json_run_id_is_null_outside_a_run() -> None:
    buf = _capture("json")
    logging.getLogger("t").info("x")
    assert json.loads(buf.getvalue())["run_id"] is None


def test_json_includes_exception_text() -> None:
    buf = _capture("json")
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("t").exception("failed")
    rec = json.loads(buf.getvalue())
    assert "ValueError: boom" in rec["exc"]


def test_json_one_object_per_line() -> None:
    buf = _capture("json")
    log = logging.getLogger("t")
    log.info("a")
    log.info("b")
    lines = buf.getvalue().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["msg"] for line in lines] == ["a", "b"]


def test_json_non_serializable_extra_is_stringified() -> None:
    buf = _capture("json")
    logging.getLogger("t").info("x", extra={"when": datetime(2026, 1, 1, tzinfo=UTC)})
    assert "2026-01-01" in json.loads(buf.getvalue())["when"]


# --- console output ----------------------------------------------------------


def test_console_line_contains_run_id_message_and_extras() -> None:
    buf = _capture("console")
    with run_context("r2"):
        logging.getLogger("t").info("hello", extra={"k": 1})
    line = buf.getvalue()
    assert "[r2]" in line
    assert "hello" in line
    assert "k=1" in line


# --- configuration behaviour -------------------------------------------------


def test_level_filters() -> None:
    buf = _capture("json", level="WARNING")
    logging.getLogger("t").info("hidden")
    logging.getLogger("t").warning("shown")
    assert buf.getvalue().count("\n") == 1


def test_reconfigure_does_not_duplicate_handlers() -> None:
    _capture("json")
    buf = _capture("json")
    logging.getLogger("t").info("once")
    assert buf.getvalue().count("\n") == 1
    assert len(logging.getLogger().handlers) == 1
