# Security Policy

## Supported Versions

Security updates and patches are applied to the `main` branch and the current production deployment of **MarketLens Analytics**.

## Reporting a Vulnerability

We take security and client financial data confidentiality seriously. **Please do not open a public GitHub issue for security vulnerabilities.**

If you discover a security issue (e.g., authentication bypass, tenant-isolation flaw, secret exposure, or XSS/CSRF/injection vector):

1. Email **`security@marketlensanalytics.in`** (or the operator support address configured in `PUBLIC_SUPPORT_EMAIL`) with:
   - A clear description of the vulnerability and affected endpoint/module.
   - Steps to reproduce or a minimal proof-of-concept.
   - Any potential impact assessment.
2. We will acknowledge receipt within **48 hours** and provide a remediation timeline for confirmed issues.

## Security Architecture Highlights

- **Tenant Isolation:** Scoped `tenant_id` row filtering across jobs, API keys, ERP connections, and audit ledger entries.
- **Data Retention:** Uploaded client workspaces under `DATA_DIR/accounts/<user_id>/jobs/<job_id>` are automatically purged on a **24-hour TTL** (`JOB_RETENTION_HOURS=24`).
- **Encryption & Secrets:** OAuth/ERP tokens are encrypted at rest via `Fernet` (`TOKEN_ENCRYPTION_KEY`), API keys are stored as SHA-256 hashes, and strict CSP/CSRF headers are enforced on all portal routes.
