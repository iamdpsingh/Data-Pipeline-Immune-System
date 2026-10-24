# Platform Exception Hierarchy
class ImmuneSystemError(Exception):
    """Base exception for all Data Pipeline Immune System errors."""


class QualityGateViolation(ImmuneSystemError):
    """Raised when data quality checks fail."""


class RemediationSafetyViolation(ImmuneSystemError):
    """Raised when remediation action trips safety boundary."""
