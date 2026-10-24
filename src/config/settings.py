# ==============================================================================
# Data Pipeline Immune System — Configuration Loader
# ==============================================================================
"""Configuration loader for the Data Pipeline Immune System.

Loads environment-specific settings (dev, staging, production) from YAML
configuration files, validating thresholds, SLAs, and safety parameters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class ProjectConfig:
    id: str
    dataset: str
    location: str


@dataclass(frozen=True)
class GCSConfig:
    source_bucket: str
    bronze_bucket: str
    quarantine_bucket: str


@dataclass(frozen=True)
class DetectionConfig:
    row_count_zscore_threshold: float
    min_baseline_runs: int
    baseline_lookback_days: int
    freshness_sla_minutes: int | None = None


@dataclass(frozen=True)
class QualityConfig:
    null_threshold: float
    duplicate_threshold: float
    volume_lower_bound: float
    volume_upper_bound: float


@dataclass(frozen=True)
class HealthScoreConfig:
    weights: dict[str, float]
    thresholds: dict[str, int]


@dataclass(frozen=True)
class AgentsConfig:
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    diagnosis_timeout_seconds: int


@dataclass(frozen=True)
class RemediationConfig:
    max_retry_count: int
    retry_backoff_base_seconds: int
    quarantine_max_percentage: float


@dataclass(frozen=True)
class FailureInjectionConfig:
    enabled: bool


@dataclass(frozen=True)
class Settings:
    environment: str
    project: ProjectConfig
    gcs: GCSConfig
    detection: DetectionConfig
    quality: QualityConfig
    health_score: HealthScoreConfig
    agents: AgentsConfig
    remediation: RemediationConfig
    failure_injection: FailureInjectionConfig
    logging_level: str


def find_config_dir() -> Path:
    """Finds the configuration directory searching upwards from current file."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        config_path = parent / "config"
        if config_path.is_dir() and (config_path / "dev.yaml").exists():
            return config_path
    # Fallback to local config relative to repo root
    return Path("config").resolve()


def load_settings(env: str | None = None) -> Settings:
    """Loads configuration for the specified or environment-selected target."""
    target_env = env or os.getenv("ENVIRONMENT", "dev").lower()
    if target_env not in ("dev", "staging", "production"):
        raise ValueError(
            f"Invalid ENVIRONMENT '{target_env}'. Must be dev, staging, or production."
        )

    config_dir = find_config_dir()
    config_file = config_dir / f"{target_env}.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_file}")

    with open(config_file, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    raw_freshness = data["detection"].get("freshness_sla_minutes")
    freshness_sla = int(raw_freshness) if raw_freshness is not None else None

    return Settings(
        environment=target_env,
        project=ProjectConfig(
            id=data["project"]["id"],
            dataset=data["project"]["dataset"],
            location=data["project"].get("location", "us-central1"),
        ),
        gcs=GCSConfig(
            source_bucket=data["gcs"]["source_bucket"],
            bronze_bucket=data["gcs"]["bronze_bucket"],
            quarantine_bucket=data["gcs"]["quarantine_bucket"],
        ),
        detection=DetectionConfig(
            row_count_zscore_threshold=float(
                data["detection"]["row_count_zscore_threshold"]
            ),
            min_baseline_runs=int(data["detection"]["min_baseline_runs"]),
            baseline_lookback_days=int(data["detection"]["baseline_lookback_days"]),
            freshness_sla_minutes=freshness_sla,
        ),
        quality=QualityConfig(
            null_threshold=float(data["quality"]["null_threshold"]),
            duplicate_threshold=float(data["quality"]["duplicate_threshold"]),
            volume_lower_bound=float(data["quality"]["volume_lower_bound"]),
            volume_upper_bound=float(data["quality"]["volume_upper_bound"]),
        ),
        health_score=HealthScoreConfig(
            weights=dict(data["health_score"]["weights"]),
            thresholds=dict(data["health_score"]["thresholds"]),
        ),
        agents=AgentsConfig(
            llm_model=data["agents"]["llm_model"],
            llm_temperature=float(data["agents"]["llm_temperature"]),
            llm_max_tokens=int(data["agents"]["llm_max_tokens"]),
            diagnosis_timeout_seconds=int(data["agents"]["diagnosis_timeout_seconds"]),
        ),
        remediation=RemediationConfig(
            max_retry_count=int(data["remediation"]["max_retry_count"]),
            retry_backoff_base_seconds=int(
                data["remediation"]["retry_backoff_base_seconds"]
            ),
            quarantine_max_percentage=float(
                data["remediation"]["quarantine_max_percentage"]
            ),
        ),
        failure_injection=FailureInjectionConfig(
            enabled=bool(data.get("failure_injection", {}).get("enabled", False)),
        ),
        logging_level=data.get("logging", {}).get("level", "INFO"),
    )
