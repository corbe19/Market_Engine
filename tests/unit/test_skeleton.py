"""Skeleton checks.

These exist so that a broken environment (missing editable install, wrong
interpreter, shadowed package name) fails loudly and immediately rather than
surfacing later as a confusing failure inside real tests.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import market_engine

PIPELINE_SUBPACKAGES = [
    "api",
    "execution",
    "features",
    "ingestion",
    "labels",
    "models",
    "monitoring",
    "orderbook",
    "regimes",
    "replay",
]


def test_package_is_installed_and_versioned() -> None:
    assert market_engine.__version__


def test_package_resolves_to_src_not_cwd() -> None:
    """Guards the src layout: importing must not pick up a stray local dir."""
    module_file = market_engine.__file__
    assert module_file is not None
    assert Path(module_file).parent.parent.name == "src"


@pytest.mark.parametrize("name", PIPELINE_SUBPACKAGES)
def test_pipeline_subpackage_imports(name: str) -> None:
    assert importlib.import_module(f"market_engine.{name}")
