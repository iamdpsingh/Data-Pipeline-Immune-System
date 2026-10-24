# Enterprise Data Audit & Compliance Playbook
## 1. Regulatory Guarantees
Every autonomous decision records:
- Exact agent identity (DetectionAgent, RiskAgent, RemediationAgent)
- Cryptographic hash of affected dataset partition
- Timestamp, confidence score, and remediation payload
## 2. Exporting Audit Reports
Run `python3 scripts/export_audit_records.py --start-date 2026-10-01` to generate SOC2-compliant CSV evidence.
