---
name: deploy-check
description: Smoke-test an environment after a deploy — the endpoints and pages that historically break first
---

Environment: $ARGUMENTS (`dev`, `tst`, `ppr` or `prd`). Ask if empty.

Check, and report status code plus response time for each:

1. Aggregated homepage endpoint — `/api/1/site/home/` (backend). Slow here means the backend; fast here plus a slow page means the CMS.
2. `/me` (backend, authenticated) — a 401 after a SAML change usually means `metadata.xml` pins the wrong-environment IdP certificate.
3. A resource download proxy — `/r/<id>` for a known WMS/OGC resource. A 502 usually means the proxy read timeout is too low for a slow GetCapabilities.
4. The public homepage (frontend) — measure TTFB. Squidex CMS latency shows up here while both the backend and Next are fast.
5. If a harvester changed: confirm the Celery worker **and** beat were restarted, otherwise the run uses stale in-memory code.

Report a short table: check, result, and what the result implicates. Do not change
configuration; report what needs changing.
