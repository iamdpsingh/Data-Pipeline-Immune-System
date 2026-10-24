# Audit & Regulatory Compliance Playbook (SOC 2, ISO 27001, GDPR, HIPAA)

## 1. Compliance Architecture Overview
The Data Pipeline Immune System incorporates autonomous AI agents alongside deterministic code gates. To satisfy SOC 2 (Security, Processing Integrity, Confidentiality), ISO 27001, and GDPR/HIPAA standards, every autonomous action is governed by three architectural controls:
1. **Deterministic Precedence**: Hardcoded rules and Never-Allow code invariants run before and supersede any LLM diagnosis or remediation proposal.
2. **Append-Only Tamper-Evident Audit Logging**: Every system decision is committed to BigQuery immutable audit datasets with SHA-256 parameter hashes.
3. **Strict Separation of Duties & Least Privilege**: Diagnosis agents possess read-only IAM scopes; only the Remediation Agent has scoped write access to pre-approved action types.

---

## 2. Auditor Verification Query Cookbook

### Verification 1: Confirm Zero Never-Allow Violations
Proves that no autonomous agent executed prohibited actions (e.g. `DELETE_TABLE`, `MODIFY_IAM`, `EXPOSE_PII`):
```sql
SELECT
    event_id,
    timestamp,
    agent_name,
    action_type,
    status,
    details
FROM `data-pipeline-immune-system.dpis_analytics_prod.incident_audit_log`
WHERE action_type IN (
    'DELETE_PRODUCTION_TABLE',
    'EXECUTE_ARBITRARY_SQL',
    'MODIFY_IAM_ROLE',
    'EXPOSE_PII_PLAINTEXT',
    'DISABLE_VALIDATION_RULE'
)
  AND status = 'SUCCESS';
-- EXPECTED RESULT: 0 ROWS RETURNED (100% INVIOLABLE SAFETY)
```

### Verification 2: Reconstruct Complete Forensic Lineage for an Incident
Demonstrates complete auditability from detection to verification:
```sql
SELECT
    timestamp,
    agent_name,
    action_type,
    status,
    details.root_cause AS diagnosed_cause,
    details.risk_level AS assessed_risk,
    details.action_executed AS executed_action,
    details.verification_status AS verification
FROM `data-pipeline-immune-system.dpis_analytics_prod.incident_audit_log`
WHERE incident_id = 'inc-4ee243383907'
ORDER BY timestamp ASC;
```

---

## 3. Handling GDPR / CCPA "Right to be Forgotten" Requests
When a customer exercises their right to data deletion:
1. **Crypto-Shredding Architecture**:
   - Customer IDs in analytical tables are pseudonymized using SHA-256 with a salt stored securely in Google Secret Manager (`CUSTOMER_SALT_SECRET`).
   - Deleting the customer encryption key renders all historical analytical rows irreversibly unreadable without requiring destructive table rewrites.
2. **Purging Active Silver Tables**:
   - Execute an authorized DML deletion targeted to the customer's pseudonymized ID:
     ```sql
     DELETE FROM `dpis_silver_prod.orders`
     WHERE customer_id_hash = SHA256(CONCAT('cust-12345', '<SALT>'));
     ```
   - Log the deletion event in `dpis_analytics_prod.compliance_deletion_log` with the data protection officer's sign-off ID.

---

## 4. Quarterly Compliance Checklist
- [ ] Verify that no service account keys (`.json` files) exist in Google Secret Manager or git repositories.
- [ ] Review Cloud Audit Logs to confirm BigQuery audit datasets have zero `DELETE` or `DROP TABLE` API calls.
- [ ] Confirm that all Cloud Run instances enforce HTTPS TLS 1.3 and require Google IAM / OIDC authentication.
- [ ] Validate that the Dead-Letter Quarantine gate has zero unreviewed records older than 90 days.
