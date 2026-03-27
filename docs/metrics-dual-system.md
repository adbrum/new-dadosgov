# Metrics Dual System — Internal vs External (Airflow/Hydra)

The dados.gov.pt platform has two metrics processing pipelines that share the same data source (`MetricEvent` in MongoDB) but serve different purposes. This document describes each system independently and how they work together.

---

## Shared Data Source

Both systems read from the same MongoDB collection: `metric_event`.

Events are created by two entry points:

1. **API call listener** — every request to the udata API triggers `on_api_call` signal. The listener in `udata/core/metrics/listeners.py` parses the URL and creates a `MetricEvent` for views and downloads (generic API calls like listings are ignored).

2. **Frontend POST endpoint** — the Next.js frontend sends explicit tracking events via `POST /api/1/tracking/` with `event_type`, `object_type`, and `object_id`. The React hook `usePageTracking` ensures one view per session per object.

### MetricEvent model

| Field | Type | Description |
|---|---|---|
| `event_type` | string (required) | `view`, `download`, `search`, `click`, `api_call`, `custom` |
| `object_type` | string | `dataset`, `resource`, `reuse`, `organization`, `dataservice`, `page` |
| `object_id` | string | Slug or ObjectId of the tracked object |
| `user_id` | string | Authenticated user ID (if any) |
| `ip` | string | Anonymized IP (last IPv4 octet zeroed, IPv6 hashed) |
| `user_agent` | string | Browser user agent |
| `referer` | string | HTTP referer header |
| `extra` | dict | Additional data (e.g. `{"dataset_id": "...", "resource_id": "..."}`) |
| `created_at` | datetime | Timestamp, auto-delete after 90 days (TTL index) |

**Collection:** `metric_event`
**Defined in:** `backend/udata/core/metrics/events.py`

---

## System 1: Internal (Native udata)

### Purpose

Update the `metrics` field on udata model documents (Dataset, Reuse, Organization, Dataservice) so the API can serve view/download counts directly from MongoDB.

### Architecture

```
MetricEvent (metric_event collection)
       |
       +---------+-----------+
       |         |           |
       v         v           v
  update-   aggregate-  compute-
  metrics   metrics     site-metrics
  (Celery)  (Celery)    (Celery)
       |         |           |
       v         v           v
  Model.     MetricAgg   Site.
  metrics    (daily/     metrics
  (MongoDB)  monthly)   (MongoDB)
```

### How it works

#### Step 1: Events accumulate

Every API request that targets a specific object (e.g. `GET /api/1/datasets/my-dataset/`) creates a `MetricEvent`. Frontend page visits also create events via `POST /api/1/tracking/`.

#### Step 2: `update-metrics` task aggregates events into model documents

**File:** `backend/udata/core/metrics/tasks.py` (function `update_metrics_from_internal`)

When `METRICS_API` is **not configured** (None), this task runs five MongoDB aggregation pipelines:

| Pipeline | Match criteria | Groups by | Updates |
|---|---|---|---|
| Dataset views | `event_type="view"`, `object_type="dataset"` | `object_id` | `Dataset.metrics.views` |
| Dataset downloads | `event_type="download"` | `extra.dataset_id` | `Dataset.metrics.resources_downloads` |
| Reuse views | `event_type="view"`, `object_type="reuse"` | `object_id` | `Reuse.metrics.views` |
| Organization views | `event_type="view"`, `object_type="organization"` | `object_id` | `Organization.metrics.views` |
| Dataservice views | `event_type="view"`, `object_type="dataservice"` | `object_id` | `Dataservice.metrics.views` |

Only `event_type="view"` counts as a page view. Events with `event_type="api_call"` are ignored because a single page visit generates 4-7 API calls, which would inflate the numbers.

The task resolves objects by ObjectId first, then by slug as fallback.

#### Step 3: `aggregate-metrics` task creates historical summaries

**File:** `backend/udata/core/metrics/tasks.py` (function `aggregate_metrics`)

Runs daily. Processes yesterday's `MetricEvent` data:

1. Queries events from yesterday (00:00 to 23:59 UTC)
2. Groups by `(object_type, object_id, event_type)`, counts occurrences
3. Upserts into `MetricAggregation` for two period types:
   - **Daily:** period = `"2026-03-27"`, increments views/downloads/api_calls
   - **Monthly:** period = `"2026-03"`, increments views/downloads/api_calls

`MetricAggregation` documents are permanent (no TTL). This preserves historical data after the raw events expire at 90 days.

#### Step 4: `compute-site-metrics` task updates portal-wide statistics

**File:** `backend/udata/core/metrics/tasks.py` (function `compute_site_metrics`)

Counts totals across all collections:
- `Site.metrics.datasets` = total datasets
- `Site.metrics.organizations` = total organizations
- `Site.metrics.reuses`, `users`, `discussions`, `followers`, etc.
- Stock metrics (new objects per month for the last 365 days)

Emits `on_site_metrics_computed` signal when done.

### Configuration

| Key | Default | Description |
|---|---|---|
| `TRACKING_ENABLED` | `True` | Enable the `on_api_call` listener and `/api/1/tracking/` endpoint |
| `TRACKING_EVENT_TTL_DAYS` | `90` | Auto-delete raw events after N days |
| `METRICS_API` | `None` | When None, `update-metrics` uses internal aggregation |

### Scheduling (Celery beat)

```bash
udata job schedule update-metrics "0 * * * *"       # every hour
udata job schedule aggregate-metrics "0 2 * * *"     # daily at 02:00
udata job schedule compute-site-metrics "0 3 * * *"  # daily at 03:00
```

### Data storage

| Collection | Contents | Retention |
|---|---|---|
| `metric_event` | Raw events (views, downloads, searches) | 90 days (TTL) |
| `metric_aggregation` | Daily/monthly totals per object | Permanent |
| Model documents (`dataset`, `reuse`, etc.) | `metrics` field with current totals | Permanent |
| `site` | Portal-wide statistics | Permanent |

### Key files

| File | Purpose |
|---|---|
| `udata/core/metrics/__init__.py` | Initialization, connects listeners |
| `udata/core/metrics/events.py` | `MetricEvent` model |
| `udata/core/metrics/aggregations.py` | `MetricAggregation` model |
| `udata/core/metrics/listeners.py` | `on_api_call` signal handler, URL regex patterns |
| `udata/core/metrics/api.py` | `POST /api/1/tracking/` endpoint |
| `udata/core/metrics/tasks.py` | Celery tasks: update-metrics, aggregate-metrics, compute-site-metrics |
| `udata/core/metrics/helpers.py` | Query functions for 13-month history |
| `udata/core/metrics/models.py` | `WithMetrics` mixin for model documents |
| `udata/core/metrics/commands.py` | CLI: `udata metrics update` |

---

## System 2: External (Airflow + Hydra)

### Purpose

Export metrics data from MongoDB to PostgreSQL (Hydra) for long-term storage, CSV exports, and PostgREST API access. Also updates udata model documents via the `METRICS_API` configuration.

### Architecture

```
MetricEvent (metric_event collection)
       |
       v
Airflow DAG: exemplo_etl (every minute)
       |
       +--→ Task 1: extract_tracking_events
       |    (aggregates views/downloads from MongoDB)
       |
       +--→ Task 2: send_to_metrics_db
       |    (writes to PostgreSQL / Hydra)
       |
       +--→ Task 3: update_udata_metrics
       |    (reads from PostgREST, writes back to MongoDB models)
       |
       +--→ Task 4: save_to_mongodb
            (execution log)

       PostgreSQL (Hydra)
              |
              v
       PostgREST (api-tabular, port 8006)
              |
              v
       update-metrics task reads METRICS_API
              |
              v
       Dataset.metrics.views = N
```

### How it works

#### Step 1: Airflow DAG extracts and aggregates

**Container:** `airflow-demo-test` (port 18080)
**Schedule:** Every minute (`* * * * *`)

**Task 1 — `extract_tracking_events`:**
- Reads from MongoDB `metric_event` collection (previously `tracking_events`)
- Aggregates views and downloads per dataset, organization, reuse, dataservice
- Aggregates downloads per individual resource
- Computes site-level counts (total datasets, organizations, users, etc.)

**Task 2 — `send_to_metrics_db`:**
- Writes aggregated data to PostgreSQL (Hydra, port 5434)
- Uses `ON CONFLICT ... DO UPDATE` for upsert by `(entity_id, metric_month)`

PostgreSQL tables:

| Table | Primary Key | Columns |
|---|---|---|
| `datasets` | `(dataset_id, metric_month)` | `monthly_visit`, `monthly_download_resource` |
| `organizations` | `(organization_id, metric_month)` | `monthly_visit_dataset` |
| `reuses` | `(reuse_id, metric_month)` | `monthly_visit` |
| `dataservices` | `(dataservice_id, metric_month)` | `monthly_visit` |
| `resources` | `(resource_id, metric_month)` | `download_resource` |

PostgreSQL views (consumed by PostgREST):

| View | Aggregation |
|---|---|
| `datasets_total` | `SUM(monthly_visit)`, `SUM(monthly_download_resource)` per dataset |
| `organizations_total` | `SUM(monthly_visit_dataset)` per organization |
| `reuses_total` | `SUM(monthly_visit)` per reuse |
| `dataservices_total` | `SUM(monthly_visit)` per dataservice |
| `resources_total` | `SUM(download_resource)` per resource |

**Task 3 — `update_udata_metrics`:**
- Reads totals from PostgREST: `GET http://api-tabular:8006/api/datasets_total/data/`
- Updates MongoDB model documents: `Dataset.metrics.views`, `Dataset.metrics.resources_downloads`
- Updates per-resource download counts: `resources.$.metrics.views`
- Computes relationship metrics from MongoDB: followers, discussions, reuses per dataset
- Updates organization and site-level metrics

**Task 4 — `save_to_mongodb`:**
- Saves execution log to `hydra_metrics.metrics_logs`

#### Step 2: `update-metrics` task reads from PostgREST

When `METRICS_API` **is configured**, the udata Celery task `update-metrics` also reads from the same PostgREST API:

**File:** `backend/udata/core/metrics/tasks.py` (function `update_metrics_for_models`)

1. Queries `{METRICS_API}/datasets_total/data/?visit__greater=0`
2. Paginates through all results
3. Updates `Dataset.metrics.views` and `Dataset.metrics.resources_downloads`
4. Repeats for reuses, organizations, dataservices

This provides a second path for the same data to reach the models, independent of the Airflow Task 3.

### Configuration

| Key | Value | Description |
|---|---|---|
| `METRICS_API` | `http://api-tabular:8006/api` | PostgREST endpoint URL |

### Infrastructure

| Service | Container | Port | Purpose |
|---|---|---|---|
| Airflow webserver | `airflow-demo-test` | 18080 | DAG management UI |
| PostgreSQL (Hydra) | `hydra-pt-database-csv-1` | 5434 | Metrics storage |
| PostgREST (api-tabular) | `api-tabular-pt-postgrest-1` | 8006 | REST API over PostgreSQL |

### Data storage

| Storage | Contents | Retention |
|---|---|---|
| PostgreSQL `datasets` table | Monthly visit/download counts per dataset | Permanent |
| PostgreSQL `resources` table | Monthly download counts per resource | Permanent |
| PostgreSQL views (`datasets_total`, etc.) | Aggregated totals | Derived from tables |
| `hydra_metrics.metrics_logs` | DAG execution logs | Permanent |

---

## Side-by-Side Comparison

### What each system does that the other does not

| Capability | Internal (native) | External (Airflow/Hydra) |
|---|---|---|
| Views per dataset/reuse/org/dataservice | Yes | Yes |
| Downloads per dataset | Yes | Yes |
| Downloads per individual resource | Yes (via `extra.resource_id`) | Yes (via `resources.$.metrics.views`) |
| Daily historical data | Yes (`MetricAggregation` daily) | No (monthly only) |
| Monthly historical data | Yes (`MetricAggregation` monthly) | Yes (PostgreSQL tables) |
| 13-month trend API | Yes (`get_metrics_for_model()`) | Yes (via PostgREST query) |
| Site-wide statistics | Yes (`compute-site-metrics`) | Yes (Airflow Task 3) |
| Data export to PostgreSQL | No | Yes |
| CSV export of metrics | No (would need to be built) | Yes (PostgreSQL native) |
| Pipeline execution dashboard | No (Celery logs only) | Yes (Airflow UI on port 18080) |
| GDPR IP anonymization | Yes (built-in at event creation) | No |
| View deduplication | Yes (sessionStorage, 1 per session) | Yes (5-min IP window) |
| Operates without external services | Yes (MongoDB only) | No (requires Airflow + PostgreSQL + PostgREST) |
| Automatic fallback | Yes (default when `METRICS_API` is None) | No |
| Per-resource metrics in API response | No (aggregated at dataset level) | Yes (`resources.$.metrics.views`) |
| Relationship metrics (followers, discussions) | Yes (`compute-site-metrics`) | Yes (Airflow Task 3) |
| Real-time processing | Near real-time (after next task run) | Every minute (Airflow schedule) |

### Performance

| Aspect | Internal | External |
|---|---|---|
| Write path | MongoDB insert (local) | MongoDB → Airflow → PostgreSQL (3 hops) |
| Read path for model update | MongoDB aggregation pipeline (1 query) | HTTP GET to PostgREST (network call) |
| Processing overhead | Single Celery task | 4 Airflow tasks + PostgREST queries |
| Infrastructure cost | Zero additional services | 3 additional containers |
| Failure impact | MongoDB down = entire app down anyway | Airflow/PostgreSQL down = metrics stop updating, app continues |

---

## How They Work Together

The two systems are **complementary, not competing**. They share the same source (`MetricEvent`) and serve different purposes:

```
MetricEvent (MongoDB, metric_event collection)
       |
       |
       +────────────────────────────────────────+
       |                                        |
       v                                        v
  Internal System                        External System
  (update model metrics)                 (export to Hydra/PostgreSQL)
       |                                        |
       v                                        v
  Dataset.metrics.views              PostgreSQL datasets table
  Reuse.metrics.views                PostgreSQL resources table
  Organization.metrics.views         PostgREST API (api-tabular)
  MetricAggregation (history)               |
       |                                    |
       |        +---------------------------+
       |        |
       |        v
       |   METRICS_API configured?
       |        |
       |    Yes: update-metrics reads from PostgREST
       |    No:  update-metrics reads from MetricEvent directly
       |
       v
  /api/1/datasets/{slug}/
  → returns dataset.metrics in JSON response
  → frontend displays views, downloads, followers
```

### Current production setup

- `METRICS_API` is set in `.env` → `update-metrics` reads from api-tabular (external path)
- Airflow DAG runs every minute, keeping PostgreSQL in sync
- `aggregate-metrics` should also run daily to keep `MetricAggregation` updated as backup
- If Hydra/api-tabular goes down, removing `METRICS_API` from `.env` switches to the internal path without code changes

### When to use which

| Scenario | Recommended |
|---|---|
| Production with full infrastructure | External (Airflow/Hydra) as primary, internal as fallback |
| Local development | Internal only (`METRICS_API` not set) |
| Hydra/api-tabular unavailable | Internal (comment out `METRICS_API`) |
| Need metrics data in PostgreSQL for analytics/export | External (only path to Hydra) |
| Disaster recovery | Internal (zero external dependencies) |

---

## Related Documentation

- [Internal Metrics System](internal-metrics-system.md) — detailed guide for the native system (configuration, CLI commands, frontend integration, troubleshooting)
- [Metrics Workflow](metrics-workflow.md) — detailed guide for the external system (Airflow DAG, PostgreSQL tables, PostgREST API, Playwright tests)
- [Piwik Removal Rationale](piwik-removal-rationale.md) — why udata-piwik was removed in favour of the native system
