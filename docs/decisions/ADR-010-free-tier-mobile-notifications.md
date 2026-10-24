# ADR-010: Free-Tier Multi-Channel Operational Notification Architecture

## Status: Accepted (In Production)

## Context
Production monitoring requires real-time alerting for data engineers on-call and comprehensive scheduled operational digests for engineering leadership.

Historically, enterprise teams adopted proprietary SaaS notification platforms (Twilio SMS, PagerDuty, SendGrid) that impose:
1. Significant recurring monthly platform costs and per-message charges.
2. Inflexible vendor SDK lock-in with proprietary message templates.
3. Complex account onboarding, credit card verification requirements, and phone number lease fees.

The Data Pipeline Immune System requires reliable, instant, and scheduled notifications that can operate entirely on zero-cost free-tier infrastructure.

## Decision
We implement a zero-cost, resilient multi-channel notification architecture (`src/notifications/`):

1. **Daily Operational Digests via Standard SMTP**:
   - Uses standard, universally supported SMTP over TLS (`smtp.gmail.com:587` with Google App Passwords or GCP Cloud SMTP Relay).
   - Generates responsive, executive-tier, industrial HTML reports (`DailyReportGenerator`) featuring Composite Health Scores, Lakehouse tier storage status, MTTR metrics, and Never-Allow safety audits.
   - Zero vendor fees; authenticated directly against standard mail servers.

2. **Real-Time Operational Alerts via Telegram Bot API**:
   - Real-time hourly pulses and critical P0/P1 incident notifications dispatch to mobile devices via the **Telegram Bot API**.
   - Zero cost, zero message limits, and zero phone carrier lease fees.
   - Supports structured markdown formatting, status indicators, and direct webhook callback links.

3. **Pluggable WhatsApp Interface**:
   - The notification subsystem includes an extensible WhatsApp dispatcher interface (`WhatsAppAlertDispatcher`) ready for direct integration with WhatsApp Cloud API or Meta Graph API.
   - When credentials are not yet provisioned, the engine operates in graceful dry-run / fallback logging mode without throwing unhandled exceptions or halting pipeline runs.

4. **Security & Input Sanitation**:
   - All notification credentials (`SMTP_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) are stored in Secret Manager or gitignored `.env`.
   - Dispatchers automatically sanitize input (e.g. stripping spaces from Gmail 16-character App Passwords) to prevent connection failures.

## Consequences

### Positive
- **Zero Subscription Costs**: 100% free-tier operation with zero recurring monthly SaaS fees.
- **High Reliability**: Standard SMTP and Telegram APIs provide sub-second delivery latencies globally.
- **Clean Fallback**: Failure of a notification channel never impacts data pipeline execution, quarantine operations, or autonomous self-healing.

### Negative / Trade-Offs
- Free Gmail SMTP enforces a daily outbound sending limit (typically 500 emails/day), which is more than sufficient for daily operational reports but unsuitable for high-volume marketing blasts.
- On-call engineers must install the Telegram client on mobile devices to receive real-time mobile push notifications.
