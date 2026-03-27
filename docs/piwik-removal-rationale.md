# Removal of udata-piwik — Rationale and Comparison

Decision record documenting why `udata-piwik` (and its dependency `udata-metrics`) were removed from the dados.gov.pt backend, and how the native metrics system replaces all their functionality.

## Context

The dados.gov.pt project is a fork of the udata open data platform. The original udata used a Flask/Jinja2 monolithic frontend. This project migrated the frontend to **Next.js**, creating a decoupled architecture where the backend serves a REST API and the frontend is a separate application.

The `udata-piwik` plugin (v2.1.4) was designed for the original monolithic architecture. Its primary mechanism — injecting a Matomo JavaScript tracking snippet via Jinja2 `template_hook('footer.snippets')` — is incompatible with the Next.js frontend. Additionally, the plugin requires three external services (Matomo, InfluxDB, Metrics API) to function, while the backend already contains a complete, self-contained metrics system in `udata/core/metrics/` that requires no external dependencies beyond the existing MongoDB.

**Packages removed:**
- `udata-piwik==2.1.4`
- `udata-metrics==1.0.2` (transitive dependency)
- `influxdb==5.2.3` (transitive dependency)

**Configuration removed from `udata.cfg`:**
- `PLUGINS` block (no registered entry points existed)
- `PIWIK_ID_FRONT`, `PIWIK_ID_API`, `PIWIK_ID`
- `PIWIK_SCHEME`, `PIWIK_URL`, `PIWIK_AUTH`
- `PIWIK_GOALS` (goal mapping dictionary)
- `PIWIK_TRACK_TIMEOUT`, `PIWIK_ANALYZE_TIMEOUT`
- `PIWIK_CONTENT_TRACKING`
- `METRICS_API`

---

## Native System vs udata-piwik — Comparison

| Funcionalidade | Nativo | udata-piwik |
|---|---|---|
| Tracking de views | MetricEvent (MongoDB) | Matomo API |
| Tracking de downloads | MetricEvent (MongoDB) | Matomo API |
| Agregacao | MetricAggregation (MongoDB, diaria/mensal) | Matomo + InfluxDB |
| API de tracking (frontend) | `POST /api/tracking/` | JS snippet (Jinja2) |
| GDPR (anonimizacao de IP) | Built-in (`anonymize_ip()`) | Nao implementado |
| Dependencias externas | Nenhuma (so MongoDB) | Matomo + InfluxDB |
| Dual-mode | Sim — usa `METRICS_API` externo OU dados internos | So externo |
| TTL automatico | 90 dias configurable | Gerido pelo Matomo |

### Why the native system wins

1. **Zero additional infrastructure** — uses the same MongoDB instance the application already depends on, versus three additional services (Matomo server, InfluxDB, Metrics API) that need to be provisioned, monitored, and maintained.

2. **Compatible with Next.js** — the native system exposes `POST /api/1/tracking/` for the frontend and provides a React hook (`usePageTracking`) with session-based deduplication. The piwik plugin requires `template_hook` from Flask/Jinja2, which does not exist.

3. **GDPR compliant by default** — IP addresses are anonymized before storage (last IPv4 octet zeroed, IPv6 hashed). The piwik plugin stores raw IPs in the `PiwikTracking` MongoDB model.

4. **Simpler data flow** — the piwik plugin sends data to Matomo, reads it back via the Reporting API, writes to InfluxDB via udata-metrics, then reads from InfluxDB to update MongoDB models (4 hops across 3 services). The native system writes directly to MongoDB and aggregates in place (1 hop).

5. **Better deduplication** — the frontend hook uses `sessionStorage` to ensure each object is counted once per browser session. The piwik plugin has no deduplication mechanism of its own.

---

## What udata-piwik did

### Architecture

```
User visits page
       |
       v
+----------------------------------------------------------+
|  udata-piwik JS snippet (injected via Jinja2 template)   |
|  Sends page views, searches, goals to Matomo             |
+----------------------------+-----------------------------+
                             |
                             v
                    +----------------+
                    |   Matomo        |  <-- External service
                    |   Server       |
                    +-------+--------+
                            |
              +-------------+-------------+
              v             v             v
         Celery task   Celery task   Celery task
         (piwik-       (piwik-       (piwik-bulk-
         current-      yesterday-    track-api)
         metrics)      metrics)
              |             |             |
              v             v             v
     +---------------------------------------------+
     |  udata-metrics (InfluxDB client)             |  <-- External service
     |  Writes: dataset_views, reuse_views,         |
     |  resource_views, org_views, user_views       |
     +----------------------+-----------------------+
                            |
                            v
                  +-------------------+
                  |     InfluxDB      |  <-- External service
                  +---------+---------+
                            |
                            v
                  Celery task reads back
                  from InfluxDB and updates
                  model.metrics['views']
                  in MongoDB
```

### Components and their status

| Component | Purpose | Status in dados.gov.pt |
|---|---|---|
| `udata_piwik/views.py` | Injects Matomo JS tracking snippet into Jinja2 footer | **Broken** — uses `template_hook` from Flask frontend, which no longer exists |
| `udata_piwik/tasks.py` | Celery tasks to fetch metrics from Matomo API and process bulk API tracking | Functional but **redundant** |
| `udata_piwik/counter.py` | Parses Matomo API responses, matches URLs to Flask routes, counts views | **Broken** — relies on Flask URL routing (`datasets.show`, `reuses.show`) |
| `udata_piwik/download_counter.py` | Counts resource downloads from Matomo outlinks/downloads data | Functional but **redundant** |
| `udata_piwik/client.py` | HTTP client for Matomo Tracking API and Reporting API | Functional but **unused** without Matomo server |
| `udata_piwik/models.py` | `PiwikTracking` MongoDB model for bulk API call tracking | **Unnecessary** — native system tracks API calls directly |
| `udata_piwik/upsert.py` | Writes metrics to InfluxDB via udata-metrics client | **Unnecessary** — native system stores in MongoDB |
| `udata_metrics/client.py` | InfluxDB client for reading/writing time-series metrics | **Unnecessary** — native system uses MongoDB |
| `udata_metrics/tasks.py` | Listens to `on_site_metrics_computed` signal, writes to InfluxDB | **Unnecessary** |

### Data it collected

| Data Type | How Collected | Sent To |
|---|---|---|
| Page views (datasets, reuses, orgs, users) | Matomo JS SDK in browser | Matomo server |
| Search queries with result counts | Matomo `trackSiteSearch()` | Matomo server |
| Resource downloads | Matomo outlink/download detection | Matomo server |
| API calls (URLs, timestamps, IPs) | `on_api_call` signal → bulk tracking | Matomo server |
| Goal conversions (new dataset, reuse, follow, share) | Signal handlers in Celery tasks | Matomo server |
| Content impressions | Matomo JS content tracking | Matomo server |

### Configuration it required

| Key | Purpose | Required Service |
|---|---|---|
| `PIWIK_URL` | Matomo server hostname | Matomo |
| `PIWIK_SCHEME` | HTTP or HTTPS | Matomo |
| `PIWIK_ID_FRONT` | Site ID for frontend tracking | Matomo |
| `PIWIK_ID_API` | Site ID for API tracking | Matomo |
| `PIWIK_AUTH` | 32-char authentication token | Matomo |
| `PIWIK_GOALS` | Goal ID mapping | Matomo |
| `PIWIK_TRACK_TIMEOUT` | Tracking request timeout | Matomo |
| `PIWIK_ANALYZE_TIMEOUT` | Reporting API timeout | Matomo |
| `METRICS_API` | External metrics REST endpoint | InfluxDB + API |
| `METRICS_DSN` | InfluxDB connection string | InfluxDB |

**Total external services required: 3** (Matomo, InfluxDB, Metrics API)

---

## What the native system does

### Architecture

```
User visits page (Next.js)
       |
       +---- POST /api/1/tracking/  ----------------+
       |     event_type: "view"                      |
       |     (sendBeacon, 1x per session)            |
       |                                             v
       |                                   +------------------+
       |                                   |   MetricEvent     |
User downloads resource                    |   (MongoDB)       |
       |                                   |   TTL: 90 days    |
       +---- GET /api/1/datasets/r/{id}    |   IP anonymized   |
       |     (302 redirect, tracked by     +---------+---------+
       |      after_request hook)                    |
       |                                   +---------+-----------+
       |                                   v         v           v
User calls API                        update-   aggregate-  compute-
       |                              metrics   metrics     site-metrics
       +---- on_api_call signal       (Celery)  (Celery)    (Celery)
             (auto-captured by             |         |           |
              listeners.py)                v         v           v
                                      Dataset    MetricAgg   Site
                                      .metrics   (daily/     .metrics
                                      .views     monthly)
                                      .resources_downloads
```

### Configuration required

| Key | Default | Purpose |
|---|---|---|
| `TRACKING_ENABLED` | `True` | Enable/disable the tracking system |
| `TRACKING_EVENT_TTL_DAYS` | `90` | Auto-delete raw events after N days |

**Total external services required: 0** (uses existing MongoDB)

---

## Feature-by-feature comparison

| Feature | udata-piwik | Native System | Winner |
|---|---|---|---|
| **Page view tracking** | Matomo JS in Jinja2 template (broken with Next.js) | `POST /api/1/tracking/` + `usePageTracking` hook | Native |
| **Download tracking** | Matomo outlink detection + counter | `after_request` hook on resource redirect | Native |
| **Search tracking** | Matomo `trackSiteSearch()` (broken) | `POST /api/1/tracking/` with `event_type: "search"` | Native |
| **API call tracking** | `on_api_call` → PiwikTracking model → bulk POST to Matomo | `on_api_call` → MetricEvent (direct MongoDB write) | Native |
| **Goal tracking** | Signal handlers → Matomo goals API | Not implemented (business logic, not metrics) | N/A |
| **View deduplication** | None (relies on Matomo) | `sessionStorage` — 1 view per session per object | Native |
| **IP anonymization** | Not implemented | Last IPv4 octet zeroed, IPv6 hashed (GDPR compliant) | Native |
| **Data aggregation** | Matomo API → InfluxDB → MongoDB (3 hops) | MetricEvent → MetricAggregation (1 hop, same DB) | Native |
| **Historical data** | Matomo retention policies | MetricAggregation (permanent), MetricEvent (90-day TTL) | Tie |
| **Per-resource downloads** | URL pattern matching in download_counter.py | Direct `resource_id` tracking in MetricEvent | Native |
| **Model metrics updates** | Read from InfluxDB → write to model.metrics | Read from MetricAggregation → write to model.metrics | Native |
| **13-month history API** | Not available | `get_metrics_for_model()` returns monthly breakdown | Native |
| **External dependencies** | Matomo + InfluxDB + Metrics API (3 services) | None (MongoDB only) | Native |
| **Next.js compatibility** | Broken (requires Jinja2 `template_hook`) | Designed for it (`sendBeacon`, React hooks) | Native |

---

## Performance comparison

| Metric | udata-piwik | Native System |
|---|---|---|
| **Write latency (tracking)** | HTTP POST to Matomo server (network round-trip) | MongoDB insert (local/fast) |
| **Read latency (metrics)** | HTTP GET to Matomo API + HTTP to InfluxDB | MongoDB query (same DB as app) |
| **Bulk API tracking** | Accumulates in MongoDB → batch POST to Matomo | Direct MongoDB insert per event |
| **Aggregation** | Matomo processes internally + InfluxDB query | MongoDB aggregation pipeline (single query) |
| **Infrastructure overhead** | 3 additional services to maintain and monitor | Zero additional services |
| **Network calls per page view** | Browser → Matomo + Backend → Matomo (2 external calls) | Browser → Backend (1 internal call) |
| **Failure modes** | Matomo down = no tracking; InfluxDB down = no metrics | MongoDB down = entire app down anyway |

---

## If Matomo web analytics are needed later

The Matomo JavaScript tracking code can be added directly in Next.js without any backend plugin. This gives standard web analytics (bounce rate, session duration, referrers, geography) that the native metrics system intentionally does not cover, as those are frontend-only concerns.

```tsx
// Example: frontend/src/app/layout.tsx
<Script
  src="https://matomo.example.com/matomo.js"
  strategy="afterInteractive"
/>
```

This approach is:
- Independent of the backend
- Standard Next.js pattern
- Does not require udata-piwik or any backend plugin
- Can be configured via environment variable (`NEXT_PUBLIC_MATOMO_URL`)

---

## Related documentation

- [Internal Metrics System](internal-metrics-system.md) — full documentation of the native tracking system
- [Metrics Workflow](metrics-workflow.md) — end-to-end data flow including Airflow DAG pipeline
