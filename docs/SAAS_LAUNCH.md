# MarketLens Subscription & Production Launch Checklist

The portal supports verified email/password accounts, Google sign-in, SAML 2.0 Enterprise SSO, private per-tenant jobs and reports, monthly plan limits, multi-currency billing (**Stripe** for USD/EUR/GBP and **Razorpay** for INR), and scoped VaaS API keys.

| Plan | Key | USD / mo | INR / mo | Valuations / mo |
| --- | --- | ---: | ---: | ---: |
| Executive Pilot (Free) | `free` | \$0 | ₹0 | 1 |
| Advisory & Corporate Desk | `pro` | \$499 | ₹39,999 | 25 |
| Private Equity & Fund Desk | `business` | \$1,499 | ₹1,19,999 | 100 |
| Institutional Sovereign | `enterprise` | \$4,999 | ₹3,99,999 | 999 |

Limits and prices can be configured via environment variables. One live-company analysis or uploaded-file pack consumes one successful monthly valuation; failed jobs do not consume quota.

## Required Railway Setup

Do not accept public customer files or payments until these steps are complete:

1. **Storage & Database:**
   - Provision **Railway PostgreSQL** (`DATABASE_URL`) for multi-user production, and attach a persistent volume at `/data` with `MARKETLENS_DATA_DIR=/data` (required for SQLite fallback and temporary job workspaces).
   - Keep `WEB_CONCURRENCY=1` (single replica) if using SQLite/local disk without Redis + S3/R2.
2. **Core Security Secrets:**
   - Set `APP_ENV=production`, `PUBLIC_APP_URL=https://<your-domain>`, and `ALLOWED_HOSTS=<your-domain>`.
   - Set a strong `SESSION_SECRET` and a valid Fernet `TOKEN_ENCRYPTION_KEY` in Railway's secret-variable UI (a startup warning is logged in production if `TOKEN_ENCRYPTION_KEY` is omitted).
3. **Redis & Celery (Optional Horizontal Scale):**
   - Provision **Railway Redis** (`REDIS_URL`) to enable distributed API rate limiting across workers and Celery background queues (`valuation_heavy`, `scraper_daily`) when `USE_CELERY_WORKERS=1`.
4. **Transactional Email & Google OAuth:**
   - Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, and SMTP credentials.
   - Configure Google OAuth redirect URI: `https://<your-domain>/api/v1/auth/google/callback` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
5. **Billing (Stripe & Razorpay):**
   - Configure Stripe API keys, price IDs, and webhook secret for `USD`/`EUR`/`GBP`.
   - In Razorpay, create monthly INR plans (`₹39,999` Pro, `₹1,19,999` Business, `₹3,99,999` Enterprise), set `RAZORPAY_PLAN_ID_PRO` / `RAZORPAY_PLAN_ID_BUSINESS` / `RAZORPAY_PLAN_ID_ENTERPRISE`, and register `https://<your-domain>/api/v1/billing/webhook`.
6. **Legal & Compliance:**
   - Set `PUBLIC_LEGAL_NAME` and `PUBLIC_SUPPORT_EMAIL`, and review `/terms` and `/privacy` for your operator identity, governing law, tax/GST, and privacy disclosures.

## Customer Data Retention & Disclaimers

- Uploads are limited to `25 MB` by default (`MAX_UPLOAD_BYTES`) and isolated under `DATA_DIR/accounts/<user_id>/jobs/<job_id>`.
- Job workspaces on disk are automatically purged after **24 hours** (`JOB_RETENTION_HOURS=24`) by `_start_workspace_ttl_purger()`, while SHA-256 Merkle audit ledger records remain verifiable in the database.
- MarketLens is an informational modeling tool, not investment, legal, tax, or accounting advice. Customers must independently review source data and assumptions.
