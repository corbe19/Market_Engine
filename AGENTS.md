# AGENTS.md

Operating manual for anyone — human or agent — working in this repository.
`plan.md` says *what* and *why*; this file says *how*. Read both before
starting a task; the protocol in `plan.md` §11 is binding.

## Setup

```bash
py -3.11 -m venv .venv                       # Windows; `python3.11 -m venv .venv` elsewhere
.venv/Scripts/python.exe -m pip install -e ".[dev]"   # .venv/bin/python elsewhere
```

Python 3.11 is the floor. 3.12 is tested in CI. 3.14 is deliberately not used
yet: the numerical stack's wheel coverage is the constraint, and it matters
from Milestone 4 onward.

## The one command

```bash
python scripts/check.py          # ruff check, ruff format --check, mypy, pytest
python scripts/check.py --fix    # apply ruff fixes and formatting first
```

CI runs exactly this on Linux and Windows. A green local run predicts a green
CI run; nothing else is considered "passing".

Individual tools, when you want only one:

```bash
python -m pytest tests/unit/test_config.py -k unknown   # narrow test loop
python -m ruff check .                                   # lint
python -m ruff format .                                  # format in place
python -m mypy                                           # types (strict)
```

## Layout

```
src/market_engine/     the package; import as `market_engine.<stage>`
  config.py            typed, frozen config — see "Configuration"
  ingestion/           exchange WebSocket, normalization, raw capture      (M1)
  orderbook/           local book reconstruction and invariants            (M2)
  replay/              deterministic playback of recorded logs             (M2)
  features/            causal streaming features                           (M3)
  labels/              forward-looking labels                              (M3)
  models/              baselines, models, calibration, registry         (M4, M8)
  regimes/             regime definition and assignment                    (M5)
  execution/           execution simulator                                 (M6)
  monitoring/          logging, metrics, drift                         (M0, M8)
    logs.py            structured logging + run IDs — see "Logging"
  api/                 FastAPI service                                     (M8)
cpp/                   native path, empty until Milestone 7
configs/               development / research / production profiles
schemas/               versioned JSON Schema for the data contracts
tests/                 unit / property / integration / replay / performance
scripts/               entry points; check.py is the CI command
data/                  see data/README.md — raw/ and processed/ are never committed
artifacts/             models, metrics, figures — never committed
research/              notebooks, experiment configs, reports
```

Dependency direction is one way: `ingestion → orderbook → features → labels →
models → execution`. `replay` feeds `orderbook` in place of `ingestion`.
`monitoring` and `api` observe; nothing in the pipeline imports from them.

## Configuration

```python
from market_engine.config import load_config
cfg = load_config("configs/research.yaml")        # or $MARKET_ENGINE_CONFIG, or defaults
cfg = load_config(path, overrides={"run": {"seed": 3}})   # CLI flags go here
```

Rules:

- **Unknown keys are errors.** A typo fails at load, never silently no-ops.
- **Config is frozen.** Do not work around this; if a value must change
  mid-run, it is not configuration.
- **Never hard-code** an exchange, instrument, path, threshold, or credential.
  Add a typed field with a `description`; then regenerate the reference block
  in `configs/development.yaml`:

  ```bash
  python -c "from market_engine.config import describe_defaults; print(describe_defaults())"
  ```

  A test fails if that file and the code disagree.
- `research.yaml` and `production.yaml` list only what differs from defaults.

## Logging

```python
import logging
from market_engine.monitoring.logs import configure_logging, run_context

configure_logging(level=cfg.run.log_level, fmt=cfg.run.log_format)
with run_context() as run_id:          # every log line now carries run_id
    log = logging.getLogger(__name__)
    log.warning("sequence gap", extra={"expected": 41, "received": 44})
```

- Use `logging.getLogger(__name__)`; never `print` from library code.
- Put facts in `extra=`, not in the message string. They become JSON keys and
  are what metrics and drift alerts are built from later.
- Every entry point (`scripts/*.py`) opens a `run_context()` and records the
  run ID in whatever it writes to `artifacts/`.
- Data-quality incidents (gaps, reconnects, crossed books, stale data) are
  logged at `WARNING` or above with enough `extra=` fields to reconstruct what
  happened. Silent recovery is a bug (`plan.md` invariant 3).

## Conventions

- **Types are strict.** `mypy --strict` passes on `src/`, `tests/`, and
  `scripts/`. Prefer precise types over `Any`; `# type: ignore` needs a
  reason code and a comment.
- **Tests live with the change.** No behaviour lands without a test. Test
  layout: `unit/` for pure functions and single classes, `property/` for
  invariants (Hypothesis, from M2), `replay/` for golden fixtures,
  `integration/` for multi-component paths, `performance/` for measurements.
- **Time is integer nanoseconds UTC** everywhere in the pipeline. Prices and
  quantities are integer ticks/units. Floats appear only at the edges (display,
  model input) and never in the book or the event log.
- **Two timestamps, always:** `exchange_timestamp_ns` (orders events, defines
  labels) and `receive_timestamp_ns` (what you actually had). Conflating them
  is a look-ahead leak.
- **Point-in-time or it doesn't ship.** Any feature must be computable from a
  single forward pass over events. If you need `df.shift(-1)`, stop.
- **Determinism is a test.** Anything touching the book, features, or replay
  gets a "run twice, compare hashes" test.
- **Decisions go in the log.** A new architectural or research choice is
  recorded in `plan.md` §15 using the template there, with alternatives and
  consequences, in the same change that makes it.
- Formatting and import order are ruff's job. Don't hand-format.

## Parallel-work rules

Safe to work on simultaneously, once the interface between them is fixed:
separate pipeline stages, tests versus implementation, docs versus code.

**Not safe** without coordinating first — one owner at a time:

- `pyproject.toml`, `.github/workflows/`, `scripts/check.py`
- `src/market_engine/config.py` and `configs/`
- `schemas/` and the `MarketEvent` / `BookSnapshot` / `FeatureVector` /
  `Prediction` contracts
- Label definitions
- Timestamp and sequence-number semantics
- Golden fixtures under `tests/replay/` and `data/samples/` — changing one
  requires a migration note explaining why the expected output changed

## Definition of done for a task

1. `python scripts/check.py` is green.
2. New behaviour has tests; changed behaviour has updated tests.
3. Any new setting is in `config.py` with a description, and
   `configs/development.yaml` is regenerated.
4. Any new decision is in `plan.md` §15.
5. The relevant `plan.md` checkbox is ticked **only if** the milestone's
   acceptance criteria still hold.
6. The report names changed files, commands run, results, assumptions, and
   remaining risks.

## What not to commit

Raw or processed market data, trained models, metrics dumps, figures, `.env`,
API keys, anything under `.venv/`. `.gitignore` enforces most of this; if
`git status` shows something large or secret-looking, stop and check.
