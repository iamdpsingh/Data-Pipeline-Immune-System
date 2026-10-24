# ==============================================================================
# Data Pipeline Immune System — Schema Drift & Safety Inspector
# ==============================================================================
"""Inspects schema snapshots across pipeline executions to detect drift.

Categorizes schema changes into:
- NONE: No alterations detected.
- ADDITIVE: New non-breaking nullable columns introduced (P3 severity).
- BREAKING: Existing column removed or data type mutated (P1 severity).
- PII_EXPOSURE: New column matching PII keywords (P0 Critical Boundary).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SchemaChangeType(str, Enum):
    NONE = "NONE"
    ADDITIVE = "ADDITIVE"
    BREAKING = "BREAKING"
    PII_EXPOSURE = "PII_EXPOSURE"


PII_PATTERNS = [
    re.compile(r".*ssn.*", re.IGNORECASE),
    re.compile(r".*social_security.*", re.IGNORECASE),
    re.compile(r".*credit_card.*", re.IGNORECASE),
    re.compile(r".*card_number.*", re.IGNORECASE),
    re.compile(r".*password.*", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*cvv.*", re.IGNORECASE),
]


@dataclass(frozen=True)
class ColumnDef:
    name: str
    type: str
    nullable: bool = True


@dataclass(frozen=True)
class SchemaDiffResult:
    change_type: SchemaChangeType
    severity: str  # P0, P1, P3, or NONE
    added_columns: list[ColumnDef]
    removed_columns: list[ColumnDef]
    modified_columns: list[dict[str, Any]]
    is_safe_to_auto_migrate: bool
    summary_message: str


class SchemaDriftInspector:
    """Compares baseline schema against observed landing schema."""

    @staticmethod
    def contains_pii(column_name: str) -> bool:
        """Returns True if column name matches known PII sensitive patterns."""
        return any(pattern.match(column_name) for pattern in PII_PATTERNS)

    @classmethod
    def compare(
        cls,
        baseline_schema: dict[str, ColumnDef],
        observed_schema: dict[str, ColumnDef],
    ) -> SchemaDiffResult:
        """Compares baseline column definitions to observed definitions."""
        baseline_keys = set(baseline_schema.keys())
        observed_keys = set(observed_schema.keys())

        added_keys = observed_keys - baseline_keys
        removed_keys = baseline_keys - observed_keys
        common_keys = baseline_keys & observed_keys

        # Check for PII introduction in newly added columns
        for key in added_keys:
            if cls.contains_pii(key):
                return SchemaDiffResult(
                    change_type=SchemaChangeType.PII_EXPOSURE,
                    severity="P0",
                    added_columns=[observed_schema[key]],
                    removed_columns=[],
                    modified_columns=[],
                    is_safe_to_auto_migrate=False,
                    summary_message=f"CRITICAL: Column '{key}' matches sensitive PII pattern. Auto-remediation prohibited.",
                )

        added_cols = [observed_schema[k] for k in added_keys]
        removed_cols = [baseline_schema[k] for k in removed_keys]

        modified_cols = []
        for key in common_keys:
            base_col = baseline_schema[key]
            obs_col = observed_schema[key]
            if base_col.type != obs_col.type:
                modified_cols.append(
                    {
                        "column": key,
                        "old_type": base_col.type,
                        "new_type": obs_col.type,
                    }
                )

        # Evaluate breaking vs additive
        if removed_cols or modified_cols:
            return SchemaDiffResult(
                change_type=SchemaChangeType.BREAKING,
                severity="P1",
                added_columns=added_cols,
                removed_columns=removed_cols,
                modified_columns=modified_cols,
                is_safe_to_auto_migrate=False,
                summary_message=(
                    f"BREAKING schema change detected: {len(removed_cols)} columns dropped, "
                    f"{len(modified_cols)} columns changed type. Requires human review."
                ),
            )

        if added_cols:
            return SchemaDiffResult(
                change_type=SchemaChangeType.ADDITIVE,
                severity="P3",
                added_columns=added_cols,
                removed_columns=[],
                modified_columns=[],
                is_safe_to_auto_migrate=True,
                summary_message=f"ADDITIVE non-breaking change: {len(added_cols)} new columns observed.",
            )

        return SchemaDiffResult(
            change_type=SchemaChangeType.NONE,
            severity="NONE",
            added_columns=[],
            removed_columns=[],
            modified_columns=[],
            is_safe_to_auto_migrate=True,
            summary_message="Schemas are identical.",
        )
