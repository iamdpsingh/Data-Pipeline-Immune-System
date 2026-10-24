# ==============================================================================
# Data Pipeline Immune System — Notification & Reporting Subsystem
# ==============================================================================
"""Automated reporting and alerting package for the Data Pipeline Immune System.

Modules:
- reporter: Generates and dispatches daily email health summaries.
- whatsapp: Dispatches hourly operational status alerts via WhatsApp.
"""

from src.notifications.reporter import DailyReportGenerator, EmailDispatcher
from src.notifications.whatsapp import WhatsAppAlertDispatcher

__all__ = ["DailyReportGenerator", "EmailDispatcher", "WhatsAppAlertDispatcher"]
