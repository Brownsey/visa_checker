"""Tests for configuration loading and validation."""
import os
import textwrap
from pathlib import Path

import pytest

from visa_checker.config.settings import ConfigValidationError, load_settings


def test_load_valid_config(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(textwrap.dedent("""\
        targets:
          - country: France
            provider: tlscontact
            centre: London
            visa_type: short_stay
            earliest_date: "2026-06-01"
            latest_date: "2026-09-30"
        polling:
          interval_seconds: 60
    """))
    settings = load_settings(str(config))
    assert len(settings.targets) == 1
    assert settings.targets[0].country == "France"


def test_missing_file_raises():
    with pytest.raises(ConfigValidationError, match="not found"):
        load_settings("/nonexistent/path/config.yaml")


def test_invalid_dates_raises(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(textwrap.dedent("""\
        targets:
          - country: France
            provider: tlscontact
            centre: London
            earliest_date: "2026-09-30"
            latest_date: "2026-06-01"
    """))
    with pytest.raises(ConfigValidationError):
        load_settings(str(config))


def test_env_var_interpolation(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_TELEGRAM_TOKEN", "abc123")
    config = tmp_path / "config.yaml"
    config.write_text(textwrap.dedent("""\
        targets:
          - country: Germany
            provider: vfs_global
            centre: London
            earliest_date: "2026-06-01"
            latest_date: "2026-09-30"
        alerts:
          telegram:
            enabled: true
            bot_token: ${TEST_TELEGRAM_TOKEN}
            chat_id: "12345"
    """))
    settings = load_settings(str(config))
    assert settings.alerts.telegram.bot_token == "abc123"


def test_empty_targets_raises(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("targets: []\n")
    with pytest.raises(ConfigValidationError):
        load_settings(str(config))
