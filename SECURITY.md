# Security Policy — Data Pipeline Immune System

The **Data Pipeline Immune System** is an autonomous platform that monitors, diagnoses, and self-heals production data pipelines. Because autonomous agents possess execution capabilities, safety and security are fundamental design requirements.

---

## 1. Supported Versions

We provide security updates and patches for the following versions:

| Version | Supported | Security Patch SLA |
|---|---|---|
| `0.1.x` (Current Main) | :white_check_mark: | Critical vulnerabilities patched within 48 hours |
| `< 0.1.0` | :x: | Unsupported |

---

## 2. Reporting a Vulnerability

We take security issues seriously and appreciate responsible disclosure from the community.

### 2.1. How to Report
- **Preferred Method**: Open a confidential security advisory directly on GitHub via [Security Advisories](https://github.com/iamdpsingh/Data-Pipeline-Immune-System/security/advisories/new).
- **Direct Email**: If GitHub Security Advisories are unavailable, send an encrypted or direct email to `dhruvpratapsingh30.official2.o@gmail.com` with the subject line:
  `[SECURITY VULNERABILITY] Data Pipeline Immune System - <Brief Title>`

### 2.2. Report Information Needed
To help us triage and resolve the issue quickly, please include:
1. Description of the vulnerability and its potential security impact.
2. Step-by-step reproduction instructions or a minimal Proof of Concept (PoC).
3. The component affected (`agents/`, `src/risk/`, `src/remediation/`, BigQuery IAM, Terraform).
4. Any proposed mitigations or code fixes.

### 2.3. Response Timeline
- **Initial Acknowledgment**: Within 24 hours of receipt.
- **Triage & Severity Assessment**: Within 48 hours.
- **Patch & Public Disclosure**: Within 7 to 14 days, coordinated with the reporter.

---

## 3. Autonomous Agent Threat Model & Defensive Invariants

The platform enforces defense-in-depth security to mitigate risks specific to autonomous AI systems operating on enterprise databases:

### 3.1. Agent Least Privilege
- **Detection, Diagnosis, Risk, Verification Agents**: Strictly bound to read-only IAM service accounts. They possess zero write or delete privileges across any Google Cloud Storage bucket or BigQuery dataset.
- **Remediation Agent**: Write permissions are constrained to calling pre-vetted Python action handlers in [src/remediation/actions.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/remediation/actions.py). The agent has **no arbitrary SQL execution or shell access**.
- **Learning Agent**: Write access is restricted exclusively to appending incident records in `dpis_audit.incident_memory`.

### 3.2. Code-Enforced Never-Allow Invariants
Prompt-level constraints in LLMs can be bypassed via prompt injection or adversarial inputs. Therefore, our security boundary is enforced deterministically in Python:
- The [NeverAllowEnforcer](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/risk/never_allow.py) inspects all planned actions against `rules/safety_rules.yaml`.
- Destructive commands (`DROP TABLE`, `TRUNCATE`, `DROP DATABASE`, unpartitioned deletion, or modifying schema definitions without migration scripts) raise an uncatchable `CriticalSafetyViolation` and abort execution immediately.
- LLM confidence scores **cannot override** never-allow rules under any circumstance.

### 3.3. Secrets & Credential Management
- No API keys, service account credentials, or passwords are stored in git repositories or local configuration files.
- Production secrets are stored exclusively in **GCP Secret Manager** and accessed at runtime via Workload Identity federation.

### 3.4. Failure Injection Environment Isolation
- The chaos testing framework in [failure_injection/](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/failure_injection/) includes hardcoded environment guards.
- Running injection routines in an environment where `ENVIRONMENT=production` automatically halts execution with a fatal safety error unless an explicit multi-factor verification flag is passed.

---

## 4. Responsible Disclosure Guidelines

- Do not attempt to access, modify, or exfiltrate private data belonging to other users or organizations.
- Give the maintainers adequate time to investigate and release a fix before publishing details publicly.
- Do not execute denial-of-service (DoS) attacks against live Cloud Run or BigQuery infrastructure.
