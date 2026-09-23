"""Typed, validated, immutable configuration.

Layering, later wins::

    built-in defaults  ->  YAML file  ->  explicit ``overrides`` dict

Two rules matter more than the rest:

* **Unknown keys are errors.** A misspelled key must not silently fall back
  to a default, because the experiment record would then claim a setting that
  never applied (``plan.md`` invariant 9).
* **Config is frozen.** Nothing may mutate it after load, so the value recorded
  in a run manifest is the value every component actually saw.

Every field carries a ``description``; ``describe_defaults()`` renders them so
the ``configs/*.yaml`` files and this module cannot drift apart unnoticed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

ENV_CONFIG_PATH = "MARKET_ENGINE_CONFIG"
"""Environment variable naming the YAML file to load when no path is given."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RunConfig(_Strict):
    seed: int = Field(
        default=0,
        ge=0,
        description="Global RNG seed. Recorded in every run manifest.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Minimum severity emitted by the root logger.",
    )
    log_format: Literal["console", "json"] = Field(
        default="console",
        description=(
            "'console' is human-readable for development; 'json' is one object "
            "per line for anything that will be searched or shipped."
        ),
    )


class PathsConfig(_Strict):
    data_root: Path = Field(
        default=Path("data"),
        description="Root for raw/, processed/, samples/. Relative to the working directory.",
    )
    artifacts_root: Path = Field(
        default=Path("artifacts"),
        description="Root for models/, metrics/, figures/. Relative to the working directory.",
    )


class Config(_Strict):
    run: RunConfig = Field(default_factory=RunConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)


def load_config(
    path: str | os.PathLike[str] | None = None,
    *,
    overrides: dict[str, Any] | None = None,
) -> Config:
    """Build a :class:`Config`.

    ``path`` defaults to ``$MARKET_ENGINE_CONFIG``; if neither is set, built-in
    defaults are used. ``overrides`` is deep-merged on top and is intended for
    CLI flags and tests, not for a second config file.
    """
    raw: dict[str, Any] = {}

    resolved = Path(path) if path is not None else _path_from_env()
    if resolved is not None:
        raw = _read_yaml(resolved)

    if overrides:
        raw = _deep_merge(raw, overrides)

    return Config.model_validate(raw)


def describe_defaults() -> str:
    """Render every field with its default and description, as YAML comments.

    Used to generate the reference block in ``configs/development.yaml`` and
    by a test that fails if that file falls out of date.
    """
    lines: list[str] = []
    for section_name, section_field in Config.model_fields.items():
        section_type = section_field.annotation
        assert isinstance(section_type, type) and issubclass(section_type, BaseModel)
        lines.append(f"{section_name}:")
        for name, field in section_type.model_fields.items():
            default = field.get_default(call_default_factory=True)
            # Dump as a one-key mapping so YAML applies its own quoting rules.
            rendered = yaml.safe_dump({name: _to_yaml_scalar(default)}).strip()
            lines.append(f"  # {field.description}")
            lines.append(f"  {rendered}")
    return "\n".join(lines) + "\n"


def _path_from_env() -> Path | None:
    value = os.environ.get(ENV_CONFIG_PATH)
    return Path(value) if value else None


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise TypeError(f"{path}: top level must be a mapping, got {type(loaded).__name__}")
    return loaded


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _to_yaml_scalar(value: object) -> object:
    # PurePath is not a YAML-native type; everything else we use is.
    return str(value) if isinstance(value, Path) else value
