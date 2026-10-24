"""Unit tests for Data Quality and Schema Drift validation engines."""

from src.validation.quality_engine import CheckStatus, CheckType, DataQualityValidator
from src.validation.schema_drift import (
    ColumnDef,
    SchemaChangeType,
    SchemaDriftInspector,
)


class TestDataQualityValidator:
    def setup_method(self):
        self.validator = DataQualityValidator(
            pipeline_id="orders",
            table_name="orders_silver",
            run_id="run-test-001",
        )

    def test_null_check_pass(self):
        res = self.validator.check_null_ratio(
            column_name="customer_id",
            null_count=2,
            total_count=100,
            threshold=0.05,
        )
        assert res.status == CheckStatus.PASS
        assert res.actual_value == 0.02
        assert res.check_type == CheckType.COMPLETENESS

    def test_null_check_fail(self):
        res = self.validator.check_null_ratio(
            column_name="customer_id",
            null_count=15,
            total_count=100,
            threshold=0.05,
        )
        assert res.status == CheckStatus.FAIL
        assert res.actual_value == 0.15
        assert res.severity in ("P1", "P2")

    def test_duplicate_check(self):
        res = self.validator.check_duplicate_ratio(
            key_column="order_id",
            duplicate_count=1,
            total_count=100,
            threshold=0.02,
        )
        assert res.status == CheckStatus.PASS

        res_fail = self.validator.check_duplicate_ratio(
            key_column="order_id",
            duplicate_count=10,
            total_count=100,
            threshold=0.02,
        )
        assert res_fail.status == CheckStatus.FAIL

    def test_volume_bounds_check(self):
        res = self.validator.check_volume_bounds(
            actual_rows=950,
            expected_rows=1000,
            lower_bound_pct=0.80,
            upper_bound_pct=1.20,
        )
        assert res.status == CheckStatus.PASS

        # Severe drop (e.g. 48% drop)
        res_drop = self.validator.check_volume_bounds(
            actual_rows=400,
            expected_rows=1000,
            lower_bound_pct=0.80,
            upper_bound_pct=1.20,
        )
        assert res_drop.status == CheckStatus.FAIL
        assert res_drop.severity == "P1"


class TestSchemaDriftInspector:
    def setup_method(self):
        self.base_schema = {
            "order_id": ColumnDef("order_id", "STRING", False),
            "customer_id": ColumnDef("customer_id", "STRING", False),
            "amount": ColumnDef("amount", "FLOAT", False),
        }

    def test_identical_schema(self):
        diff = SchemaDriftInspector.compare(self.base_schema, self.base_schema)
        assert diff.change_type == SchemaChangeType.NONE
        assert diff.is_safe_to_auto_migrate is True

    def test_additive_schema(self):
        observed = dict(self.base_schema)
        observed["phone"] = ColumnDef("phone", "STRING", True)
        diff = SchemaDriftInspector.compare(self.base_schema, observed)
        assert diff.change_type == SchemaChangeType.ADDITIVE
        assert diff.severity == "P3"
        assert diff.is_safe_to_auto_migrate is True
        assert len(diff.added_columns) == 1

    def test_breaking_type_change(self):
        observed = dict(self.base_schema)
        observed["amount"] = ColumnDef("amount", "STRING", False)  # FLOAT -> STRING
        diff = SchemaDriftInspector.compare(self.base_schema, observed)
        assert diff.change_type == SchemaChangeType.BREAKING
        assert diff.severity == "P1"
        assert diff.is_safe_to_auto_migrate is False
        assert len(diff.modified_columns) == 1

    def test_column_removal(self):
        observed = {
            "order_id": ColumnDef("order_id", "STRING", False),
            "customer_id": ColumnDef("customer_id", "STRING", False),
        }  # 'amount' dropped
        diff = SchemaDriftInspector.compare(self.base_schema, observed)
        assert diff.change_type == SchemaChangeType.BREAKING
        assert diff.severity == "P1"
        assert len(diff.removed_columns) == 1

    def test_pii_exposure_triggers_p0(self):
        observed = dict(self.base_schema)
        observed["customer_ssn"] = ColumnDef("customer_ssn", "STRING", True)
        diff = SchemaDriftInspector.compare(self.base_schema, observed)
        assert diff.change_type == SchemaChangeType.PII_EXPOSURE
        assert diff.severity == "P0"
        assert diff.is_safe_to_auto_migrate is False
