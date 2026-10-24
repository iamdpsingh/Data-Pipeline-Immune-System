"""Remediation exception definitions."""


class RemediationNotAuthorisedError(Exception):
    """Raised when an action is blocked, unapproved, or outside the approved library."""

    pass
