# ==============================================================================
# Data Pipeline Immune System — Risk Assessment Agent (Phase 7)
# ==============================================================================
"""Determines whether an incident remediation action is safe to auto-execute.

Permissions: READ ONLY
Inputs: DiagnosisResult
Outputs: RiskAssessment (risk level, auto-remediable, human approval, blocked)

Architecture:
- ADR-002: Read-only safety agent.
- ADR-004: Confidence score never overrides safety rules or never-allow boundaries.
- Default-to-safe principle: Ambiguity or unhandled cases mandate human approval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from agents.diagnosis_agent import DiagnosisResult
from src.config.settings import Settings, load_settings
from src.risk.never_allow import check_never_allow
from src.risk.safety_rules import ActionPolicy, SafetyRulesLoader

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    NEVER_ALLOW = "NEVER_ALLOW"


@dataclass(frozen=True)
class RiskInput:
    incident_id: str
    diagnosis_result: DiagnosisResult


@dataclass(frozen=True)
class RiskAssessment:
    incident_id: str
    risk_level: RiskLevel
    auto_remediable: bool
    requires_human_approval: bool
    blocked: bool
    block_reason: str | None
    approved_action: str | None
    assessed_at: str


class RiskAgent:
    """Evaluates proposed remediation actions against never-allow and safety policies."""

    def __init__(
        self,
        settings: Settings | None = None,
        safety_rules: SafetyRulesLoader | None = None,
    ):
        self.settings = settings or load_settings()
        self.safety_rules = safety_rules or SafetyRulesLoader()

    def assess(self, input_data: RiskInput) -> RiskAssessment:
        """Evaluates remediation action risk and produces safety authorization."""
        now_str = datetime.now(UTC).isoformat()
        diag = input_data.diagnosis_result
        action = diag.recommended_action

        logger.info(
            "RiskAgent assessing incident=%s action='%s' cause='%s' confidence=%.2f",
            input_data.incident_id,
            action,
            diag.root_cause,
            diag.confidence,
        )

        # 1. Hard Never-Allow Boundary Check (ADR-004) & PII Block
        if (
            check_never_allow(action)
            or action == "BLOCK_PIPELINE"
            or diag.root_cause == "PII_EXPOSURE_RISK"
        ):
            reason = f"Prohibited action/cause '{action or diag.root_cause}' violates never-allow safety policy."
            logger.critical(
                "NEVER-ALLOW / HARD BLOCK: %s for incident %s",
                action,
                input_data.incident_id,
            )
            return RiskAssessment(
                incident_id=input_data.incident_id,
                risk_level=RiskLevel.NEVER_ALLOW,
                auto_remediable=False,
                requires_human_approval=False,
                blocked=True,
                block_reason=reason,
                approved_action=None,
                assessed_at=now_str,
            )

        # 2. Breaking schema change explicitly mandates human authorization
        if diag.root_cause == "SCHEMA_BREAKING_CHANGE":
            logger.warning(
                "Root cause SCHEMA_BREAKING_CHANGE requires explicit human approval."
            )
            return RiskAssessment(
                incident_id=input_data.incident_id,
                risk_level=RiskLevel.HIGH,
                auto_remediable=False,
                requires_human_approval=True,
                blocked=False,
                block_reason=None,
                approved_action=action,
                assessed_at=now_str,
            )

        # 3. Retrieve policy for proposed action
        policy: ActionPolicy = self.safety_rules.get_policy(action)

        # 4. High Risk actions always require human authorization
        if policy.risk_tier == "HIGH":
            logger.warning(
                "Action '%s' is HIGH risk. Requiring human approval.", action
            )
            return RiskAssessment(
                incident_id=input_data.incident_id,
                risk_level=RiskLevel.HIGH,
                auto_remediable=False,
                requires_human_approval=True,
                blocked=False,
                block_reason=None,
                approved_action=action,
                assessed_at=now_str,
            )

        # 5. Medium Risk actions check minimum confidence
        if policy.risk_tier == "MEDIUM":
            if diag.confidence >= policy.min_confidence:
                return RiskAssessment(
                    incident_id=input_data.incident_id,
                    risk_level=RiskLevel.MEDIUM,
                    auto_remediable=True,
                    requires_human_approval=False,
                    blocked=False,
                    block_reason=None,
                    approved_action=action,
                    assessed_at=now_str,
                )
            else:
                return RiskAssessment(
                    incident_id=input_data.incident_id,
                    risk_level=RiskLevel.MEDIUM,
                    auto_remediable=False,
                    requires_human_approval=True,
                    blocked=False,
                    block_reason=None,
                    approved_action=action,
                    assessed_at=now_str,
                )

        # 6. Low Risk actions are auto-remediable if confidence is acceptable
        if policy.risk_tier == "LOW":
            if diag.confidence >= policy.min_confidence:
                return RiskAssessment(
                    incident_id=input_data.incident_id,
                    risk_level=RiskLevel.LOW,
                    auto_remediable=True,
                    requires_human_approval=False,
                    blocked=False,
                    block_reason=None,
                    approved_action=action,
                    assessed_at=now_str,
                )

        # Default-to-safe principle fallback
        return RiskAssessment(
            incident_id=input_data.incident_id,
            risk_level=RiskLevel.HIGH,
            auto_remediable=False,
            requires_human_approval=True,
            blocked=False,
            block_reason=None,
            approved_action=action,
            assessed_at=now_str,
        )
