# MarketLens subscription launch

The portal now supports verified email/password accounts, Google sign-in, private per-account jobs and reports, monthly plan limits, and Razorpay recurring subscriptions. Prices are INR-only:

| Plan | Monthly price | Valuations per month |
| --- | ---: | ---: |
| Free | ₹0 | 1 |
| Pro | ₹1,499 | 20 |
| Business | ₹4,999 | 100 |

Limits and prices can be changed with the environment variables in `.env.example`. One live-company analysis or uploaded-file pack consumes one successful monthly valuation. Failed jobs do not consume quota.

## Required Railway setup

Do not accept public customer files or payments until these steps are complete:

1. Attach a Railway persistent volume to the web service at `/data` and set `MARKETLENS_DATA_DIR=/data`. Both the SQLite database (unless `DATABASE_URL` is set) and private reports live there. Keep one app replica while using SQLite and local report storage.
2. Set `APP_ENV=production`, `PUBLIC_APP_URL=https://<your-domain>`, and `ALLOWED_HOSTS=<your-domain>`. Set a strong `SESSION_SECRET` in Railway's secret-variable UI. Do not send secrets through chat or commit them.
3. Configure transactional email by setting `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, and the SMTP credentials. Account creation, verification, and password recovery require email delivery.
4. Configure Google OAuth in Google Cloud. Add this exact redirect URI to the OAuth client: `https://<your-domain>/api/v1/auth/google/callback`. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
5. In Razorpay test mode, create monthly INR plans for ₹1,499 and ₹4,999. Set their plan IDs as `RAZORPAY_PLAN_ID_PRO` and `RAZORPAY_PLAN_ID_BUSINESS`; the app verifies amount, currency, and monthly interval before checkout.
6. Set Razorpay test credentials and a webhook secret. Register `https://<your-domain>/api/v1/billing/webhook` and subscribe to `subscription.activated`, `subscription.charged`, `subscription.resumed`, `subscription.paused`, `subscription.halted`, `subscription.cancelled`, and `subscription.completed`.
7. Test signup, email verification, Google sign-in, one Free valuation, quota rejection, a Razorpay test subscription, cancellation, and report access from a second account. Only then replace test keys/plan IDs with production values.
8. Set `PUBLIC_LEGAL_NAME` and `PUBLIC_SUPPORT_EMAIL`. Replace/review the starter Terms and Privacy pages with your real operator identity, governing law, tax/GST, cancellation/refund, retention/deletion, and applicable India/international privacy disclosures before taking payment.

If using a Railway PostgreSQL service, set `DATABASE_URL` to its private connection reference. Keep the persistent volume for generated files. The current valuation runner uses in-process background tasks and local report files; do not scale to multiple replicas until a durable job queue and shared object storage are configured.

International visitors currently see INR prices. International card acceptance, cross-border sales, taxes, and local consumer/privacy requirements depend on your Razorpay account and must be enabled/handled by the operator; USD billing is not configured.

## Customer data and valuation disclaimers

Uploads and output files are not mounted as public static folders. A signed-in, verified account can access only its own reports. Uploads are limited to 25 MB by default. Reports persist on the configured volume; they are not automatically deleted, so establish and publish a retention/deletion policy before launch.

MarketLens is an informational modeling tool, not investment, legal, tax, or accounting advice. Market data and model assumptions can be incomplete or wrong; customers must independently review source data and results.

## Database and schema notes

The initial schema is created automatically at application startup. For a first deployment, configure storage before inviting users. Back up the database and volume before upgrades; future schema changes should use an explicit migration process. SQLite is suitable only for a single app replica. PostgreSQL is recommended for multi-user production, but multiple replicas still require a shared durable job queue and shared report storage.
