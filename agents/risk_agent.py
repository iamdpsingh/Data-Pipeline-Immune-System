"""
Risk Agent

Determines whether an incident can be safely auto-remediated, requires
human approval, or must be blocked unconditionally.

Permissions: READ ONLY
Inputs: DiagnosisResult
Outputs: RiskAssessment

The Risk Agent is the critical safety gate between diagnosis and action.
It enforces two layers of rules:

  1. Never-allow rules (src/risk/never_allow.py) — these are enforced in
     application code and cannot be overridden by LLM output, confidence
     scores, or configuration.

  2. Risk classification rules (rules/safety_rules.yaml) — these define
     the risk level for each action type and whether human approval is needed.

Confidence scores from the Diagnosis Agent influence risk assessment
but never override safety rules. A 0.99 confidence score on a schema
deletion action still produces NEVER_ALLOW.

For the full safety model, see docs/security/security-model.md.
For the safety rules policy, see rules/safety_rules.yaml.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from src.config.loader import AgentConfig
from src.risk.never_allow import check_never_allow
from src.risk.safety_rules import SafetyRulesLoader
from agents.diagnosis_agent import DiagnosisResult

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
    """
    Determines whether auto-remediation is safe for a given diagnosis.

    Permissions: READ ONLY

    Default-to-safe: if this agent itself fails or produces an unexpected result,
    the controller defaults to requires_human_approval = True.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.safety_rules = SafetyRulesLoader(config.rules_path / "safety_rules.yaml")

    def assess(self, input: RiskInput) -> RiskAssessment:
        """
        Evaluate the risk of the proposed remediation action.

        Never-allow check runs first. If the recommended action is on the
        never-allow list, the result is BLOCKED regardless of everything else.
        """
        raise NotImplementedError("Risk agent implementation pending — Phase 7")
