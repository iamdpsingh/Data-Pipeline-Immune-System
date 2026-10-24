# ==============================================================================
# Unit Tests — Notification Subsystem (Daily Reports & WhatsApp)
# ==============================================================================
import pytest

from src.notifications.reporter import (
    DailyReportGenerator,
    DailyReportMetrics,
    EmailDispatcher,
)
from src.notifications.whatsapp import WhatsAppAlertDispatcher


class TestDailyReportGenerator:
    def test_collect_metrics_default(self):
        generator = DailyReportGenerator(environment="dev")
        metrics = generator.collect_metrics()
        assert isinstance(metrics, DailyReportMetrics)
        assert metrics.overall_health_score > 90.0
        assert metrics.environment == "dev"
        assert metrics.total_runs > 0

    def test_render_html_report(self):
        generator = DailyReportGenerator(environment="dev")
        metrics = generator.collect_metrics()
        html = generator.render_html_report(metrics)
        assert "Data Pipeline Immune System" in html
        assert "Composite Health Score" in html
        assert "Medallion Lakehouse Status" in html

    def test_render_text_report(self):
        generator = DailyReportGenerator(environment="dev")
        metrics = generator.collect_metrics()
        text = generator.render_text_report(metrics)
        assert "DATA PIPELINE IMMUNE SYSTEM — DAILY REPORT" in text
        assert "Health Score:" in text

    def test_email_dispatcher_dry_run(self):
        dispatcher = EmailDispatcher()
        generator = DailyReportGenerator(environment="dev")
        metrics = generator.collect_metrics()
        result = dispatcher.send_daily_report(
            recipient="test@example.com",
            metrics=metrics,
            generator=generator,
        )
        assert result is True


class TestWhatsAppAlertDispatcher:
    def test_format_hourly_alert(self):
        dispatcher = WhatsAppAlertDispatcher()
        msg = dispatcher.format_hourly_alert(
            pipeline_count=12,
            health_status="HEALTHY",
            health_score=98.5,
        )
        assert "Data Pipeline Immune System" in msg
        assert "Hourly Pulse" in msg
        assert "HEALTHY (98.5/100)" in msg

    def test_send_hourly_alert_dry_run(self):
        dispatcher = WhatsAppAlertDispatcher()
        result = dispatcher.send_hourly_alert(
            recipient_phone="+1234567890",
            health_status="HEALTHY",
        )
        assert result is True
