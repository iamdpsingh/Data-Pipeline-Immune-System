"""Unit tests for configuration loader and environment settings."""

import pytest
from src.config.settings import load_settings


def test_load_settings_dev():
    settings = load_settings("dev")
    assert settings.environment == "dev"
    assert settings.project.id == "data-pipeline-immune-system"
    assert settings.project.dataset == "dpis_dev"
    assert settings.failure_injection.enabled is True
    assert settings.detection.row_count_zscore_threshold == 2.0
    assert settings.remediation.max_retry_count == 3


def test_load_settings_staging():
    settings = load_settings("staging")
    assert settings.environment == "staging"
    assert settings.project.id == "dpis-staging"
    assert settings.project.dataset == "dpis_staging"
    assert settings.failure_injection.enabled is False
    assert settings.detection.row_count_zscore_threshold == 3.0


def test_load_settings_production():
    settings = load_settings("production")
    assert settings.environment == "production"
    assert settings.project.id == "dpis-prod"
    assert settings.project.dataset == "dpis_prod"
    assert settings.failure_injection.enabled is False
    assert settings.detection.row_count_zscore_threshold == 3.0
    assert settings.remediation.quarantine_max_percentage == 0.05


def test_load_settings_invalid_env():
    with pytest.raises(ValueError, match="Invalid ENVIRONMENT"):
        load_settings("unknown_env")
