"""
Tests for the never-allow rule enforcement.

These are safety-critical tests. If any of these fail, the core safety
guarantee of the system is broken. These must pass on every CI run.

The never-allow list exists because AI confidence scores cannot be the
only safety mechanism. An LLM can be confidently wrong. For actions with
irreversible consequences, the enforcement must be in deterministic code.
"""

import pytest

from src.risk.never_allow import check_never_allow, NeverAllowViolation, NEVER_ALLOW_ACTIONS


@pytest.mark.safety_critical
class TestNeverAllowRules:
    """
    Verifies that never-allow actions are blocked unconditionally.
    These tests are not exhaustive of all possible inputs — they test
    the specific actions that must be blocked.
    """

    def test_delete_production_table_is_blocked(self):
        assert check_never_allow("DELETE_PRODUCTION_TABLE") is True

    def test_execute_arbitrary_sql_is_blocked(self):
        assert check_never_allow("EXECUTE_ARBITRARY_SQL") is True

    def test_modify_iam_is_blocked(self):
        assert check_never_allow("MODIFY_IAM_PERMISSION") is True

    def test_expose_pii_is_blocked(self):
        assert check_never_allow("EXPOSE_PII_COLUMN") is True

    def test_disable_validation_is_blocked(self):
        assert check_never_allow("DISABLE_VALIDATION") is True

    def test_modify_financial_record_is_blocked(self):
        assert check_never_allow("MODIFY_FINANCIAL_RECORD") is True

    def test_drop_schema_is_blocked(self):
        assert check_never_allow("DROP_SCHEMA") is True

    def test_safe_action_is_not_blocked(self):
        """Make sure we're not over-blocking legitimate actions."""
        assert check_never_allow("RETRY_TASK") is False

    def test_safe_action_reprocess_partition(self):
        assert check_never_allow("REPROCESS_PARTITION") is False

    def test_safe_action_retry_source_extraction(self):
        assert check_never_allow("RETRY_SOURCE_EXTRACTION") is False

    def test_unknown_action_is_not_in_never_allow(self):
        """
        Unknown actions should NOT be in the never-allow list.
        They are blocked via a different mechanism (unknown actions
        don't appear in the approved action library, so they can't
        be executed regardless).
        """
        assert check_never_allow("COMPLETELY_MADE_UP_ACTION_XYZ") is False

    def test_never_allow_list_is_immutable(self):
        """
        The frozenset cannot be modified at runtime.
        This test documents the intended immutability of the list.
        """
        with pytest.raises((AttributeError, TypeError)):
            NEVER_ALLOW_ACTIONS.add("SOME_NEW_ACTION")  # type: ignore
