# ==============================================================================
# Data Pipeline Immune System — Safety Rules Policy Loader
# ==============================================================================
"""Parses and validates safety policies defined in rules/safety_rules.yaml.

Categorizes actions into:
- NEVER_ALLOW: Unconditionally blocked by hard code policy (src/risk/never_allow.py).
- HIGH_RISK: Always requires human operator approval via dashboard.
- MEDIUM_RISK: Auto-approved if root-cause confidence meets required threshold.
- LOW_RISK: Idempotent and safe for automated autonomous execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.risk.never_allow import NEVER_ALLOW_ACTIONS, check_never_allow

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActionPolicy:
    action: str
    risk_tier: str  # NEVER_ALLOW, HIGH, MEDIUM, LOW
    requires_approval: bool
    min_confidence: float
    reason: str


class SafetyRulesLoader:
    """Loads and indexes safety policies from safety_rules.yaml."""

    def __init__(self, yaml_path: Optional[Path | str] = None):
        self.yaml_path = Path(yaml_path) if yaml_path else Path("rules/safety_rules.yaml").resolve()
        self.policies: Dict[str, ActionPolicy] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Parses safety rules and enforces code boundary synchronization."""
        if not self.yaml_path.exists():
            logger.warning("Safety rules file not found at %s. Using default safety set.", self.yaml_path)
            self._init_defaults()
            return

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 1. Never allow
        for item in data.get("never_allow", []):
            act = item["action"]
            self.policies[act] = ActionPolicy(
                action=act,
                risk_tier="NEVER_ALLOW",
                requires_approval=True,
                min_confidence=1.0,
                reason=item.get("reason", "Prohibited by never-allow boundary"),
            )

        # Ensure all actions in code NEVER_ALLOW_ACTIONS are included
        for act in NEVER_ALLOW_ACTIONS:
            if act not in self.policies:
                self.policies[act] = ActionPolicy(
                    action=act,
                    risk_tier="NEVER_ALLOW",
                    requires_approval=True,
                    min_confidence=1.0,
                    reason="Hardcoded safety invariant",
                )

        # 2. High risk
        for item in data.get("high_risk", []):
            act = item["action"]
            self.policies[act] = ActionPolicy(
                action=act,
                risk_tier="HIGH",
                requires_approval=True,
                min_confidence=item.get("min_confidence", 0.90),
                reason=item.get("reason", "High-risk operation"),
            )

        # 3. Medium risk
        for item in data.get("medium_risk", []):
            act = item["action"]
            self.policies[act] = ActionPolicy(
                action=act,
                risk_tier="MEDIUM",
                requires_approval=False,  # auto if confidence met
                min_confidence=float(item.get("min_confidence", 0.75)),
                reason=item.get("reason", "Medium-risk operation"),
            )

        # 4. Low risk
        for item in data.get("low_risk", []):
            act = item["action"]
            self.policies[act] = ActionPolicy(
                action=act,
                risk_tier="LOW",
                requires_approval=False,
                min_confidence=float(item.get("min_confidence", 0.50)),
                reason=item.get("reason", "Low-risk idempotent repair"),
            )

    def _init_defaults(self) -> None:
        for act in NEVER_ALLOW_ACTIONS:
            self.policies[act] = ActionPolicy(
                action=act,
                risk_tier="NEVER_ALLOW",
                requires_approval=True,
                min_confidence=1.0,
                reason="Default never-allow policy",
            )

    def get_policy(self, action: str) -> ActionPolicy:
        """Retrieves policy for action, defaulting safely to HIGH risk if unknown."""
        # 1. Hard code check
        if check_never_allow(action):
            return ActionPolicy(
                action=action,
                risk_tier="NEVER_ALLOW",
                requires_approval=True,
                min_confidence=1.0,
                reason="Hard boundary never-allow violation",
            )

        if action in self.policies:
            return self.policies[action]

        # Default-to-safe principle: Unknown actions default to HIGH risk requiring human approval
        return ActionPolicy(
            action=action,
            risk_tier="HIGH",
            requires_approval=True,
            min_confidence=0.99,
            reason="Unrecognized action; defaults to requiring human authorization",
        )
