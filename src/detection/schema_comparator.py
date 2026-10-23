# ==============================================================================
# Data Pipeline Immune System — Schema Comparator
# ==============================================================================
"""Compares schema snapshots across runs and evaluates drift hazards."""

from __future__ import annotations

from typing import Dict

from src.validation.schema_drift import (
    ColumnDef,
    SchemaDiffResult,
    SchemaDriftInspector,
)


class SchemaComparator:
    """Detects schema drift between baseline and incoming runs."""

    def compare_schemas(
        self,
        baseline: Dict[str, ColumnDef],
        observed: Dict[str, ColumnDef],
    ) -> SchemaDiffResult:
        """Executes full schema comparison returning structured diff."""
        return SchemaDriftInspector.compare(baseline, observed)
