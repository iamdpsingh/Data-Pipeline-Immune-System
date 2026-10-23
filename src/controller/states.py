# ==============================================================================
# Data Pipeline Immune System — Incident State Machine (ADR-010)
# ==============================================================================
"""Enforces valid state transitions throughout the incident lifecycle.

States:
  DETECTED -> CLASSIFIED -> DIAGNOSED -> RISK_ASSESSED -> ACTION_SELECTED ->
  REMEDIATION -> VERIFICATION -> RESOLVED
  |
  +-> BLOCKED (from RISK_ASSESSED on never-allow violations)
  +-> ESCALATED (from any state on unresolvable failure or manual override)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Set


class IncidentState(str, Enum):
    DETECTED = "DETECTED"
    CLASSIFIED = "CLASSIFIED"
    DIAGNOSED = "DIAGNOSED"
    RISK_ASSESSED = "RISK_ASSESSED"
    ACTION_SELECTED = "ACTION_SELECTED"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"
    RESOLVED = "RESOLVED"
    BLOCKED = "BLOCKED"
    ESCALATED = "ESCALATED"


# Valid state transitions dictionary
VALID_TRANSITIONS: Dict[IncidentState, Set[IncidentState]] = {
    IncidentState.DETECTED: {IncidentState.CLASSIFIED, IncidentState.ESCALATED},
    IncidentState.CLASSIFIED: {IncidentState.DIAGNOSED, IncidentState.ESCALATED},
    IncidentState.DIAGNOSED: {IncidentState.RISK_ASSESSED, IncidentState.ESCALATED},
    IncidentState.RISK_ASSESSED: {
        IncidentState.ACTION_SELECTED,
        IncidentState.BLOCKED,
        IncidentState.ESCALATED,
    },
    IncidentState.ACTION_SELECTED: {IncidentState.REMEDIATION, IncidentState.ESCALATED},
    IncidentState.REMEDIATION: {IncidentState.VERIFICATION, IncidentState.ESCALATED},
    IncidentState.VERIFICATION: {
        IncidentState.RESOLVED,
        IncidentState.DIAGNOSED,  # Re-diagnose if verification reveals hidden root cause
        IncidentState.ESCALATED,
    },
    IncidentState.RESOLVED: set(),
    IncidentState.BLOCKED: {IncidentState.ESCALATED},
    IncidentState.ESCALATED: {IncidentState.ACTION_SELECTED, IncidentState.RESOLVED},
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal transition is attempted in the incident state machine."""
    pass


def transition(current_state: IncidentState, next_state: IncidentState) -> IncidentState:
    """Validates and applies a state transition."""
    allowed = VALID_TRANSITIONS.get(current_state, set())
    if next_state not in allowed:
        raise InvalidStateTransitionError(
            f"Illegal state transition from {current_state.value} to {next_state.value}. Allowed: {[s.value for s in allowed]}"
        )
    return next_state
