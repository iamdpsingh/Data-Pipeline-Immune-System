"""
Never-allow rule enforcement.

This module is the hard boundary that prevents the LLM or any other component
from executing actions that could cause irreversible damage.

The never-allow list here is the source of truth in CODE. The same list
appears in rules/safety_rules.yaml for documentation purposes, but this
file is what actually gets enforced at runtime.

If the two lists are ever inconsistent, the code wins. The YAML is for
human readability — this file is for machine enforcement.

Adding to the never-allow list requires a code change + code review.
It cannot be changed via configuration file alone. That is intentional.
"""

from __future__ import annotations

# Actions that are blocked unconditionally, regardless of:
# - AI confidence score
# - Diagnosis result
# - Human approval
# - Any configuration flag
#
# If you think a new action belongs here, it almost certainly does.
# If you think something should be removed from here, be very sure.
NEVER_ALLOW_ACTIONS: frozenset[str] = frozenset(
    {
        "DELETE_PRODUCTION_TABLE",
        "DROP_SCHEMA",
        "EXECUTE_ARBITRARY_SQL",
        "MODIFY_IAM_PERMISSION",
        "DISABLE_VALIDATION",
        "BYPASS_QUALITY_GATE",
        "EXPOSE_PII_COLUMN",
        "MODIFY_FINANCIAL_RECORD",
        "DELETE_QUARANTINE_TABLE",
        "DELETE_INCIDENT_MEMORY",
        "TRUNCATE_GOLD_TABLE",
        "MODIFY_GOLD_TABLE_SCHEMA",
        "GRANT_PUBLIC_ACCESS",
        "DISABLE_AUDIT_LOGGING",
    }
)


def check_never_allow(action: str) -> bool:
    """
    Returns True if the action is unconditionally blocked.

    Call this before any other risk check. If this returns True,
    the action must not proceed regardless of what else the system says.

    Usage:
        if check_never_allow(proposed_action):
            raise NeverAllowViolation(f"Action {proposed_action} is never-allow.")
    """
    return action in NEVER_ALLOW_ACTIONS


class NeverAllowViolation(Exception):
    """
    Raised when a never-allow action is attempted.

    This should propagate up to the controller, which will:
    - Log the violation with full context
    - Mark the incident as BLOCKED
    - Alert immediately
    """

    pass
