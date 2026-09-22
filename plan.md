# Real-Time Market Microstructure Intelligence Platform

## 1. Purpose

Build a production-style research and engineering platform that consumes live limit-order-book data, reconstructs the book locally, computes point-in-time-correct streaming features, generates calibrated short-horizon predictions, and evaluates whether those predictions remain useful after realistic execution costs and latency.

This project is intended to demonstrate:

- Machine learning on noisy, non-stationary time-series data
- Probability, calibration, and rigorous experimental design
- Real-time event processing and data engineering
- Performance-sensitive C++ and Python interoperability
- Backtesting with realistic market constraints
- Production ML practices: monitoring, drift detection, retraining, and deployment
- Clear technical judgment, including honest negative results

The project is a research platform, not a claim of profitable trading alpha.

## 2. Central Research Question

> Can short-horizon order-book signals remain predictive after accounting for market regime, execution latency, transaction costs, and model degradation over time?

Every major feature should help answer this question. Avoid adding infrastructure that does not strengthen the research result, system reliability, or measured performance.

## 3. Target Outcome

A reproducible system that can:

1. Consume a live exchange WebSocket feed.
2. Reconstruct and validate a local limit order book.
3. Persist raw events for deterministic replay.
4. Compute streaming microstructure features without look-ahead leakage.
5. Predict the probability of a short-horizon mid-price movement.
6. Detect or classify the current market regime.
7. Evaluate models using walk-forward validation and probability calibration.
8. Simulate execution with fees, spread, slippage, latency, partial fills, and inventory limits.
9. Report throughput, feature freshness, and p50/p95/p99 latency.
10. Display live predictions, system health, drift, and simulated performance.

## 4. Scope

### Core deliverable

The first complete version uses one exchange, one liquid instrument, and one primary prediction task:

> Given all information available at time `t`, estimate the probability that the mid-price will increase by at least `X` basis points during the next `H` seconds.

Initial experimental defaults:

- Instrument: one highly liquid crypto pair
- Prediction horizon `H`: test 1, 5, and 10 seconds; select one primary horizon using validation data only
- Movement threshold `X`: define relative to spread or recent volatility so the label is not dominated by noise
- Primary model output: calibrated probability, not only a class label
- Primary baseline: regularized logistic regression
- Primary advanced model: gradient-boosted trees

### Stretch deliverables

Complete these only after the core pipeline is reliable and reproducible:

- Regime-specific mixture-of-experts routing
- Online learning and automated champion/challenger promotion
- C++ streaming feature engine exposed through `pybind11`
- Fill-probability, volatility, or spread-widening auxiliary models
- Multi-instrument or cross-exchange signals
- Temporal neural network such as a TCN or compact Transformer
- Paper-trading integration using strict risk controls

### Explicit non-goals

- Trading real money
- Claiming profitability from a short or cherry-picked test period
- Building a full exchange or brokerage system
- Supporting many exchanges before one feed is correct
- Optimizing low-level code before profiling identifies a bottleneck
- Using a deep model without strong simple baselines
- Random train/test splits for time-series experiments

## 5. System Architecture

```text
Exchange WebSocket
        |
        v
Feed Handler -----> Raw Append-Only Event Log
        |
        v
Order-Book Engine <----- Deterministic Replay Engine
        |
        v
Streaming Feature Engine
        |
        +------> Feature/Label Dataset Builder
        |                    |
        |                    v
        |            Training + Walk-Forward Evaluation
        |                    |
        |                    v
        +------------> Model Registry
                             |
                             v
Live Inference -----> Regime Model -----> Execution Simulator
        |                                      |
        +------------------+-------------------+
                           v
                  API + Monitoring + Dashboard
```

### Proposed technology choices

| Concern                         | Initial choice                                              | Rationale                                                    |
| ------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------ |
| Research and orchestration      | Python 3.11+                                                | Strong ML/data ecosystem and fast iteration                  |
| Performance-critical processing | C++20                                                       | Demonstrates systems ability and enables latency comparisons |
| Python/C++ boundary             | `pybind11`                                                  | Keeps research workflow simple while exposing native code    |
| Modeling                        | scikit-learn, LightGBM/XGBoost, PyTorch only when justified | Strong baselines before neural models                        |
| API                             | FastAPI                                                     | Typed, lightweight inference and metrics endpoints           |
| Live transport                  | Exchange WebSocket client                                   | Event-driven market data ingestion                           |
| Historical storage              | Parquet partitioned by date/instrument                      | Efficient replay and research access                         |
| Metadata/results                | PostgreSQL or SQLite initially                              | Experiment, run, and model metadata                          |
| Metrics                         | Prometheus-compatible metrics                               | Standard latency, throughput, and health instrumentation     |
| Dashboard                       | Next.js/React                                               | Live system and research-result presentation                 |
| Packaging                       | Docker Compose                                              | Reproducible local development and demos                     |
| CI                              | GitHub Actions                                              | Automated tests, linting, and benchmark smoke tests          |

Use simpler replacements during early milestones when they shorten the path to a validated end-to-end slice.

## 6. Repository Layout

```text
market-intelligence/
├── plan.md
├── README.md
├── AGENTS.md
├── pyproject.toml
├── CMakeLists.txt
├── docker-compose.yml
├── configs/
│   ├── development.yaml
│   ├── research.yaml
│   └── production.yaml
├── schemas/
│   ├── market_event.schema.json
│   ├── book_snapshot.schema.json
│   └── prediction.schema.json
├── src/
│   ├── ingestion/
│   ├── orderbook/
│   ├── replay/
│   ├── features/
│   ├── labels/
│   ├── models/
│   ├── regimes/
│   ├── execution/
│   ├── monitoring/
│   └── api/
├── cpp/
│   ├── orderbook/
│   ├── features/
│   ├── bindings/
│   └── benchmarks/
├── dashboard/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── property/
│   ├── replay/
│   └── performance/
├── research/
│   ├── notebooks/
│   ├── experiments/
│   └── reports/
├── data/
│   ├── README.md
│   ├── raw/.gitkeep
│   ├── processed/.gitkeep
│   └── samples/
├── artifacts/
│   ├── models/.gitkeep
│   ├── metrics/.gitkeep
│   └── figures/.gitkeep
└── scripts/
    ├── collect.py
    ├── replay.py
    ├── build_dataset.py
    ├── train.py
    ├── evaluate.py
    └── run_demo.py
```

Do not commit large raw datasets or secrets. Commit small deterministic samples sufficient for tests and a local demo.

## 7. Engineering Invariants

These rules are mandatory across all milestones:

1. **Point-in-time correctness:** a feature at time `t` may use only events with exchange timestamps no later than `t` and only events received before inference.
2. **Deterministic replay:** replaying the same ordered event log with the same configuration must produce identical book states, features, labels, and predictions.
3. **No silent recovery:** dropped messages, sequence gaps, crossed books, stale data, and reconnects must be recorded and surfaced as metrics.
4. **Time-aware evaluation:** all validation and testing must move forward in time. Never randomly shuffle observations across splits.
5. **Baseline first:** every complex model must be compared with naive, linear, and simple tree-based baselines.
6. **Calibration matters:** classification results must include Brier score, log loss, and reliability analysis—not accuracy alone.
7. **Execution realism:** any P&L result must state fees, spread, slippage, latency, fill assumptions, position limits, and rejected/stale predictions.
8. **Measured optimization:** move code to C++ only after profiling or to run an explicit Python-versus-C++ benchmark.
9. **Reproducibility:** experiments must record data interval, code commit, configuration, random seed, feature set, label definition, and environment.
10. **Honest reporting:** failed experiments and negative results belong in the final report when they influence conclusions.

## 8. Core Data Contracts

Define these contracts before implementing business logic. Use integer price and quantity units where possible to avoid floating-point ambiguity.

### `MarketEvent`

Required fields:

- `exchange`
- `instrument`
- `event_type`
- `exchange_timestamp_ns`
- `receive_timestamp_ns`
- `sequence_number`
- `side`
- `price_ticks`
- `quantity_units`
- `order_or_level_id` when available
- `connection_id`

### `BookSnapshot`

Required fields:

- Event identity and both timestamps
- Best bid and ask
- Mid-price and spread
- Top `N` price levels on both sides
- Book-validity flag
- Staleness and sequence-gap flags

### `FeatureVector`

Required fields:

- Feature timestamp and source event sequence
- Feature schema version
- Spread, mid-price, microprice/weighted mid-price
- Depth and imbalance at multiple levels
- Trade-flow imbalance
- Rolling volatility and returns
- Arrival and cancellation intensity
- Data-quality flags

### `Prediction`

Required fields:

- Inference timestamp
- Feature timestamp
- Model version
- Label definition/version
- Raw probability
- Calibrated probability
- Current regime and confidence
- End-to-end latency
- Valid/stale decision flag

## 9. Milestone Plan

Agents should work in milestone order unless a task is explicitly marked parallel-safe. A milestone is complete only when its acceptance criteria pass.

### Milestone 0 — Repository and reproducibility foundation

**Goal:** Make the project safe for parallel, repeatable development.

Tasks:

- [x] Create the proposed directory structure.
- [x] Add Python environment, linting, formatting, type checking, and tests.
- [ ] Add C++ build configuration and a minimal Python binding smoke test. _(deferred to Milestone 7 — see decision log)_
- [ ] Add configuration loading with documented defaults.
- [ ] Add structured logging and run IDs.
- [ ] Add CI for Python and C++ tests.
- [ ] Write `AGENTS.md` with commands, conventions, and ownership rules.
- [x] Add `data/README.md` documenting data retention and privacy constraints.

Acceptance criteria:

- One command installs or starts the development environment.
- One command runs all tests and static checks.
- CI passes on a clean checkout.
- No secret or large-data path is tracked by Git.

### Milestone 1 — Reliable ingestion and raw event capture

**Goal:** Collect replayable live market events from one exchange and instrument.

Tasks:

- [ ] Select the initial exchange and instrument; record the decision in Section 15.
- [ ] Implement WebSocket connection, subscription, heartbeat, and graceful shutdown.
- [ ] Normalize exchange messages into `MarketEvent`.
- [ ] Preserve exchange and local receive timestamps.
- [ ] Detect sequence gaps, reconnects, duplicates, and malformed messages.
- [ ] Persist raw normalized events to append-only, partitioned storage.
- [ ] Create a small sanitized event fixture for tests.
- [ ] Add collection metrics: message rate, lag, reconnects, gaps, and parse errors.

Acceptance criteria:

- The collector runs continuously for at least two hours without silent failure.
- A disconnect/reconnect integration test passes.
- Captured events can be read back in original sequence.
- Data-quality incidents appear in logs and metrics.

### Milestone 2 — Order-book reconstruction and deterministic replay

**Goal:** Reconstruct a correct local book and reproduce it offline.

Tasks:

- [ ] Implement snapshot initialization and incremental updates.
- [ ] Enforce exchange-specific sequencing rules.
- [ ] Invalidate and resynchronize the book after a detected gap.
- [ ] Implement deterministic event replay with controllable playback speed.
- [ ] Add invariants: sorted levels, positive quantities, and best bid below best ask unless explicitly invalid.
- [ ] Build property-based tests for insert, modify, cancel, and reset behavior.
- [ ] Compare reconstructed checksums or snapshots with source snapshots when supported.

Acceptance criteria:

- Replaying a fixture produces an expected final book exactly.
- Replaying the same log twice produces identical snapshots and hashes.
- Sequence-gap tests invalidate the book and trigger resynchronization.
- Invalid book states cannot silently flow into features.

### Milestone 3 — Point-in-time streaming features and labels

**Goal:** Build a leakage-safe supervised-learning dataset from the live/replay path.

Tasks:

- [ ] Implement spread, mid-price, microprice, and multi-level depth imbalance.
- [ ] Implement rolling returns, realized volatility, trade imbalance, event intensity, and cancellation intensity.
- [ ] Support several causal windows such as 100 ms, 1 s, 5 s, and 30 s.
- [ ] Version the feature schema.
- [ ] Define movement labels for 1, 5, and 10 seconds.
- [ ] Account for overlapping labels and serial dependence in evaluation design.
- [ ] Add feature freshness and missingness flags.
- [ ] Write explicit leakage tests using synthetic events with known future shocks.

Acceptance criteria:

- Live and replay paths produce equivalent features for the same events.
- Leakage tests show that a future event cannot change an earlier feature vector.
- A dataset manifest records time range, gaps, dropped intervals, schema version, and label balance.
- The generated dataset is sufficient to reproduce an initial experiment.

### Milestone 4 — Baseline research framework

**Goal:** Establish honest, reproducible performance baselines.

Tasks:

- [ ] Implement naive baselines: majority/no-move, last-move, and imbalance threshold.
- [ ] Train regularized logistic regression.
- [ ] Train a gradient-boosted tree model.
- [ ] Use chronological train/validation/test periods.
- [ ] Add rolling or expanding walk-forward evaluation.
- [ ] Fit probability calibration on validation data only.
- [ ] Report confusion metrics, ROC-AUC/PR-AUC where appropriate, Brier score, log loss, calibration error, and reliability curves.
- [ ] Report results by time period, class, spread bucket, volatility bucket, and data-quality state.
- [ ] Add permutation or ablation analysis for feature groups.

Acceptance criteria:

- A single command reproduces the baseline report from a dataset manifest.
- Test data remains untouched until model and threshold choices are fixed.
- Results include confidence intervals or block-bootstrap uncertainty where appropriate.
- The report clearly distinguishes discrimination, calibration, and simulated economic value.

### Milestone 5 — Market-regime analysis

**Goal:** Determine whether predictive behavior changes across market conditions.

Tasks:

- [ ] Define interpretable rule-based regimes as a baseline.
- [ ] Compare with an unsupervised model such as Gaussian mixture, HMM, or clustering.
- [ ] Prevent regime fitting from seeing future/test information.
- [ ] Measure baseline model performance within each regime.
- [ ] Test a regime-feature model before separate expert models.
- [ ] If justified, train regime-specific models and compare with a single global model.
- [ ] Analyze transition stability and regime duration.

Acceptance criteria:

- Regimes are reproducible and described by measurable market characteristics.
- Regime-aware results are compared against the same global baseline and test periods.
- Added complexity is retained only if it improves out-of-sample performance or yields a meaningful diagnostic insight.

### Milestone 6 — Execution simulator and economic evaluation

**Goal:** Test whether statistical signal survives realistic implementation assumptions.

Tasks:

- [ ] Convert calibrated predictions into explicit decision rules.
- [ ] Implement market-order execution with fees and spread crossing.
- [ ] Implement limit-order execution with queue/fill assumptions clearly documented.
- [ ] Model configurable signal-to-order and network latency.
- [ ] Model partial fills, slippage, inventory, position limits, and cooldowns.
- [ ] Reject predictions that are stale or generated from an invalid book.
- [ ] Compare gross and net results under multiple cost and latency scenarios.
- [ ] Add risk metrics: drawdown, turnover, exposure, tail loss, and regime-specific performance.

Acceptance criteria:

- Results change predictably when fees or latency increase.
- No strategy can trade on information unavailable at simulated decision time.
- Every result names its execution assumptions.
- The final report includes at least one adversarial/conservative assumption set.

### Milestone 7 — C++ performance path

**Goal:** Demonstrate measured systems optimization without changing behavior.

Tasks:

- [ ] Profile the Python end-to-end replay and live pipeline.
- [ ] Select order-book reconstruction or feature calculation based on measured bottlenecks.
- [ ] Implement the selected component in C++20.
- [ ] Expose it to Python through `pybind11` or a documented service boundary.
- [ ] Create parity tests between Python and C++ implementations.
- [ ] Benchmark throughput, p50/p95/p99 latency, CPU, and memory.
- [ ] Document measurement environment and methodology.

Acceptance criteria:

- Python and C++ implementations produce equivalent outputs on shared fixtures.
- Benchmarks are repeatable and include warm-up and sufficient sample counts.
- The report states absolute performance and speedup, not speedup alone.
- Optimization does not weaken validation, error handling, or observability.

### Milestone 8 — Live inference, monitoring, and drift

**Goal:** Operate the model as a measurable production-style service.

Tasks:

- [ ] Package preprocessing, feature schema, model, and calibration artifacts together.
- [ ] Implement live inference with model/version metadata.
- [ ] Add health, readiness, predictions, and metrics API endpoints.
- [ ] Monitor feature distributions, missingness, prediction distributions, calibration lag, and realized performance.
- [ ] Add drift tests such as PSI/KS or distribution-distance measures with carefully chosen thresholds.
- [ ] Implement shadow evaluation for a challenger model.
- [ ] Define retraining and promotion rules; require human approval for promotion in the core version.
- [ ] Test rollback to the previous model.

Acceptance criteria:

- A replayed event stream can drive the same API and monitoring path as live data.
- Every prediction is traceable to model, feature, and label versions.
- A synthetic distribution shift triggers a drift alert.
- A failed or inferior challenger cannot replace the champion automatically.

### Milestone 9 — Dashboard, final report, and public demo

**Goal:** Make the technical depth understandable within a few minutes.

Tasks:

- [ ] Display book depth, spread, regime, calibrated probability, and prediction freshness.
- [ ] Display system throughput and p50/p95/p99 latency.
- [ ] Display simulated positions, trades, gross/net P&L, and assumptions.
- [ ] Display reliability curves, walk-forward metrics, drift, and model versions.
- [ ] Write an architecture and research README.
- [ ] Write a final report centered on the central research question.
- [ ] Include failures, limitations, and results that did not survive costs.
- [ ] Record a short deterministic demo using replay data.
- [ ] Add resume bullets with measured scale and performance only after measurements exist.

Acceptance criteria:

- A new user can run the deterministic demo from a clean checkout.
- The README distinguishes live mode from deterministic replay mode.
- Charts can be regenerated from versioned experiment outputs.
- Claims in the README and resume bullets trace to reproducible metrics.

## 10. Recommended Build Order

Do not build all components simultaneously. Prioritize vertical slices:

1. **Replay slice:** fixture -> book -> features -> baseline prediction -> evaluation report.
2. **Live slice:** WebSocket -> event log -> book -> features -> live prediction -> metrics.
3. **Research slice:** larger dataset -> walk-forward models -> calibration -> regime analysis.
4. **Economic slice:** predictions -> execution simulator -> cost/latency sensitivity.
5. **Systems slice:** profile -> C++ implementation -> parity and benchmark report.
6. **Production slice:** registry -> service -> drift -> dashboard -> reproducible demo.

The replay slice should exist early because it gives every agent a deterministic development and test environment.

## 11. Agent Operating Protocol

Agents working from this file must follow this protocol.

### Before starting a task

1. Read `plan.md`, `AGENTS.md`, and the relevant source/tests.
2. Check the current branch, working tree, and open task ledger.
3. Select one unchecked task with satisfied dependencies.
4. State the selected task, files expected to change, and acceptance test.
5. Do not overwrite or revert unrelated work from another agent.

### While working

1. Keep changes scoped to one coherent task.
2. Define or update tests with implementation changes.
3. Preserve data contracts and engineering invariants.
4. Use configuration rather than hard-coded exchange, instrument, paths, thresholds, or credentials.
5. Never commit credentials, large datasets, generated models, or private exchange data.
6. Record a new architectural or research choice in the decision log.
7. If blocked by an ambiguous contract, stop and document the blocker rather than inventing incompatible behavior.

### Before marking a task complete

1. Run the narrow tests for changed code.
2. Run the repository-wide test/static-check command when practical.
3. Update relevant documentation and configuration examples.
4. Report changed files, commands run, results, assumptions, and remaining risks.
5. Mark a checkbox complete only when its milestone acceptance criteria remain satisfied.

### Parallel-work boundaries

Parallel work is safe when agents own separate modules with an agreed interface. Good examples:

- Ingestion adapter and dashboard scaffolding after schemas are fixed
- Python baseline models and C++ benchmark harness after fixtures are fixed
- Monitoring views and research-report tooling after output schemas are fixed

Parallel work is unsafe when interfaces are still changing. Avoid simultaneous uncoordinated edits to:

- Core schemas and event contracts
- Label definitions
- Timestamp/sequence semantics
- Shared configuration loaders
- Model artifact format
- Repository-wide dependency or build files

## 12. Testing Strategy

### Unit tests

- Message normalization
- Book updates and invariants
- Individual streaming features
- Label boundary conditions
- Cost and latency calculations
- Calibration and metric helpers

### Property-based tests

- Book levels remain ordered and quantities nonnegative
- Replay output is deterministic
- Future events cannot alter earlier features
- Increasing fees cannot improve otherwise identical net P&L
- Increasing execution latency cannot move a fill backward in time

### Integration tests

- Disconnect, reconnect, snapshot reload, and gap recovery
- Raw events through book, features, model, and API
- Python/C++ parity
- Model packaging, loading, and rollback

### Golden replay tests

Maintain a small committed event stream with expected:

- Book snapshots
- Feature vectors
- Labels
- Baseline predictions
- Simulated fills

Golden fixtures require an explicit migration note when intentionally changed.

### Performance tests

- Events processed per second
- End-to-end and component p50/p95/p99 latency
- Feature freshness
- Peak memory during replay
- Python/C++ parity and speed comparison

Performance tests should have generous CI smoke thresholds; publish rigorous benchmark results only from a documented stable environment.

## 13. Research and Evaluation Rules

- Split by contiguous time blocks, never randomly by row.
- Include an embargo or gap when overlapping prediction horizons could leak information across boundaries.
- Select features, horizons, thresholds, hyperparameters, and calibration methods without inspecting the final test period.
- Prefer multiple walk-forward test windows over one lucky period.
- Compare against market and modeling baselines, not just other complex models.
- Use block bootstrap or another dependence-aware method for uncertainty estimates.
- Report class prevalence and performance conditional on periods where a valid prediction was possible.
- Separate predictive significance from economic significance.
- Stress test fees, slippage, latency, threshold, and fill assumptions.
- Treat regime definitions as models that must also be fit without future information.
- Preserve all experiment configurations and summary outputs needed to reproduce tables and figures.

## 14. Risks and Mitigations

| Risk                                              | Mitigation                                                                 |
| ------------------------------------------------- | -------------------------------------------------------------------------- |
| Exchange feed gaps or ambiguous semantics         | Sequence validation, invalidation, resnapshot, and raw-event retention     |
| Severe label imbalance or excessive no-move cases | Volatility/spread-aware labels and appropriate probability metrics         |
| Look-ahead leakage                                | Causal feature API, chronological splits, explicit synthetic leakage tests |
| Strong autocorrelation inflates confidence        | Walk-forward testing and dependence-aware uncertainty estimates            |
| Apparent alpha disappears after costs             | Treat this as a valid result and focus on rigorous diagnosis               |
| Scope becomes unmanageable                        | One exchange/instrument/task until Milestone 6 is complete                 |
| Dashboard consumes time before research works     | Build it last, using stable output contracts                               |
| C++ adds complexity without value                 | Profile first and require parity/benchmark evidence                        |
| Live data is expensive or hard to redistribute    | Store local raw data; commit only small permitted fixtures and scripts     |
| Neural models overfit limited data                | Require simple baselines, ablations, and multi-period evaluation           |
| Results cannot be reproduced                      | Version schemas, manifests, configs, code commit, and seeds                |

## 15. Decision Log

Record decisions using this template:

```text
Date:
Decision:
Context:
Alternatives considered:
Reason:
Consequences:
Owner:
```

Initial decisions still required:

- [ ] Initial exchange and market-data channel
- [ ] Initial instrument
- [ ] Normalized event semantics
- [ ] Price/quantity integer scaling
- [ ] Primary prediction horizon and movement threshold selection procedure
- [ ] Storage partitioning and compression
- [x] Python dependency/build tooling
- [ ] C++/Python boundary
- [ ] Experiment tracking format

### Recorded decisions

```text
Date: 2026-09-21
Decision: Python package root is `src/market_engine/`, not bare `src/<module>/`.
Context: Section 6 sketches `src/ingestion/`, `src/features/`, etc. with no
  package namespace.
Alternatives considered: (a) flat layout as literally drawn; (b) a top-level
  `market_engine/` package with no `src/`.
Reason: A bare `src/` tree is not installable or importable as a unit, and
  generic names like `models/` and `api/` collide with third-party packages on
  `sys.path`. A `src/` layout additionally forces imports to resolve through the
  installed package rather than the working directory, so a test can never
  accidentally pass against uninstalled local files. That is a reproducibility
  guarantee, not a style preference (invariant 9).
Consequences: Imports are `market_engine.orderbook`, not `orderbook`. Working on
  the repo requires an editable install. Enforced by
  `tests/unit/test_skeleton.py::test_package_resolves_to_src_not_cwd`.
Owner: Milestone 0
```

```text
Date: 2026-09-21
Decision: Dependency and build tooling is stdlib `venv` + `pip` + a single
  `pyproject.toml`, with zero runtime dependencies at Milestone 0.
Context: Section 18 task 1 requires the skeleton "without adding unnecessary
  dependencies."
Alternatives considered: uv, Poetry, PDM, conda.
Reason: uv is measurably faster but is not installed on the development machine
  and adds a bootstrap step to the "one command sets up the environment"
  acceptance criterion. `pyproject.toml` is the common substrate for all of
  these, so migrating to uv later is a lockfile addition, not a rewrite. Runtime
  deps stay empty so that an environment fault cannot be mistaken for a code
  fault; each milestone adds only what it needs.
Consequences: No lockfile yet, so builds are not byte-reproducible across
  machines. Acceptable until Milestone 4, where model results start depending on
  library versions — revisit and pin before the first reported experiment.
Owner: Milestone 0
```

```text
Date: 2026-09-21
Decision: Defer all C++ build configuration to Milestone 7. `cpp/` exists as
  empty scaffolding; no CMake, no pybind11, no binding smoke test yet.
Context: Milestone 0 lists a C++ build config and binding smoke test. No C++
  toolchain or CMake is present on the development machine.
Alternatives considered: Install MSVC + CMake now and add a trivial binding.
Reason: Invariant 8 permits native code only after profiling identifies a
  bottleneck. There is no pipeline to profile yet, so a binding added now would
  be maintained across seven milestones while proving nothing, and would make the
  "clean checkout, one command" criterion depend on a compiler. Milestone 7 owns
  the toolchain setup as part of its benchmark methodology.
Consequences: Milestone 0's C++ task is intentionally left unchecked rather than
  treated as complete. CI stays Python-only until Milestone 7.
Owner: Milestone 0
```

## 16. Project-Level Definition of Done

The project is resume-ready when all of the following are true:

- [ ] A deterministic replay demo works from a clean checkout.
- [ ] A live feed can run through ingestion, book reconstruction, features, inference, and monitoring.
- [ ] Order-book correctness and point-in-time feature behavior are tested.
- [ ] At least three credible baselines are evaluated using walk-forward validation.
- [ ] Classification probabilities are calibrated and assessed with reliability metrics.
- [ ] Results are broken down by market regime.
- [ ] Execution results include conservative fees, spread, slippage, latency, and inventory assumptions.
- [ ] Python and C++ components have parity tests and published benchmarks.
- [ ] Drift can be detected in a controlled test and model versions can be rolled back.
- [ ] The dashboard communicates model behavior, system performance, and limitations.
- [ ] The final report answers the central research question without overstating results.
- [ ] README claims and resume bullets are backed by reproducible measurements.

## 17. Evidence to Capture for Future Resume Bullets

Do not invent numbers in advance. Instrument the system so the following can be measured:

- Total events collected and hours/days of continuous operation
- Sustained events processed per second
- End-to-end p50/p95/p99 inference latency
- Python-to-C++ throughput and latency improvement
- Number of order-book levels and streaming features maintained
- Number and length of walk-forward evaluation windows
- Calibration improvement over uncalibrated baselines
- Performance variation across regimes
- Effect of fees and latency on gross versus net simulated results
- Drift incidents detected and time to detection
- Test count, coverage for critical modules, and replay determinism

Potential final bullet structure:

> Engineered a real-time market-microstructure ML platform that processed **[measured rate]** order-book events per second, reconstructed **[depth]** price levels in C++, and served calibrated short-horizon predictions at **[measured p99 latency]**.

> Built leakage-safe walk-forward evaluation and an execution simulator incorporating fees, spread, slippage, partial fills, latency, and inventory constraints; quantified how signal performance changed across **[count]** market regimes and **[count]** test windows.

## 18. First Tasks

The next agent should begin with Milestone 0 and complete this sequence:

1. Create the repository skeleton without adding unnecessary dependencies.
2. Draft `AGENTS.md` with canonical setup, test, lint, build, and run commands.
3. Define versioned `MarketEvent` and `BookSnapshot` schemas.
4. Add a tiny hand-authored golden event fixture and schema-validation tests.
5. Implement a Python reference order book against the fixture.
6. Add deterministic replay and expected final-book tests.

Do not start model training until the replayed book and feature timestamps are demonstrably correct.
