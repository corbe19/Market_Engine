# Data directory

## Layout

| Path              | Contents                                               | Tracked by Git |
| ----------------- | ------------------------------------------------------ | -------------- |
| `data/raw/`       | Append-only normalized exchange events, as captured     | No             |
| `data/processed/` | Derived datasets: feature/label tables, manifests       | No             |
| `data/samples/`   | Small hand-authored or sanitized fixtures used by tests | **Yes**        |

## Why raw data is not committed

1. **Size.** One liquid instrument produces on the order of millions of book
   events per day. This does not belong in Git history.
2. **Redistribution.** Exchange market data is generally licensed for use, not
   for republication. Capturing it locally for research is normally fine;
   mirroring it in a public repository is not.
3. **Reproducibility does not require it.** Results are reproduced from a
   *dataset manifest* (time range, instrument, schema version, code commit,
   config, seed) plus a collector that can re-capture or a replay log held
   locally. See `plan.md` invariant 9.

`data/samples/` is the exception: fixtures there must be small, deterministic,
and either hand-authored or derived from a short public window, so that a clean
checkout can run the full test suite and the replay demo with no network access.

## Retention

Raw capture is local and disposable. Delete or archive `data/raw/` partitions
freely — but only after any experiment depending on them has recorded its
results and manifest under `artifacts/` or `research/experiments/`.

## Privacy

Public market data contains no personal information: it describes anonymous
aggregate price levels and executed trades, not identified counterparties.

Two things that would change that, and are therefore prohibited here:

- **Never** commit API keys, secrets, or authenticated private endpoints. Only
  public market-data channels are used. Credentials belong in a local `.env`
  (git-ignored) or the environment.
- **Never** capture account-scoped streams (own orders, fills, balances). They
  are personal financial data and out of scope for this project.
