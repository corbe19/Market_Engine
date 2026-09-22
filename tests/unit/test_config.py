from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from market_engine.config import ENV_CONFIG_PATH, Config, describe_defaults, load_config

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS = REPO_ROOT / "configs"


def test_defaults_when_nothing_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_CONFIG_PATH, raising=False)
    cfg = load_config()
    assert cfg == Config()
    assert cfg.run.seed == 0
    assert cfg.paths.data_root == Path("data")


def test_yaml_file_overrides_defaults(tmp_path: Path) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("run:\n  seed: 7\n  log_format: json\n", encoding="utf-8")
    cfg = load_config(file)
    assert cfg.run.seed == 7
    assert cfg.run.log_format == "json"
    # Untouched sections keep their defaults.
    assert cfg.paths == Config().paths


def test_env_var_selects_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("run:\n  seed: 99\n", encoding="utf-8")
    monkeypatch.setenv(ENV_CONFIG_PATH, str(file))
    assert load_config().run.seed == 99


def test_explicit_path_beats_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "env.yaml"
    env_file.write_text("run:\n  seed: 1\n", encoding="utf-8")
    explicit = tmp_path / "explicit.yaml"
    explicit.write_text("run:\n  seed: 2\n", encoding="utf-8")
    monkeypatch.setenv(ENV_CONFIG_PATH, str(env_file))
    assert load_config(explicit).run.seed == 2


def test_overrides_deep_merge_on_top_of_file(tmp_path: Path) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("run:\n  seed: 7\n  log_level: DEBUG\n", encoding="utf-8")
    cfg = load_config(file, overrides={"run": {"seed": 8}})
    assert cfg.run.seed == 8
    assert cfg.run.log_level == "DEBUG"  # sibling key from the file survives


def test_unknown_key_is_an_error(tmp_path: Path) -> None:
    """A typo must fail loudly, never silently fall back to a default."""
    file = tmp_path / "c.yaml"
    file.write_text("run:\n  sede: 7\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="sede"):
        load_config(file)


def test_unknown_section_is_an_error(tmp_path: Path) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("runs:\n  seed: 7\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="runs"):
        load_config(file)


def test_invalid_value_is_an_error(tmp_path: Path) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("run:\n  log_format: xml\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="log_format"):
        load_config(file)


def test_config_is_frozen() -> None:
    cfg = Config()
    with pytest.raises(ValidationError):
        cfg.run.seed = 5  # type: ignore[misc]


def test_empty_file_means_defaults(tmp_path: Path) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("# nothing here\n", encoding="utf-8")
    assert load_config(file) == Config()


def test_non_mapping_top_level_is_an_error(tmp_path: Path) -> None:
    file = tmp_path / "c.yaml"
    file.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(TypeError, match="mapping"):
        load_config(file)


@pytest.mark.parametrize("name", ["development", "research", "production"])
def test_shipped_profiles_load(name: str) -> None:
    load_config(CONFIGS / f"{name}.yaml")


def test_development_profile_matches_code_defaults() -> None:
    """configs/development.yaml embeds describe_defaults() verbatim.

    If this fails, a field was added or its default/description changed
    without regenerating the file. Regenerate; do not edit by hand.
    """
    text = (CONFIGS / "development.yaml").read_text(encoding="utf-8")
    assert describe_defaults() in text
    assert load_config(CONFIGS / "development.yaml") == Config()
