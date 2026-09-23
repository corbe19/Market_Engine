"""Run every static check and the test suite; exit non-zero if any fail.

This is the single command behind Milestone 0's acceptance criterion and is
exactly what CI runs, so a green local run predicts a green CI run.

    python scripts/check.py          # check everything
    python scripts/check.py --fix    # apply ruff auto-fixes and formatting first
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

Step = tuple[str, list[str]]

CHECKS: list[Step] = [
    ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("mypy", [sys.executable, "-m", "mypy"]),
    ("pytest", [sys.executable, "-m", "pytest"]),
]

FIXES: list[Step] = [
    ("ruff check --fix", [sys.executable, "-m", "ruff", "check", "--fix", "."]),
    ("ruff format", [sys.executable, "-m", "ruff", "format", "."]),
]


def run(steps: list[Step]) -> list[tuple[str, int, float]]:
    results: list[tuple[str, int, float]] = []
    for name, cmd in steps:
        print(f"\n=== {name} ===", flush=True)
        started = time.perf_counter()
        code = subprocess.run(cmd, cwd=ROOT, check=False).returncode
        results.append((name, code, time.perf_counter() - started))
    return results


def main(argv: list[str]) -> int:
    if "--fix" in argv:
        run(FIXES)

    results = run(CHECKS)

    print("\n=== summary ===")
    for name, code, seconds in results:
        status = "ok  " if code == 0 else "FAIL"
        print(f"  {status}  {name:<14} {seconds:6.1f}s")

    return 0 if all(code == 0 for _, code, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
